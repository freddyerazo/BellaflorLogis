from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.database.connection import engine
from app.database.helpers import build_set_clause, jsonable_params
from app.schemas.varieties import VarietyCreate, VarietyUpdate

router = APIRouter()


@router.get("/varieties")
def list_varieties():
    with engine.connect() as conn:
        return conn.execute(
            text(
                """
                SELECT v.*, s.code AS species_code, s.name AS species_name
                FROM varieties v
                JOIN species s ON s.id = v.species_id
                ORDER BY s.name, v.name
                """
            )
        ).mappings().all()


@router.post("/varieties", status_code=201)
def create_variety(payload: VarietyCreate):
    data = jsonable_params(payload.model_dump())
    with engine.begin() as conn:
        return conn.execute(
            text(
                """
                INSERT INTO varieties (species_id, code, name)
                VALUES (:species_id, :code, :name)
                RETURNING *
                """
            ),
            data,
        ).mappings().first()


@router.put("/varieties/{variety_id}")
def update_variety(variety_id: str, payload: VarietyUpdate):
    data = jsonable_params(payload.model_dump(exclude_unset=True))
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = build_set_clause(data)
    data["id"] = variety_id

    with engine.begin() as conn:
        row = conn.execute(
            text(f"UPDATE varieties SET {set_clause}, updated_at = now() WHERE id = :id RETURNING *"),
            data,
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Variety not found")
    return row


@router.delete("/varieties/{variety_id}")
def delete_variety(variety_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                UPDATE varieties
                SET active = false, inactive_date = now(), updated_at = now()
                WHERE id = :id
                RETURNING *
                """
            ),
            {"id": variety_id},
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Variety not found")
    return row
