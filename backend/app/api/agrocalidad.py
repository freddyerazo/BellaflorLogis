"""
API del modulo Agrocalidad: consulta de requisitos fitosanitarios de
exportacion (guia.agrocalidad.gob.ec).

El sitio de Agrocalidad esta protegido por Imperva/Incapsula y bloquea
cualquier peticion que no venga de un navegador real, por lo que el
scraping en si NO corre aqui: sigue viviendo en GitHub Actions del repo
freddyerazo/AgrocalidadDartis (workflow "Consultar Agrocalidad", ejecuta
worker_ci.py con Playwright). Este modulo solo:
  1. Encola la solicitud en public.agrocalidad_requests (misma Supabase).
  2. Dispara ese workflow via la API REST de GitHub.
  3. Permite hacer polling del resultado y consultar el historial ya
     guardado en public.agrocalidad_requirements.
"""

import os

import httpx
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.database.connection import engine
from app.schemas.agrocalidad import (
    AREAS_VALIDAS,
    TIPOS_VALIDOS,
    AgrocalidadConsultaRequest,
)

router = APIRouter(prefix="/agrocalidad", tags=["Agrocalidad"])

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO", "freddyerazo/AgrocalidadDartis")
GITHUB_WORKFLOW = "consultar.yml"


@router.get("/catalogo")
def get_catalogo():
    """Especies/paises disponibles y los choices fijos de tipo/area."""
    with engine.connect() as conn:
        especies = conn.execute(text(
            "SELECT id, code, name, name_agrocalidad FROM species "
            "WHERE active = true ORDER BY name"
        )).mappings().all()
        paises = conn.execute(text(
            "SELECT id, code, name, name_es FROM countries "
            "WHERE active = true ORDER BY name_es NULLS LAST, name"
        )).mappings().all()

    return {
        "especies": especies,
        "paises": paises,
        "tipos": sorted(TIPOS_VALIDOS),
        "areas": sorted(AREAS_VALIDAS),
    }


@router.get("/requisitos")
def list_requisitos(species_id: str | None = None, country_id: str | None = None):
    """Historial de requisitos ya consultados (sin relanzar el scraping)."""
    filtros = []
    params = {}
    if species_id:
        filtros.append("r.species_id = :species_id")
        params["species_id"] = species_id
    if country_id:
        filtros.append("r.country_id = :country_id")
        params["country_id"] = country_id
    where = f"WHERE {' AND '.join(filtros)}" if filtros else ""

    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT r.*, s.name AS species_name, c.name_es AS country_name
            FROM agrocalidad_requirements r
            JOIN species s ON s.id = r.species_id
            JOIN countries c ON c.id = r.country_id
            {where}
            ORDER BY r.queried_at DESC
            LIMIT 200
        """), params).mappings().all()
    return rows


@router.get("/solicitud/{request_id}")
def get_solicitud(request_id: str):
    with engine.connect() as conn:
        solicitud = conn.execute(text("""
            SELECT * FROM agrocalidad_requests WHERE id = :id
        """), {"id": request_id}).mappings().first()

        if solicitud is None:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada")

        solicitud = dict(solicitud)
        if solicitud.get("requirement_id"):
            requirement = conn.execute(text("""
                SELECT * FROM agrocalidad_requirements WHERE id = :id
            """), {"id": solicitud["requirement_id"]}).mappings().first()
            solicitud["requirement"] = requirement

    return solicitud


@router.post("/consultar", status_code=201)
def crear_consulta(payload: AgrocalidadConsultaRequest):
    if payload.trade_type not in TIPOS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"trade_type invalido: {payload.trade_type}")
    if payload.area_code not in AREAS_VALIDAS:
        raise HTTPException(status_code=400, detail=f"area_code invalido: {payload.area_code}")

    with engine.begin() as conn:
        solicitud = conn.execute(text("""
            INSERT INTO agrocalidad_requests (species_id, country_id, trade_type, area_code, status)
            VALUES (:species_id, :country_id, :trade_type, :area_code, 'pending')
            RETURNING *
        """), {
            "species_id": str(payload.species_id),
            "country_id": str(payload.country_id),
            "trade_type": payload.trade_type,
            "area_code": payload.area_code,
        }).mappings().first()

    _disparar_workflow(str(solicitud["id"]))
    return solicitud


def _disparar_workflow(request_id: str):
    if not GITHUB_TOKEN:
        # Sin token configurado: la solicitud queda encolada como "pending"
        # y puede procesarse manualmente desde GitHub Actions mientras tanto.
        return

    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{GITHUB_WORKFLOW}/dispatches"
    try:
        resp = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
            },
            json={"ref": "main", "inputs": {"request_id": request_id}},
            timeout=15,
        )
        resp.raise_for_status()
    except httpx.HTTPError as e:
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE agrocalidad_requests
                SET status = 'error', error_message = :msg, updated_at = now()
                WHERE id = :id
            """), {"id": request_id, "msg": f"No se pudo disparar el workflow: {e}"})
