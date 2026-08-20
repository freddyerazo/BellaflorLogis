"""Construccion/parseo del XML que espera la API de ordenes de compra de LAG.

Clonado de InventarioApiLag/backend/app/xml_utils.py sin cambios de logica.
"""

import xml.etree.ElementTree as ET

from app.schemas.inventario_lag import PurchaseOrderIn


def _add(parent: ET.Element, tag: str, value) -> None:
    ET.SubElement(parent, tag).text = "" if value is None else str(value)


def build_purchase_order_xml(order: PurchaseOrderIn) -> str:
    root = ET.Element("XMLPosAlliance")
    po = ET.SubElement(root, "Po")

    header = ET.SubElement(po, "Header")
    _add(header, "WarehouseCode", order.warehouse_code)
    _add(header, "ConsigneeCode", order.consignee_code)
    _add(header, "PoNumber", order.po_number)
    _add(header, "OriginPortCode", order.origin_port_code)
    _add(header, "DestinationPortCode", order.destination_port_code)
    _add(header, "EstimatedDate", order.estimated_date)
    _add(header, "Comments", order.comments)
    _add(header, "PostType", order.post_type)
    _add(header, "Accion", order.accion)

    details = ET.SubElement(po, "Details")
    for item in order.items:
        detail = ET.SubElement(details, "Detail")
        _add(detail, "ShipToCode", item.ship_to_code)
        _add(detail, "CarrierCode", item.carrier_code)
        _add(detail, "DispatchDate", item.dispatch_date)
        _add(detail, "FarmCode", item.farm_code)
        _add(detail, "Barcode", item.barcode)
        _add(detail, "BoxSize", item.box_size)
        _add(detail, "ProductCode", item.product_code)
        _add(detail, "ProductDescription", item.product_description)
        _add(detail, "Packing", item.packing)
        _add(detail, "UnitPrice", item.unit_price)
        _add(detail, "Length", item.length)
        _add(detail, "Width", item.width)
        # LAG escribe "Hight" (sic) en su especificacion; no corregir el nombre del tag.
        _add(detail, "Hight", item.height)
        _add(detail, "GrossWeight", item.gross_weight)
        _add(detail, "UnitOfMeasurement", item.unit_of_measurement)
        _add(detail, "Comments", item.comments)

    return ET.tostring(root, encoding="unicode")


def parse_po_status(xml_text: str) -> tuple[bool, list[dict[str, str]]]:
    root = ET.fromstring(xml_text)
    success_node = root.find(".//IsSuccess")
    is_success = success_node is not None and (success_node.text or "").strip().lower() == "true"

    errors = []
    for node in root.iter("PoErrorDetails"):
        po_number = node.findtext("POnumber") or ""
        message = node.findtext("Message") or ""
        errors.append({"poNumber": po_number.strip(), "message": message.strip()})

    return is_success, errors
