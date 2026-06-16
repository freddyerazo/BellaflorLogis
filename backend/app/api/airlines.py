from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.database.connection import engine
from app.database.helpers import build_set_clause, jsonable_params
from app.schemas.airlines import AirlineCreate, AirlineUpdate

router = APIRouter()


@router.get("/airlines")
def list_airlines():
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT * FROM airlines ORDER BY airline_code")
        ).mappings().all()


@router.post("/airlines", status_code=201)
def create_airline(payload: AirlineCreate):
    with engine.begin() as conn:
        return conn.execute(
            text(
                """
                INSERT INTO airlines (airline_code, airline_name)
                VALUES (:airline_code, :airline_name)
                RETURNING *
                """
            ),
            payload.model_dump(),
        ).mappings().first()


@router.put("/airlines/{airline_id}")
def update_airline(airline_id: str, payload: AirlineUpdate):
    data = jsonable_params(payload.model_dump(exclude_unset=True))
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = build_set_clause(data)
    data["id"] = airline_id

    with engine.begin() as conn:
        row = conn.execute(
            text(f"UPDATE airlines SET {set_clause}, updated_at = now() WHERE id = :id RETURNING *"),
            data,
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Airline not found")
    return row


@router.delete("/airlines/{airline_id}")
def delete_airline(airline_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                UPDATE airlines
                SET active = false, inactive_date = now(), updated_at = now()
                WHERE id = :id
                RETURNING *
                """
            ),
            {"id": airline_id},
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Airline not found")
    return row
