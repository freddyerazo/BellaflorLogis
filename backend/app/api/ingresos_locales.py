import os
import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException

load_dotenv()

router = APIRouter()


def _get_gas_url() -> str:
    return os.getenv("INGRESOS_LOCALES_URL", "")


@router.get("/ingresos-locales/datos")
async def get_datos():
    """Proxy hacia el endpoint JSON del GAS de IngresosLocales."""
    gas_url = _get_gas_url()
    if not gas_url:
        raise HTTPException(
            status_code=501,
            detail="INGRESOS_LOCALES_URL no configurada en .env"
        )
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=120) as client:
            resp = await client.get(gas_url)
            resp.raise_for_status()
            return resp.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="GAS no respondio en 120s — intenta de nuevo")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Error GAS: {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
