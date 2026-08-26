"""Arma el XML AelisShipperEDI que espera Armellini.

El formato se reproduce tal cual los archivos que Bellaflor ya venia enviando
a mano (cabecera con dos espacios de sangria, OrderDetail con tabulaciones).
No se "mejora" la sangria a proposito: es el archivo que Armellini recibe.

Los datos salen de expoflor_operaciones_cajas, cruzada con:
  - farms.name              -> <FarmName>
  - armellini_consignees    -> <Consignee> (unico campo sin fuente automatica)
  - armellini_product_overrides -> <Product>, solo si algun codigo no coincide

Nota sobre <FarmName>: los 5 XML enviados a mano hasta 2026-08 llevaban la
razon social larga ("EXPORTADORA DE FLORES EXPOFLOR CIA. LTDA."). Por decision
del usuario se usa `farms.name`, que es el nombre corto ("EXPOFLOR CIA. LTDA."),
el mismo que traen el XML de operaciones y dartis_ventas.empresa.
"""

from datetime import date
from typing import Optional

from sqlalchemy import text

from app.database.connection import engine

# Codigo de Bellaflor como shipper ante Armellini.
SHIPPER_POR_DEFECTO = "MA00114"

# Codigos de carrier de Armellini.
#
# HEB es "ARMELLINI NO EDI": la ruta de Armellini que NO recibe transmision
# EDI, y por lo tanto la que obliga a generar este XML a mano. Es el codigo
# que llevan las cajas de Heinen's, destinatario de los 5 XML historicos
# (todos con Consignee FA00140). No venia en el catalogo truck_company.
#
# ARM / ART / AAX son las otras rutas de Armellini. Antes de generarles un
# XML conviene confirmar que no reciben ya los datos por EDI: si los reciben,
# este archivo duplicaria el envio.
CARRIER_ARMELLINI_SIN_EDI = "HEB"
CARRIERS_ARMELLINI = ("HEB", "ARM", "ART", "AAX")

# OJO con <Invoice>: el campo `factura` del XML de operaciones esta mal
# nombrado -- lleva el numero de PEDIDO (= dartis_ventas.id_pedido), no el de
# factura. El numero que Armellini espera es `id_comercializadora`.
#
# Verificado contra "XML Bellaflor Heinens 01102026.xml", que lleva
# <Invoice>127196</Invoice>: en dartis_ventas id_comercializadora=127196 es
# Heinen's, guia 369-1022 1853, 21 cajas de LYSIMACHIA -- exactamente el
# contenido de ese XML (mismo AWB, mismas 21 OrderDetail). Con id_pedido=127196
# no hay ninguna fila.
#
# La relacion id_pedido -> id_comercializadora es 1:1 en los 11.187 pedidos
# cargados, asi que el DISTINCT no puede multiplicar filas.
_CONSULTA = """
    SELECT o.codigo_pieza, o.awb, o.factura, o.po, o.nombre_cliente,
           o.codigo_producto, o.descripcion_producto,
           o.largo_inch, o.ancho_inch, o.alto_inch,
           o.carrier_miami, o.fecha_carrier,
           COALESCE(f.name, o.nombre_cultivo) AS farm_name,
           ac.consignee_code,
           COALESCE(ov.armellini_code, o.codigo_producto) AS product_code,
           dv.id_comercializadora AS invoice
    FROM expoflor_operaciones_cajas o
    LEFT JOIN farms f  ON f.name = o.nombre_cultivo
    LEFT JOIN armellini_consignees ac ON ac.destinatario = o.nombre_cliente
    LEFT JOIN armellini_product_overrides ov ON ov.codigo_producto = o.codigo_producto
    LEFT JOIN (SELECT DISTINCT id_pedido, id_comercializadora FROM dartis_ventas WHERE active = true) dv
           ON dv.id_pedido = o.factura
    WHERE {filtro}
    ORDER BY o.awb, o.codigo_pieza
"""


