from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.database.connection import engine
from app.database.helpers import build_set_clause, jsonable_params
from app.schemas.product_sizes import ProductSizeCreate, ProductSizeUpdate

router = APIRouter()


@router.get("/product-sizes")
def list_product_sizes():
    with engine.connect() as conn:
        return conn.execute(
            text(
                """
                SELECT ps.*, s.code AS species_code, s.name AS species_name
                FROM product_sizes ps
                JOIN species s ON s.id = ps.species_id
                ORDER BY s.name, ps.size_code
                """
            )
        ).mappings().all()


@router.post("/product-sizes", status_code=201)
def create_product_size(payload: ProductSizeCreate):
    data = jsonable_params(payload.model_dump())
    with engine.begin() as conn:
        return conn.execute(
            text(
                """
                INSERT INTO product_sizes (species_id, size_code, description)
                VALUES (:species_id, :size_code, :description)
                RETURNING *
                """
            ),
            data,
        ).mappings().first()


@router.put("/product-sizes/{product_size_id}")
def update_product_size(product_size_id: str, payload: ProductSizeUpdate):
    data = jsonable_params(payload.model_dump(exclude_unset=True))
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = build_set_clause(data)
    data["id"] = product_size_id

    with engine.begin() as conn:
        row = conn.execute(
            text(f"UPDATE product_sizes SET {set_clause}, updated_at = now() WHERE id = :id RETURNING *"),
            data,
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Product size not found")
    return row


@router.delete("/product-sizes/{product_size_id}")
def delete_product_size(product_size_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                UPDATE product_sizes
                SET active = false, updated_at = now()
                WHERE id = :id
                RETURNING *
                """
            ),
            {"id": product_size_id},
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Product size not found")
    return row
