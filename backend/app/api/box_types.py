from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.database.connection import engine
from app.database.helpers import build_set_clause, jsonable_params
from app.schemas.box_types import BoxTypeCreate, BoxTypeUpdate

router = APIRouter()


@router.get("/box-types")
def get_box_types():

    with engine.connect() as conn:

        result = conn.execute(
            text("""
                SELECT *
                FROM box_types
                ORDER BY box_code
            """)
        )

        rows = result.mappings().all()

        return rows


@router.post("/box-types", status_code=201)
def create_box_type(payload: BoxTypeCreate):
    data = jsonable_params(payload.model_dump())
    with engine.begin() as conn:
        return conn.execute(
            text(
                """
                INSERT INTO box_types (box_code, box_name, length_cm, width_cm, height_cm, cube_ft3, reference_weight_kg)
                VALUES (:box_code, :box_name, :length_cm, :width_cm, :height_cm, :cube_ft3, :reference_weight_kg)
                RETURNING *
                """
            ),
            data,
        ).mappings().first()


@router.put("/box-types/{box_type_id}")
def update_box_type(box_type_id: str, payload: BoxTypeUpdate):
    data = jsonable_params(payload.model_dump(exclude_unset=True))
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = build_set_clause(data)
    data["id"] = box_type_id

    with engine.begin() as conn:
        row = conn.execute(
            text(f"UPDATE box_types SET {set_clause}, updated_at = now() WHERE id = :id RETURNING *"),
            data,
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Box type not found")
    return row


@router.delete("/box-types/{box_type_id}")
def delete_box_type(box_type_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                UPDATE box_types
                SET active = false, updated_at = now()
                WHERE id = :id
                RETURNING *
                """
            ),
            {"id": box_type_id},
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Box type not found")
    return row
