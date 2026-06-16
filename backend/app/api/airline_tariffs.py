from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.database.connection import engine
from app.database.helpers import build_set_clause, jsonable_params
from app.schemas.airline_tariffs import AirlineTariffCreate, AirlineTariffUpdate

router = APIRouter()


@router.get("/airline-tariffs")
def list_airline_tariffs():
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                t.id, t.airline_id, t.origin_airport_id, t.destination_airport_id,
                t.cost_per_kg, t.minimum_charge, t.currency_code,
                t.valid_from, t.valid_to, t.active, t.created_at,
                al.airline_code, al.airline_name,
                ao.iata_code AS origin_iata,  ao.city AS origin_city,
                ad.iata_code AS destination_iata, ad.city AS destination_city
            FROM airline_tariffs t
            JOIN airlines al ON al.id = t.airline_id
            JOIN airports ao ON ao.id = t.origin_airport_id
            JOIN airports ad ON ad.id = t.destination_airport_id
            ORDER BY al.airline_name, ao.iata_code, ad.iata_code, t.valid_from DESC
        """)).mappings().all()
        return [dict(r) for r in rows]


@router.post("/airline-tariffs", status_code=201)
def create_airline_tariff(payload: AirlineTariffCreate):
    data = jsonable_params(payload.model_dump())
    with engine.begin() as conn:
        row = conn.execute(text("""
            INSERT INTO airline_tariffs
                (airline_id, origin_airport_id, destination_airport_id,
                 cost_per_kg, minimum_charge, currency_code, valid_from, valid_to)
            VALUES
                (:airline_id, :origin_airport_id, :destination_airport_id,
                 :cost_per_kg, :minimum_charge, :currency_code, :valid_from, :valid_to)
            RETURNING *
        """), data).mappings().first()
        return dict(row)


@router.put("/airline-tariffs/{tariff_id}")
def update_airline_tariff(tariff_id: str, payload: AirlineTariffUpdate):
    data = jsonable_params(payload.model_dump(exclude_unset=True))
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = build_set_clause(data)
    data["id"] = tariff_id

    with engine.begin() as conn:
        row = conn.execute(
            text(f"UPDATE airline_tariffs SET {set_clause} WHERE id = :id RETURNING *"),
            data,
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Tarifa no encontrada")
    return dict(row)


@router.delete("/airline-tariffs/{tariff_id}")
def delete_airline_tariff(tariff_id: str):
    with engine.begin() as conn:
        row = conn.execute(text("""
            UPDATE airline_tariffs SET active = false WHERE id = :id RETURNING *
        """), {"id": tariff_id}).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Tarifa no encontrada")
    return dict(row)
