from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.database.connection import engine
from app.database.helpers import build_set_clause, jsonable_params
from app.schemas.profiles import ProfileUpdate

router = APIRouter()


@router.get("/profiles")
def list_profiles():
    with engine.connect() as conn:
        return conn.execute(
            text(
                """
                SELECT p.*, r.name AS role_name
                FROM profiles p
                LEFT JOIN roles r ON r.id = p.role_id
                ORDER BY p.full_name
                """
            )
        ).mappings().all()


@router.put("/profiles/{profile_id}")
def update_profile(profile_id: str, payload: ProfileUpdate):
    data = jsonable_params(payload.model_dump(exclude_unset=True))
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = build_set_clause(data)
    data["id"] = profile_id

    with engine.begin() as conn:
        row = conn.execute(
            text(f"UPDATE profiles SET {set_clause}, updated_at = now() WHERE id = :id RETURNING *"),
            data,
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return row
