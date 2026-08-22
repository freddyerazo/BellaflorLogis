"""
Cliente para el catalogo de Proveedores (Exportadores) de Logiztik Alliance.

A diferencia de lag_client.py (que habla con el WMS cloudWS), este modulo
consume el API gateway movil de Logiztik (`apigwtmb.logiztikalliance.com`),
el mismo que usa la app AllianceApp. El flujo es:

  1. Login SSO:  POST /apisso/Account/Login  (usuario/clave) -> JWT
  2. Con el Bearer <JWT>, consultar el catalogo de exportadores:
       GET  /apimobile/exportadores/CategoriaMercaderias
       POST /apimobile/exportadores/ObtenerExportadoresConMercanciaPaisAppMovil

Para Bellaflor (importador) los "proveedores" son los EXPORTADORES que le
envian mercancia. El token se cachea en memoria hasta poco antes de expirar.

Estilo alineado a BLIS: os.getenv, httpx.AsyncClient, HTTPException.
"""

import os
import time

import httpx
from fastapi import HTTPException, status

LOGIZTIK_BASE_URL = os.getenv(
    "LOGIZTIK_MOBILE_BASE_URL", "https://apigwtmb.logiztikalliance.com"
)
LOGIZTIK_USER = os.getenv("LOGIZTIK_USER", "")
LOGIZTIK_PASS = os.getenv("LOGIZTIK_PASS", "")
# Entidad (cliente) por defecto; si el login devuelve entityId, se usa ese.
LOGIZTIK_ENTITY_ID = os.getenv("LOGIZTIK_ENTITY_ID", "")
LOGIZTIK_TIMEOUT = float(os.getenv("LOGIZTIK_TIMEOUT", "30"))
# Minutos de vigencia solicitados al login (el server define el exp real del JWT).
LOGIN_MINUTOS = int(os.getenv("LOGIZTIK_LOGIN_MINUTOS", "600"))

# Cache simple del token en memoria del proceso.
_token_cache: dict = {"token": None, "entity_id": None, "expira_en": 0.0}


async def _request(method: str, path: str, **kwargs) -> httpx.Response:
    url = f"{LOGIZTIK_BASE_URL}{path}"
    # Pedir respuestas en espanol (como la app), sin pisar headers propios.
    headers = {"Accept-Language": "es-US,es;q=0.9"}
    headers.update(kwargs.pop("headers", {}) or {})
    try:
        async with httpx.AsyncClient(timeout=LOGIZTIK_TIMEOUT) as client:
            response = await client.request(method, url, headers=headers, **kwargs)
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Tiempo de espera agotado al contactar Logiztik Alliance.",
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"No se pudo contactar Logiztik Alliance: {exc}",
        )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Logiztik respondio {response.status_code}: {response.text[:300]}",
        )
    return response


async def _login() -> None:
    if not LOGIZTIK_USER or not LOGIZTIK_PASS:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Faltan credenciales de Logiztik (LOGIZTIK_USER / LOGIZTIK_PASS) en el .env.",
        )
    payload = {
        "usuario": LOGIZTIK_USER,
        "clave": LOGIZTIK_PASS,
        "minutosExpiracion": LOGIN_MINUTOS,
    }
    resp = await _request("POST", "/apisso/Account/Login", json=payload)
    try:
        data = resp.json()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Respuesta de login no valida de Logiztik.",
        )
    if not data.get("isSuccess"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Login rechazado por Logiztik: {data.get('message') or 'credenciales invalidas'}",
        )
    obj = data.get("objetoADeserializar") or {}
    token = obj.get("token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Logiztik no devolvio token en el login.",
        )
    _token_cache["token"] = token
    _token_cache["entity_id"] = obj.get("entityId") or LOGIZTIK_ENTITY_ID
    # Renovar un poco antes de que expire.
    _token_cache["expira_en"] = time.time() + max(LOGIN_MINUTOS - 5, 5) * 60


async def _ensure_token() -> None:
    if not _token_cache["token"] or time.time() >= _token_cache["expira_en"]:
        await _login()


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {_token_cache['token']}"}


async def get_categorias() -> list[dict]:
    """Categorias de mercancia (FLORES FRESCAS, FRUTAS, etc.) para el filtro."""
    await _ensure_token()
    resp = await _request(
        "GET", "/apimobile/exportadores/CategoriaMercaderias", headers=_auth_headers()
    )
    data = resp.json()
    return data.get("mercancias", []) if isinstance(data, dict) else []


async def get_proveedores(
    id_categoria: str,
    busqueda_exportador: str | None = None,
    busqueda_producto: str | None = None,
    id_pais: str | None = None,
) -> list[dict]:
    """Catalogo de proveedores (exportadores) para una categoria de mercancia.

    El API los devuelve agrupados por producto; aqui se aplanan y deduplican
    por exportador, agregando la lista de productos de cada uno.
    """
    await _ensure_token()
    body = {
        "idEntidad": _token_cache["entity_id"] or LOGIZTIK_ENTITY_ID,
        "IdCategoriaMercancia": id_categoria,
        "busquedaNombreExportador": busqueda_exportador or None,
        "busquedaNombreProducto": busqueda_producto or None,
        "idPais": id_pais or None,
    }
    resp = await _request(
        "POST",
        "/apimobile/exportadores/ObtenerExportadoresConMercanciaPaisAppMovil",
        headers=_auth_headers(),
        json=body,
    )
    grupos = resp.json()
    if not isinstance(grupos, list):
        return []

    proveedores: dict[str, dict] = {}
    for grupo in grupos:
        for exp in (grupo or {}).get("exportadores", []) or []:
            eid = exp.get("idExportador") or exp.get("nombreExportador")
            if not eid:
                continue
            if eid not in proveedores:
                proveedores[eid] = {
                    "id": exp.get("idExportador"),
                    "nombre": exp.get("nombreExportador"),
                    "pais": exp.get("nombrePais"),
                    "codigoPais": exp.get("codigoPais"),
                    "contacto": exp.get("contacto"),
                    "telefono": exp.get("telefono"),
                    "paginaWeb": exp.get("paginaWeb"),
                    "productos": exp.get("productos") or "",
                }
    return sorted(proveedores.values(), key=lambda p: (p["nombre"] or "").upper())
