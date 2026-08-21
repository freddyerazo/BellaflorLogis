from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.database.connection import engine
from app.database.helpers import build_set_clause, jsonable_params
from app.schemas.truck_company import TruckCompanyCreate, TruckCompanyUpdate

router = APIRouter()


@router.get("/truck-companies")
def list_truck_companies():
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT * FROM truck_company WHERE active = true ORDER BY carrier_name, sub_carrier_name")
        ).mappings().all()


@router.post("/truck-companies", status_code=201)
def create_truck_company(payload: TruckCompanyCreate):
    with engine.begin() as conn:
        return conn.execute(
            text(
                """
                INSERT INTO truck_company (carrier_name, sub_carrier_name, country, id_logistic_carrier)
                VALUES (:carrier_name, :sub_carrier_name, :country, :id_logistic_carrier)
                RETURNING *
                """
            ),
            payload.model_dump(),
        ).mappings().first()


@router.put("/truck-companies/{truck_company_id}")
def update_truck_company(truck_company_id: str, payload: TruckCompanyUpdate):
    data = jsonable_params(payload.model_dump(exclude_unset=True))
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = build_set_clause(data)
    data["id"] = truck_company_id

    with engine.begin() as conn:
        row = conn.execute(
            text(f"UPDATE truck_company SET {set_clause}, updated_at = now() WHERE id = :id RETURNING *"),
            data,
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Truck company not found")
    return row


@router.delete("/truck-companies/{truck_company_id}")
def delete_truck_company(truck_company_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            text("UPDATE truck_company SET active = false, updated_at = now() WHERE id = :id RETURNING *"),
            {"id": truck_company_id},
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Truck company not found")
    return row
