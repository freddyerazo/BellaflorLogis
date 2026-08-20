"""
API del modulo Inventario LAG: proxy sobre las APIs del WMS de Logiztik
Alliance Group (bodega de Bellaflor en Miami).

Clonado de InventarioApiLag (proyecto standalone). LAG es el sistema de
registro real; este modulo no persiste nada en la base de BLIS, siempre
consulta en vivo. A diferencia del proyecto original, no valida un
X-API-Key propio: el frontend de InventarioApiLag era una pagina publica
en GitHub Pages llamando a un backend externo, mientras que aqui el
frontend lo sirve el mismo backend de BLIS (igual que el resto de modulos).
"""

import asyncio
from collections import Counter
from datetime import date as date_type
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status as http_status

from app.schemas.inventario_lag import (
    InventarioCompleto,
    InventoryResponse,
    PieceInInventory,
    PiezaDetalle,
    PurchaseOrderIn,
    PurchaseOrderResult,
    RackSummary,
    SalesOrderCancelIn,
    SalesOrderIn,
)
from app.services import lag_client
from app.services import lag_inventario_completo as ic
from app.services.lag_xml_utils import build_purchase_order_xml, parse_po_status

router = APIRouter(prefix="/inventario-lag", tags=["Inventario LAG"])

SIN_UBICACION = "SIN UBICACION"

# Llamadas simultaneas maximas a Barcode Information V2, para no saturar a LAG.
MAX_CONCURRENTES = 4


@router.get("/health")
async def health():
    return {"status": "ok", "lag_env": lag_client.LAG_ENV}


@router.get("/pieces", response_model=InventoryResponse)
async def piezas_en_inventario() -> InventoryResponse:
    """Lista las piezas disponibles en bodega, con el resumen por ubicacion."""
    crudo = await lag_client.get_pieces_in_inventory()

    piezas = [
        PieceInInventory(
            barcode=str(item.get("barcode") or "").strip(),
            rack=str(item.get("rack") or "").strip() or SIN_UBICACION,
        )
        for item in crudo
        if isinstance(item, dict)
    ]
    piezas.sort(key=lambda p: (p.rack, p.barcode))

    conteo = Counter(pieza.rack for pieza in piezas)
    resumen = [RackSummary(rack=rack, piezas=n) for rack, n in sorted(conteo.items())]

    return InventoryResponse(
        total_piezas=len(piezas),
        total_racks=len(resumen),
        piezas=piezas,
        resumen_racks=resumen,
    )


@router.get("/barcode/{shipment_nr}")
async def info_codigos_barra(shipment_nr: str):
    return await lag_client.get_barcode_info(shipment_nr)


@router.get("/full", response_model=InventarioCompleto)
async def inventario_detallado(
    fecha: Optional[date_type] = Query(
        default=None, description="Fecha de embarque (YYYY-MM-DD) para descubrir las guias"
    ),
    guias: Optional[str] = Query(
        default=None, description="Guias separadas por coma, en lugar de descubrirlas por fecha"
    ),
) -> InventarioCompleto:
    """Reconstruye el reporte ResumenCodigosDeBarra combinando tres APIs de LAG.

    Indique una fecha (para descubrir las guias del dia) o una lista de guias.
    """
    avisos: list[str] = []

    # 1. Determinar que guias consultar.
    if guias:
        lista_guias = [g.strip() for g in guias.split(",") if g.strip()]
    elif fecha:
        envios = await lag_client.get_shipment_info(fecha.isoformat())
        if isinstance(envios, dict):
            raise HTTPException(
                status_code=http_status.HTTP_502_BAD_GATEWAY,
                detail=f"LAG reporto un error al listar los envios: {envios.get('mensaje', envios)}",
            )
        lista_guias = [str(e.get("awb")).strip() for e in envios or [] if e.get("awb")]
        if not lista_guias:
            avisos.append(f"LAG no reporta guias para el {fecha.isoformat()}.")
    else:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Indique 'fecha' o 'guias'.",
        )

    # 2. Detalle de cada guia, en paralelo pero con tope de concurrencia.
    semaforo = asyncio.Semaphore(MAX_CONCURRENTES)

    async def detalle(guia: str):
        async with semaforo:
            try:
                return guia, await lag_client.get_barcode_info(guia)
            except HTTPException as exc:
                return guia, exc

    resultados = await asyncio.gather(*(detalle(g) for g in lista_guias))

    # 3. Ubicaciones. Si falla, seguimos sin racks en vez de perder todo el reporte.
    racks: dict[str, str] = {}
    try:
        racks = ic.mapa_de_racks(await lag_client.get_pieces_in_inventory())
    except HTTPException as exc:
        avisos.append(f"No se pudieron obtener las ubicaciones: {exc.detail}")

    # 4. Armar las piezas.
    piezas: list[PiezaDetalle] = []
    for guia, respuesta in resultados:
        if isinstance(respuesta, HTTPException):
            avisos.append(f"Guia {ic.formatear_guia(guia)}: {respuesta.detail}")
            continue
        if isinstance(respuesta, dict):
            avisos.append(f"Guia {ic.formatear_guia(guia)}: {respuesta.get('mensaje', respuesta)}")
            continue
        for item in respuesta or []:
            if isinstance(item, dict):
                piezas.append(ic.construir_pieza(item, guia, racks))

    piezas.sort(key=lambda p: (p.consignee, p.barcode))

    recibidas = sum(1 for p in piezas if ic.esta_recibida(p.status))
    return InventarioCompleto(
        total_piezas=len(piezas),
        total_recibidas=recibidas,
        total_pendientes=len(piezas) - recibidas,
        total_unidades=sum(p.unidades or 0 for p in piezas),
        valor_total=round(sum(p.valor_caja or 0 for p in piezas), 2),
        guias_consultadas=[ic.formatear_guia(g) for g in lista_guias],
        avisos=avisos,
        piezas=piezas,
    )


@router.get("/shipments")
async def info_envios(fecha: date_type = Query(description="Fecha del envio (YYYY-MM-DD)")):
    return await lag_client.get_shipment_info(fecha.isoformat())


@router.get("/dispatched")
async def piezas_despachadas(fecha: date_type = Query(description="Fecha de despacho (YYYY-MM-DD)")):
    return await lag_client.get_pieces_dispatched(fecha.isoformat())


@router.post("/purchase-orders", response_model=PurchaseOrderResult)
async def crear_orden_compra(order: PurchaseOrderIn) -> PurchaseOrderResult:
    if order.post_type == "LOCAL" and not order.warehouse_code:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="warehouse_code es obligatorio cuando post_type es LOCAL.",
        )

    xml_body = build_purchase_order_xml(order)
    raw = await lag_client.create_purchase_order(xml_body)

    try:
        is_success, errors = parse_po_status(raw)
    except Exception:
        raise HTTPException(
            status_code=http_status.HTTP_502_BAD_GATEWAY,
            detail=f"Respuesta XML no valida de LAG: {raw[:500]}",
        )

    return PurchaseOrderResult(is_success=is_success, errors=errors, raw_response=raw)


@router.post("/sales-orders")
async def crear_orden_venta(order: SalesOrderIn):
    return await lag_client.create_sales_order(order.model_dump(exclude_none=True))


@router.post("/sales-orders/cancel")
async def cancelar_orden_venta(payload: SalesOrderCancelIn):
    return await lag_client.cancel_sales_order(payload.idOrder)
