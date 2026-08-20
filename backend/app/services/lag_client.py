"""
Cliente para las APIs de Logiztik Alliance Group (LAG): el WMS que
almacena el inventario de cajas de Bellaflor en Miami.

Clonado de InventarioApiLag/backend/app/lag_client.py, adaptado al
estilo de BLIS (variables de entorno via os.getenv, sin pydantic-settings).
"""

import os

import httpx
from fastapi import HTTPException, status

LAG_ENV = os.getenv("LAG_ENV", "test")
LAG_CUSTOMER_CODE = os.getenv("LAG_CUSTOMER_CODE", "")
LAG_TOKEN = os.getenv("LAG_TOKEN", "")
LAG_SALES_API_KEY = os.getenv("LAG_SALES_API_KEY", "")
LAG_TIMEOUT = float(os.getenv("LAG_TIMEOUT", "30"))

LAG_BASE_URL = (
    "https://cloud.logiztikalliance.com:5005/logCloudWS"
    if LAG_ENV == "prod"
    else "https://training.logiztik.com:5005/logCloudWSPre"
)
LAG_SALES_BASE_URL = (
    "https://salesapi.logiztikalliance.com"
    if LAG_ENV == "prod"
    else "https://sandsalesapi1.logiztikalliance.com"
)


async def _request(method: str, url: str, **kwargs) -> httpx.Response:
    try:
        async with httpx.AsyncClient(timeout=LAG_TIMEOUT) as client:
            response = await client.request(method, url, **kwargs)
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Tiempo de espera agotado al contactar los servicios de LAG.",
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"No se pudo contactar los servicios de LAG: {exc}",
        )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LAG respondio {response.status_code}: {response.text[:500]}",
        )
    return response


def _json(response: httpx.Response):
    try:
        return response.json()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Respuesta no valida de LAG: {response.text[:500]}",
        )


async def create_purchase_order(xml_body: str) -> str:
    url = (
        f"{LAG_BASE_URL}/api/Pos/"
        f"InsertarPosXmlClientesAllianceNuevaVersion/{LAG_TOKEN}"
    )
    response = await _request(
        "POST", url, content=xml_body.encode("utf-8"), headers={"Content-Type": "application/xml"}
    )
    return response.text


async def get_pieces_in_inventory() -> list[dict]:
    """Piezas disponibles en la bodega de Miami.

    LAG no distingue en la respuesta entre "sin inventario", "token invalido" y
    "codigo de cliente invalido": los tres devuelven []. Los parametros faltantes
    devuelven una cadena vacia, y los errores de base de datos un objeto con
    la clave "mensaje". Aqui se normaliza todo eso.
    """
    url = (
        f"{LAG_BASE_URL}/api/ClientesExternosA/"
        f"ListarCodigosDeBarraDisponiblesUbicacion/{LAG_CUSTOMER_CODE}/{LAG_TOKEN}"
    )
    response = await _request("GET", url)

    if not response.text.strip():
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "LAG respondio vacio: faltan parametros. "
                "Revise LAG_CUSTOMER_CODE y LAG_TOKEN en la configuracion del servidor."
            ),
        )

    data = _json(response)

    if isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LAG reporto un error: {data.get('mensaje', data)}",
        )

    if not isinstance(data, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Formato inesperado en la respuesta de LAG: {response.text[:200]}",
        )

    return data


async def get_barcode_info(shipment_nr: str):
    url = (
        f"{LAG_BASE_URL}/api/v2/ClientesExternosA/"
        f"ListarCodigosDeBarraPorClienteNew/{LAG_CUSTOMER_CODE}/{shipment_nr}"
    )
    return _json(await _request("GET", url, params={"authenticationToken": LAG_TOKEN}))


async def get_shipment_info(date: str):
    url = (
        f"{LAG_BASE_URL}/api/ClientesExternosA/"
        f"ListarTotalesGuiasPorClienteV2/{LAG_CUSTOMER_CODE}/{date}"
    )
    return _json(await _request("GET", url, params={"authenticationToken": LAG_TOKEN}))


async def get_pieces_dispatched(date: str):
    url = (
        f"{LAG_BASE_URL}/api/ClientesExternosA/"
        f"ListarCodigosDeBarraDespachadosFecha/{LAG_CUSTOMER_CODE}/{LAG_TOKEN}/{date}"
    )
    return _json(await _request("GET", url))


async def create_sales_order(payload: dict):
    url = f"{LAG_SALES_BASE_URL}/Order/new"
    response = await _request(
        "POST", url, json=payload, headers={"apiKey": LAG_SALES_API_KEY}
    )
    return _json(response)


async def cancel_sales_order(id_order: int):
    url = f"{LAG_SALES_BASE_URL}/order/cancel"
    response = await _request(
        "POST",
        url,
        json={"idOrder": id_order},
        headers={"apiKey": LAG_SALES_API_KEY},
    )
    return _json(response)
