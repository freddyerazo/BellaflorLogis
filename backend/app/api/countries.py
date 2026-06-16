from fastapi import APIRouter
from sqlalchemy import text

from app.database.connection import engine

router = APIRouter()


@router.get("/countries")
def list_countries():
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT * FROM countries ORDER BY name")
        ).mappings().all()
