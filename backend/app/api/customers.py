from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.database.connection import engine
from app.database.helpers import build_set_clause, jsonable_params
from app.schemas.customers import CustomerCreate, CustomerUpdate

router = APIRouter()


@router.get("/customers")
def list_customers(es_cliente_especial: bool | None = None):
    filtro = "WHERE es_cliente_especial = :esp" if es_cliente_especial is not None else ""
    params = {"esp": es_cliente_especial} if es_cliente_especial is not None else {}
    with engine.connect() as conn:
        return conn.execute(
            text(f"SELECT * FROM customers {filtro} ORDER BY customer_code"), params
        ).mappings().all()


@router.post("/customers", status_code=201)
def create_customer(payload: CustomerCreate):
    with engine.begin() as conn:
        return conn.execute(
            text(
                """
                INSERT INTO customers
                    (customer_code, customer_name, contact_name, email, phone,
                     dartis_name, destinatario, es_cliente_especial)
                VALUES (:customer_code, :customer_name, :contact_name, :email, :phone,
                        :dartis_name, :destinatario, COALESCE(:es_cliente_especial, false))
                RETURNING *
                """
            ),
            payload.model_dump(),
        ).mappings().first()


@router.put("/customers/{customer_id}")
def update_customer(customer_id: str, payload: CustomerUpdate):
    data = jsonable_params(payload.model_dump(exclude_unset=True))
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = build_set_clause(data)
    data["id"] = customer_id

    with engine.begin() as conn:
        row = conn.execute(
            text(f"UPDATE customers SET {set_clause}, updated_at = now() WHERE id = :id RETURNING *"),
            data,
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return row


@router.delete("/customers/{customer_id}")
def delete_customer(customer_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                UPDATE customers
                SET active = false, inactive_date = now(), updated_at = now()
                WHERE id = :id
                RETURNING *
                """
            ),
            {"id": customer_id},
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return row
