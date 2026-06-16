from fastapi import APIRouter
from sqlalchemy import text

from app.database.connection import engine

router = APIRouter()

@router.get("/db-test")
def db_test():

    try:

        with engine.connect() as conn:

            result = conn.execute(
                text("SELECT NOW()")
            )

            row = result.fetchone()

            return {
                "status": "connected",
                "database_time": str(row[0])
            }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }