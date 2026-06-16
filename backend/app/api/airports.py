from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.database.connection import engine
from app.database.helpers import build_set_clause, jsonable_params
from app.schemas.airports import AirportCreate, AirportUpdate

router = APIRouter()


@router.get("/airports")
def list_airports():
    with engine.connect() as conn:
        return conn.execute(
            text(
                """
                SELECT a.*, c.code AS country_code, c.name AS country_name
                FROM airports a
                LEFT JOIN countries c ON c.id = a.country_id
                ORDER BY a.iata_code
                """
            )
        ).mappings().all()


@router.post("/airports", status_code=201)
def create_airport(payload: AirportCreate):
    data = jsonable_params(payload.model_dump())
    with engine.begin() as conn:
        return conn.execute(
            text(
                """
                INSERT INTO airports (iata_code, airport_name, city, country_id)
                VALUES (:iata_code, :airport_name, :city, :country_id)
                RETURNING *
                """
            ),
            data,
        ).mappings().first()


@router.put("/airports/{airport_id}")
def update_airport(airport_id: str, payload: AirportUpdate):
    data = jsonable_params(payload.model_dump(exclude_unset=True))
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = build_set_clause(data)
    data["id"] = airport_id

    with engine.begin() as conn:
        row = conn.execute(
            text(f"UPDATE airports SET {set_clause}, updated_at = now() WHERE id = :id RETURNING *"),
            data,
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Airport not found")
    return row


@router.delete("/airports/{airport_id}")
def delete_airport(airport_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                UPDATE airports
                SET active = false, updated_at = now()
                WHERE id = :id
                RETURNING *
                """
            ),
            {"id": airport_id},
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Airport not found")
    return row
