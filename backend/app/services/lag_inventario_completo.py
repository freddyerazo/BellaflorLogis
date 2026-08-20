"""Reconstruye el reporte ResumenCodigosDeBarra combinando varias APIs de LAG.

Ninguna API entrega ese reporte completo:

  - Shipment Information V2  -> que guias (AWB) hubo en una fecha
  - Barcode Information V2   -> el detalle de cada pieza de una guia
  - Pieces in Inventory      -> la ubicacion (rack), que el detalle no trae

Once columnas del reporte original (Days, PO, Warehouse, Ship To, Legal Name,
Dispatch Date, Received O/D, Pallet Label, Manifest Nr y User) no las expone
ninguna API documentada, por lo que no se reconstruyen aqui.

Clonado de InventarioApiLag/backend/app/inventario_completo.py sin cambios
de logica.
"""

import re
from typing import Optional

from app.schemas.inventario_lag import PiezaDetalle

CM_POR_INCH = 2.54


def solo_digitos(guia) -> str:
    return re.sub(r"\D", "", str(guia or ""))


def formatear_guia(guia) -> str:
    """Presenta el AWB como en el reporte del WMS: 02303269313 -> '023-0326 9313'."""
    d = solo_digitos(guia)
    if len(d) != 11:
        return str(guia or "").strip()
    return f"{d[:3]}-{d[3:7]} {d[7:]}"


def _numero(valor) -> Optional[float]:
    if valor is None or valor == "":
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _texto(item: dict, *claves: str) -> str:
    """Lee la primera clave presente, tolerando variaciones de mayusculas de LAG."""
    normalizado = {str(k).lower(): v for k, v in item.items()}
    for clave in claves:
        valor = normalizado.get(clave.lower())
        if valor not in (None, ""):
            return str(valor).strip()
    return ""


def _dimensiones(valor: Optional[float], unidad: str) -> tuple[Optional[float], Optional[float]]:
    """Devuelve (cm, inch). El reporte del WMS muestra ambas, redondeando la convertida."""
    if valor is None:
        return None, None
    if unidad.upper().startswith("INCH"):
        return round(valor * CM_POR_INCH), valor
    return valor, round(valor / CM_POR_INCH)


def construir_pieza(detalle: dict, guia: str, racks: dict[str, str]) -> PiezaDetalle:
    unidad = _texto(detalle, "unitOfMeasurement") or "CM"
    largo_cm, largo_inch = _dimensiones(_numero(detalle.get("length")), unidad)
    ancho_cm, ancho_inch = _dimensiones(_numero(detalle.get("width")), unidad)
    alto_cm, alto_inch = _dimensiones(_numero(detalle.get("height")), unidad)

    barcode = _texto(detalle, "barcode")
    unidades = _numero(detalle.get("packing"))
    precio = _numero(detalle.get("piecePrice"))

    return PiezaDetalle(
        status=_texto(detalle, "status"),
        barcode=barcode,
        shipment_nr=formatear_guia(guia),
        house=_texto(detalle, "hawb"),
        exporter=_texto(detalle, "exporterName", "exporterCode"),
        consignee=_texto(detalle, "consigneeName", "consigneeCode"),
        carrier=_texto(detalle, "carrierName", "carrierCode"),
        location=racks.get(barcode),
        product=_texto(detalle, "productCode"),
        description=_texto(detalle, "productDescription"),
        tipo=_texto(detalle, "boxSize"),
        largo_cm=largo_cm,
        ancho_cm=ancho_cm,
        alto_cm=alto_cm,
        largo_inch=largo_inch,
        ancho_inch=ancho_inch,
        alto_inch=alto_inch,
        unidades=int(unidades) if unidades is not None else None,
        precio=precio,
        peso=_numero(detalle.get("grossWeight")),
        # El reporte del WMS trata Price como precio unitario: el valor de la
        # caja es unidades x precio (270 tallos x 0.323 = 87.21).
        valor_caja=round(unidades * precio, 2) if unidades and precio else None,
    )


def mapa_de_racks(piezas_inventario) -> dict[str, str]:
    mapa = {}
    for item in piezas_inventario or []:
        if not isinstance(item, dict):
            continue
        barcode = _texto(item, "barcode")
        rack = _texto(item, "rack")
        if barcode and rack:
            mapa[barcode] = rack
    return mapa


def esta_recibida(status: str) -> bool:
    return "RECEIV" in (status or "").upper()