def formatear_awb(awb: str) -> str:
    """02303269895 -> '023-0326 9895', como en los XML ya enviados."""
    digitos = "".join(c for c in str(awb or "") if c.isdigit())
    if len(digitos) != 11:
        return str(awb or "").strip()
    return f"{digitos[:3]}-{digitos[3:7]} {digitos[7:]}"


def escapar(valor) -> str:
    return (
        str("" if valor is None else valor)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def buscar_cajas(
    fecha_carrier: Optional[date] = None,
    carriers: Optional[list[str]] = None,
    barcodes: Optional[list[str]] = None,
) -> list[dict]:
    """Candidatas a incluir en el XML.

    Por defecto selecciona por **destino configurado en armellini_consignees**,
    no por codigo de carrier. La razon: el codigo de carrier del XML de
    operaciones no identifica de forma fiable los envios de Armellini. En el
    archivo del 2026-08-18 las 19 cajas de Heinen's -- el destinatario de los
    5 XML historicos, todos con Consignee FA00140 -- venian marcadas `HEB`,
    mientras que `ARM` traia cajas de otros clientes sin PO. Filtrar por
    carrier habria omitido justo las cajas que el modulo tiene que generar.

    `carriers` sigue disponible como filtro adicional cuando se quiere acotar
    a un camion concreto.
    """
    condiciones, params = [], {}

    if barcodes:
        condiciones.append("o.codigo_pieza = ANY(:barcodes)")
        params["barcodes"] = barcodes
    else:
        # Solo destinos que tienen codigo de consignee de Armellini cargado.
        condiciones.append("ac.consignee_code IS NOT NULL AND ac.active")

        if fecha_carrier:
            condiciones.append("o.fecha_carrier = :fecha")
            params["fecha"] = fecha_carrier

        if carriers:
            condiciones.append("o.carrier_miami = ANY(:carriers)")
            params["carriers"] = list(carriers)

    consulta = _CONSULTA.format(filtro=" AND ".join(condiciones))

    with engine.connect() as conn:
        return [dict(f) for f in conn.execute(text(consulta), params).mappings().all()]


def validar(cajas: list[dict]) -> list[str]:
    """Problemas que hacen que el XML salga incompleto. Se muestran antes de generar."""
    avisos = []

    sin_po = [c["codigo_pieza"] for c in cajas if not c["po"]]
    if sin_po:
        avisos.append(
            f"{len(sin_po)} caja(s) sin PO: {', '.join(sin_po[:5])}"
            + ("..." if len(sin_po) > 5 else "")
            + ". Armellini recibe el campo vacio si no se completa."
        )

    sin_consignee = sorted({c["nombre_cliente"] for c in cajas if not c["consignee_code"]})
    if sin_consignee:
        avisos.append(
            "Sin codigo de consignee en armellini_consignees: "
            + ", ".join(sin_consignee)
            + ". Hay que agregarlos antes de enviar."
        )

    # <Invoice> sale de dartis_ventas.id_comercializadora, buscado por el pedido.
    # Si el pedido no esta en ventas (Excel de Dartis sin importar), no hay numero.
    sin_invoice = sorted({c["factura"] for c in cajas if not c["invoice"]})
    if sin_invoice:
        avisos.append(
            "Sin numero de factura (id_comercializadora) para el/los pedido(s) "
            + ", ".join(str(p) for p in sin_invoice)
            + ". Importe las ventas de Dartis de esa fecha; si no, <Invoice> ira vacio."
        )

    sin_farm = sorted({c["codigo_pieza"] for c in cajas if not c["farm_name"]})
    if sin_farm:
        avisos.append(f"{len(sin_farm)} caja(s) sin nombre de finca.")

    sin_dim = [c["codigo_pieza"] for c in cajas if not (c["largo_inch"] and c["ancho_inch"] and c["alto_inch"])]
    if sin_dim:
        avisos.append(f"{len(sin_dim)} caja(s) sin dimensiones.")

    fechas = {c["fecha_carrier"] for c in cajas if c["fecha_carrier"]}
    if len(fechas) > 1:
        avisos.append(
            "Las cajas tienen distintas fechas de salida ("
            + ", ".join(f.isoformat() for f in sorted(fechas))
            + "); el XML lleva una sola Shipdate."
        )
    if not fechas:
        avisos.append("Ninguna caja tiene fecha de salida de Miami.")

    return avisos


def _etiqueta(nombre: str, valor) -> str:
    """Los XML ya enviados usan <Invoice /> cuando el dato falta y
    <Invoice>127196</Invoice> cuando existe. Mismo criterio para todos."""
    if valor is None or str(valor).strip() == "":
        return f"<{nombre} />"
    return f"<{nombre}>{escapar(valor)}</{nombre}>"


def _detalle(c: dict) -> str:
    return f"""\t<OrderDetail>
\t\t<UnitID>{escapar(c["codigo_pieza"])}</UnitID>
\t\t<UnitOfMeasure>Box</UnitOfMeasure>
\t\t<FarmName>{escapar(c["farm_name"])}</FarmName>
\t\t<AWB>{escapar(formatear_awb(c["awb"]))}</AWB>
\t\t<Consignee>{escapar(c["consignee_code"])}</Consignee>
\t\t<Length>{escapar(c["largo_inch"])}</Length>
\t\t<Width>{escapar(c["ancho_inch"])}</Width>
\t\t<Height>{escapar(c["alto_inch"])}</Height>
\t\t<Measure>Inch</Measure>
\t\t<Product>{escapar(c["product_code"])}</Product>
\t\t<Product_Description>{escapar(c["descripcion_producto"])}</Product_Description>
\t\t{_etiqueta("PO", c["po"])}
\t\t{_etiqueta("Invoice", c["invoice"])}
\t</OrderDetail>"""


def construir(cajas: list[dict], shipdate: date, shipper: str = SHIPPER_POR_DEFECTO) -> str:
    if not cajas:
        raise ValueError("No hay cajas para generar el XML.")

    # Armellini enruta la caja por el consignee: sin ese codigo el envio no
    # llega a ninguna parte. Se corta aqui en vez de mandar el campo vacio.
    sin_consignee = sorted({c["nombre_cliente"] for c in cajas if not c["consignee_code"]})
    if sin_consignee:
        raise ValueError(
            "Falta el codigo de consignee de Armellini para: "
            + ", ".join(sin_consignee)
            + ". Agreguelos en armellini_consignees antes de generar el XML."
        )

    detalles = "\n".join(_detalle(c) for c in cajas)

    return (
        '<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n'
        '<AelisShipperEDI xmlns="http://www.armellini.com/a4/schemas">\n'
        "  <OrderHeader>\n"
        f"    <Shipdate>{shipdate.strftime('%m/%d/%y')}</Shipdate>\n"
        f"    <Shipper>{escapar(shipper)}</Shipper>\n"
        "  </OrderHeader>\n"
        f"{detalles}\n"
        "</AelisShipperEDI>\n"
    )


def registrar_export(xml: str, cajas: list[dict], shipdate: date, shipper: str,
                     filename: str, avisos: list[str]) -> int:
    with engine.begin() as conn:
        return conn.execute(text("""
            INSERT INTO armellini_exports
                (filename, shipdate, shipper_code, total_cajas, awbs, pos, barcodes, avisos, xml_content)
            VALUES (:filename, :shipdate, :shipper, :total, :awbs, :pos, :barcodes, :avisos, :xml)
            RETURNING id
        """), {
            "filename": filename,
            "shipdate": shipdate.strftime("%m/%d/%y"),
            "shipper": shipper,
            "total": len(cajas),
            "awbs": sorted({formatear_awb(c["awb"]) for c in cajas}),
            "pos": sorted({c["po"] for c in cajas if c["po"]}),
            "barcodes": [c["codigo_pieza"] for c in cajas],
            "avisos": avisos,
            "xml": xml,
        }).scalar()
