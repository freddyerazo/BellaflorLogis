from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.database.connection import engine
from app.database.helpers import build_set_clause, jsonable_params
from app.schemas.species import SpeciesCreate, SpeciesUpdate

router = APIRouter()


@router.get("/species")
def list_species():
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT * FROM species ORDER BY code")
        ).mappings().all()


@router.post("/species", status_code=201)
def create_species(payload: SpeciesCreate):
    with engine.begin() as conn:
        return conn.execute(
            text(
                """
                INSERT INTO species (code, name)
                VALUES (:code, :name)
                RETURNING *
                """
            ),
            payload.model_dump(),
        ).mappings().first()


@router.put("/species/{species_id}")
def update_species(species_id: str, payload: SpeciesUpdate):
    data = jsonable_params(payload.model_dump(exclude_unset=True))
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = build_set_clause(data)
    data["id"] = species_id

    with engine.begin() as conn:
        row = conn.execute(
            text(f"UPDATE species SET {set_clause}, updated_at = now() WHERE id = :id RETURNING *"),
            data,
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Species not found")
    return row


@router.delete("/species/{species_id}")
def delete_species(species_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                UPDATE species
                SET active = false, inactive_date = now(), updated_at = now()
                WHERE id = :id
                RETURNING *
                """
            ),
            {"id": species_id},
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Species not found")
    return row
