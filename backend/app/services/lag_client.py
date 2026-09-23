"""
Cliente para las APIs de Logiztik Alliance Group (LAG): el WMS que
almacena el inventario de cajas de Bellaflor en Miami.

Clonado de InventarioApiLag/backend/app/lag_client.py, adaptado al
estilo de BLIS (variables de entorno via os.getenv, sin pydantic-settings).
"""

import os

import httpx
from dotenv import load_dotenv
from fastapi import HTTPException, status

# Este modulo no depende de la base de datos, asi que nada mas lo garantiza
# cargar el .env antes de leer os.getenv() -- sin esto, quedaba a merced de
# que algun otro modulo (connection.py) se hubiera importado primero en la
# misma corrida. Verificado en la practica: probar lag_client solo, sin
# pasar por la app completa, dejaba LAG_TOKEN vacio y LAG respondia 404 en
# vez de un error claro de autenticacion.
load_dotenv()

LAG_ENV = os.getenv("LAG_ENV", "test")
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

# Endpoint legacy "PlaceOrder/ordernew" (posteo de inventario). A diferencia
# del resto de APIs de LAG, no tiene ambiente de pruebas: solo existe este
# host de produccion, y token propio (distinto de LAG_TOKEN).
LAG_PLACE_ORDER_BASE_URL = os.getenv(
    "LAG_PLACE_ORDER_BASE_URL", "https://cloudus.logiztikalliance.com:5005/external/api"
)
LAG_PLACE_ORDER_TOKEN = os.getenv("LAG_PLACE_ORDER_TOKEN", "")


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


async def get_pieces_in_inventory(customer_code: str) -> list[dict]:
    """Piezas disponibles en la bodega de Miami, para UN cliente de Bellaflor.

    LAG identifica "cliente" con el codigo propio de cada cliente de Bellaflor
    (`customers.customer_code` en Supabase) -- no existe un codigo unico de
    cuenta que traiga el inventario de todos a la vez.

    LAG no distingue en la respuesta entre "sin inventario", "token invalido" y
    "codigo de cliente invalido": los tres devuelven []. Los parametros faltantes
    devuelven una cadena vacia, y los errores de base de datos un objeto con
    la clave "mensaje". Aqui se normaliza todo eso.
    """
    url = (
        f"{LAG_BASE_URL}/api/ClientesExternosA/"
        f"ListarCodigosDeBarraDisponiblesUbicacion/{customer_code}/{LAG_TOKEN}"
    )
    response = await _request("GET", url)

    if not response.text.strip():
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "LAG respondio vacio: faltan parametros. "
                "Revise el customer_code enviado y LAG_TOKEN en la configuracion del servidor."
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


async def get_barcode_info(customer_code: str, shipment_nr: str):
    url = (
        f"{LAG_BASE_URL}/api/v2/ClientesExternosA/"
        f"ListarCodigosDeBarraPorClienteNew/{customer_code}/{shipment_nr}"
    )
    return _json(await _request("GET", url, params={"authenticationToken": LAG_TOKEN}))


async def get_shipment_info(customer_code: str, date: str):
    url = (
        f"{LAG_BASE_URL}/api/ClientesExternosA/"
        f"ListarTotalesGuiasPorClienteV2/{customer_code}/{date}"
    )
    return _json(await _request("GET", url, params={"authenticationToken": LAG_TOKEN}))


async def get_pieces_dispatched(customer_code: str, date: str):
    url = (
        f"{LAG_BASE_URL}/api/ClientesExternosA/"
        f"ListarCodigosDeBarraDespachadosFecha/{customer_code}/{LAG_TOKEN}/{date}"
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


async def place_order(customer_id: str, carrier_id: str, miami_ship_date: str,
                       boxes: list[dict], print_wms_labels: bool = True) -> str:
    """Posteo de inventario via el endpoint legacy PlaceOrder/ordernew.

    boxes: [{"box_id": str, "stem_price": float | None}, ...]. Sin
    documentacion oficial del formato de respuesta (texto/XML/JSON segun el
    caso) -- se devuelve el texto crudo tal cual, sin asumir su forma.
    """
    if not LAG_PLACE_ORDER_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LAG_PLACE_ORDER_TOKEN no configurado en el servidor.",
        )

    params = {
        "token": LAG_PLACE_ORDER_TOKEN,
        "customerId": customer_id,
        "carrierId": carrier_id,
        "miamiShipDate": miami_ship_date,
        "printWmsLabels": "1" if print_wms_labels else "0",
    }
    for i, box in enumerate(boxes):
        params[f"boxIds[{i}]"] = box["box_id"]
        if box.get("stem_price") is not None:
            params[f"stemPrice[{i}]"] = str(box["stem_price"])

    url = f"{LAG_PLACE_ORDER_BASE_URL}/PlaceOrder/ordernew"
    response = await _request("GET", url, params=params)
    return response.text
