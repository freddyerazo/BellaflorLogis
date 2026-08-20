from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.database.connection import engine
from app.database.helpers import build_set_clause, jsonable_params
from app.schemas.cargo_agencies import CargoAgencyCreate, CargoAgencyUpdate

router = APIRouter()


@router.get("/cargo-agencies")
def list_cargo_agencies():
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT * FROM cargo_agencies ORDER BY name")
        ).mappings().all()


@router.get("/cargo-agencies/{agency_id}")
def get_cargo_agency(agency_id: str):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM cargo_agencies WHERE id = :id"),
            {"id": agency_id},
        ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Cargo agency not found")
    return row


@router.post("/cargo-agencies", status_code=201)
def create_cargo_agency(payload: CargoAgencyCreate):
    with engine.begin() as conn:
        return conn.execute(
            text(
                """
                INSERT INTO cargo_agencies (code, name, ocr_variants, type, country)
                VALUES (:code, :name, :ocr_variants, :type, :country)
                RETURNING *
                """
            ),
            {
                "code": payload.code,
                "name": payload.name,
                "ocr_variants": payload.ocr_variants or [],
                "type": payload.type,
                "country": payload.country,
            },
        ).mappings().first()


@router.put("/cargo-agencies/{agency_id}")
def update_cargo_agency(agency_id: str, payload: CargoAgencyUpdate):
    raw = payload.model_dump(exclude_unset=True)
    if not raw:
        raise HTTPException(status_code=400, detail="No fields to update")

    data = jsonable_params(raw)
    set_clause = build_set_clause(data)
    data["id"] = agency_id

    with engine.begin() as conn:
        row = conn.execute(
            text(
                f"UPDATE cargo_agencies SET {set_clause}, updated_at = now() "
                f"WHERE id = :id RETURNING *"
            ),
            data,
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Cargo agency not found")
    return row


@router.delete("/cargo-agencies/{agency_id}")
def delete_cargo_agency(agency_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                UPDATE cargo_agencies
                SET active = false, inactive_date = now(), updated_at = now()
                WHERE id = :id
                RETURNING *
                """
            ),
            {"id": agency_id},
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Cargo agency not found")
    return row


@router.get("/cargo-agencies/resolve/{ocr_name}")
def resolve_agency_by_ocr(ocr_name: str):
    """Busca una agencia por variante OCR — útil para el bot de Telegram."""
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT * FROM cargo_agencies
                WHERE active = true
                  AND (
                    LOWER(name) = LOWER(:name)
                    OR :name = ANY(ocr_variants)
                    OR LOWER(:name) = ANY(
                        SELECT LOWER(v) FROM unnest(ocr_variants) v
                    )
                  )
                LIMIT 1
                """
            ),
            {"name": ocr_name},
        ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="No matching agency found")
    return row
