import logging
import os
import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException

from app.services import entregas_locales_sheet as sheet

load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_gas_url() -> str:
    return os.getenv("INGRESOS_LOCALES_URL", "")


@router.get("/ingresos-locales/datos")
async def get_datos():
    """Proxy hacia el endpoint JSON del GAS de IngresosLocales.

    El JSON del bot trae la columna "Ver Foto" ya resuelta a su texto fijo
    ("📷 Ver Foto"): la URL real de Drive vive solo en la formula
    `HYPERLINK(...)` de esa celda, que `getValues()` del lado del bot no
    preserva. Para no tocar el bot (otro repo, otro despliegue), se lee esa
    URL aparte con la cuenta de servicio de solo lectura que ya usa el otro
    modulo, y se agrega como `_foto_url` en cada fila (por numero de fila,
    `_fila`, que es el mismo indice en ambas lecturas del mismo Sheet).
    """
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
            datos = resp.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="GAS no respondio en 120s — intenta de nuevo")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Error GAS: {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    try:
        mapa_fotos = sheet.mapa_urls_fotos()
        for registro in datos:
            fila = registro.get("_fila")
            if fila in mapa_fotos:
                registro["_foto_url"] = mapa_fotos[fila]
    except Exception as e:
        # La foto es un plus sobre el tablero de siempre -- si falla la
        # lectura aparte del Sheet, se devuelve el JSON del bot tal cual en
        # vez de tumbar toda la pantalla.
        logger.warning("No se pudo enriquecer con _foto_url: %s", e)

    return datos
