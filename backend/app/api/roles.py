from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.database.connection import engine
from app.database.helpers import build_set_clause, jsonable_params
from app.schemas.roles import RoleCreate, RoleUpdate

router = APIRouter()


@router.get("/roles")
def list_roles():
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT * FROM roles ORDER BY name")
        ).mappings().all()


@router.post("/roles", status_code=201)
def create_role(payload: RoleCreate):
    with engine.begin() as conn:
        return conn.execute(
            text(
                """
                INSERT INTO roles (name, description)
                VALUES (:name, :description)
                RETURNING *
                """
            ),
            payload.model_dump(),
        ).mappings().first()


@router.put("/roles/{role_id}")
def update_role(role_id: str, payload: RoleUpdate):
    data = jsonable_params(payload.model_dump(exclude_unset=True))
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = build_set_clause(data)
    data["id"] = role_id

    with engine.begin() as conn:
        row = conn.execute(
            text(f"UPDATE roles SET {set_clause}, updated_at = now() WHERE id = :id RETURNING *"),
            data,
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Role not found")
    return row


@router.delete("/roles/{role_id}")
def delete_role(role_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                UPDATE roles
                SET active = false, inactive_date = now(), updated_at = now()
                WHERE id = :id
                RETURNING *
                """
            ),
            {"id": role_id},
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Role not found")
    return row
