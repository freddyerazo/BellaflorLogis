from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.database.connection import engine
from app.database.helpers import build_set_clause, jsonable_params
from app.schemas.farms import FarmCreate, FarmUpdate

router = APIRouter()


@router.get("/farms")
def list_farms():
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT * FROM farms ORDER BY name")
        ).mappings().all()


@router.get("/farms/{farm_id}")
def get_farm(farm_id: str):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM farms WHERE id = :id"),
            {"id": farm_id},
        ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Farm not found")
    return row


@router.post("/farms", status_code=201)
def create_farm(payload: FarmCreate):
    with engine.begin() as conn:
        return conn.execute(
            text(
                """
                INSERT INTO farms (code, name, ocr_variants, dartis_postcosecha)
                VALUES (:code, :name, :ocr_variants, :dartis_postcosecha)
                RETURNING *
                """
            ),
            {
                "code": payload.code,
                "name": payload.name,
                "ocr_variants": payload.ocr_variants or [],
                "dartis_postcosecha": payload.dartis_postcosecha,
            },
        ).mappings().first()


@router.put("/farms/{farm_id}")
def update_farm(farm_id: str, payload: FarmUpdate):
    raw = payload.model_dump(exclude_unset=True)
    if not raw:
        raise HTTPException(status_code=400, detail="No fields to update")

    data = jsonable_params(raw)
    set_clause = build_set_clause(data)
    data["id"] = farm_id

    with engine.begin() as conn:
        row = conn.execute(
            text(
                f"UPDATE farms SET {set_clause}, updated_at = now() "
                f"WHERE id = :id RETURNING *"
            ),
            data,
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Farm not found")
    return row


@router.delete("/farms/{farm_id}")
def delete_farm(farm_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                UPDATE farms
                SET active = false, inactive_date = now(), updated_at = now()
                WHERE id = :id
                RETURNING *
                """
            ),
            {"id": farm_id},
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Farm not found")
    return row


@router.get("/farms/resolve/{ocr_name}")
def resolve_farm_by_ocr(ocr_name: str):
    """Normaliza un nombre OCR al registro oficial de finca."""
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT * FROM farms
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
        raise HTTPException(status_code=404, detail="No matching farm found")
    return row
