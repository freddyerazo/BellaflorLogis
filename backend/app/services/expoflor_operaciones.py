"""Lectura del XML de operaciones que emite Expoflor (ReservasExportadores).

Es el archivo `XMLOperaciones<fecha>_EXPOFL.xml`, con estructura
`masterAwb -> House -> box -> boxDetail`. Cada `box` es una caja fisica con
su codigo de barra, y es la unica fuente que tiene ese nivel de detalle:
`dartis_ventas` esta agregada por (pedido, guia, especie, tipo_caja).

El punto de union con ventas es `box/factura` = `dartis_ventas.id_pedido`.
Se verifico sobre el archivo del 2026-08-18: las 29 facturas del XML existen
en ventas y cuadran en cajas y tallos.
"""

import xml.etree.ElementTree as ET
from datetime import date, datetime
from typing import Optional

from psycopg2.extras import execute_values
from sqlalchemy import text

from app.database.connection import engine

NS = {"x": "http://tempuri.org/XMLExportadores.xsd"}

# Expoflor manda esta fecha cuando la caja todavia no tiene camion asignado.
FECHA_CENTINELA = "1900-01-01"

CM_POR_INCH = 2.54


def _texto(nodo: Optional[ET.Element], tag: str) -> str:
    if nodo is None:
        return ""
    hijo = nodo.find(f"x:{tag}", NS)
    return (hijo.text or "").strip() if hijo is not None else ""


def _entero(nodo: ET.Element, tag: str) -> Optional[int]:
    valor = _texto(nodo, tag)
    if not valor:
        return None
    try:
        return int(float(valor))
    except ValueError:
        return None


def _decimal(nodo: ET.Element, tag: str) -> Optional[float]:
    valor = _texto(nodo, tag)
    if not valor:
        return None
    try:
        return float(valor)
    except ValueError:
        return None


def _fecha(nodo: ET.Element, tag: str) -> Optional[date]:
    valor = _texto(nodo, tag)
    if not valor or valor == FECHA_CENTINELA:
        return None
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse(contenido: bytes, archivo: str) -> tuple[list[dict], list[str]]:
    """Devuelve (cajas, avisos). No lanza por datos incompletos: los reporta."""
    avisos: list[str] = []

    try:
        raiz = ET.fromstring(contenido)
    except ET.ParseError as exc:
        raise ValueError(f"El archivo no es un XML valido: {exc}")

    if not raiz.tag.endswith("ReservasExportadores"):
        raise ValueError(
            "El archivo no es un XML de operaciones de Expoflor "
            f"(se esperaba <ReservasExportadores>, llego <{raiz.tag}>)."
        )

    cajas: list[dict] = []
    vistos: set[str] = set()

    for master in raiz.findall("x:masterAwb", NS):
        awb = _texto(master, "awb")
        fecha_despacho = _fecha(master, "fechaDespacho")
        origen = _texto(master, "origen")
        destino = _texto(master, "destino")

        for house in master.findall("x:House", NS):
            hawb = _texto(house, "hawb")
            codigo_cultivo = _texto(house, "codigoCultivo")
            nombre_cultivo = _texto(house, "nombreCultivo")

            for box in house.findall("x:box", NS):
                codigo_pieza = _texto(box, "codigoPieza")

                if not codigo_pieza:
                    avisos.append(f"Guia {hawb}: una caja llego sin codigoPieza; se omitio.")
                    continue
                if codigo_pieza in vistos:
                    avisos.append(f"Codigo de pieza repetido en el archivo: {codigo_pieza}; se omitio la copia.")
                    continue
                vistos.add(codigo_pieza)

                cajas.append({
                    "archivo": archivo,
                    "awb": awb,
                    "fecha_despacho": fecha_despacho,
                    "origen": origen,
                    "destino": destino,
                    "hawb": hawb,
                    "codigo_cultivo": codigo_cultivo,
                    "nombre_cultivo": nombre_cultivo,
                    "numero_dae": _texto(box, "numeroDae"),
                    "codigo_cliente": _texto(box, "codigoCliente"),
                    "nombre_cliente": _texto(box, "nombreCliente"),
                    "codigo_pieza": codigo_pieza,
                    "codigo_producto": _texto(box, "codigoProducto"),
                    "descripcion_producto": _texto(box, "descripcionProducto"),
                    "descripcion_variedad": _texto(box, "descripcionVariedad"),
                    "empaque": _texto(box, "empaque"),
                    "factura": _entero(box, "factura"),
                    "unidades": _entero(box, "unidades"),
                    "piezas": _decimal(box, "piezas"),
                    "kilos": _decimal(box, "kilos"),
                    "po": _texto(box, "po") or None,
                    "largo_cm": _decimal(box, "largo"),
                    "ancho_cm": _decimal(box, "ancho"),
                    "alto_cm": _decimal(box, "alto"),
                    "carrier_miami": _texto(box, "caja_transportador") or None,
                    "fecha_carrier": _fecha(box, "caja_fecha_transportador"),
                    "precio_xml": _decimal(box, "precio"),
                    "valortotal_xml": _decimal(box, "valortotal"),
                })

    if not cajas:
        raise ValueError("El XML no contiene cajas (<box>).")

    sin_po = sum(1 for c in cajas if not c["po"])
    if sin_po:
        avisos.append(
            f"{sin_po} de {len(cajas)} cajas llegaron sin PO. "
            "Habra que digitarlo antes de generar el XML de Armellini para esas cajas."
        )

    sin_carrier = sum(1 for c in cajas if not c["carrier_miami"])
    if sin_carrier:
        avisos.append(f"{sin_carrier} cajas todavia no tienen camion asignado en Miami.")

    sin_fecha = sum(1 for c in cajas if not c["fecha_carrier"])
    if sin_fecha:
        avisos.append(
            f"{sin_fecha} cajas no tienen fecha de salida de Miami "
            f"(vacia o {FECHA_CENTINELA})."
        )

    sin_dimensiones = sum(
        1 for c in cajas if not (c["largo_cm"] and c["ancho_cm"] and c["alto_cm"])
    )
    if sin_dimensiones:
        avisos.append(f"{sin_dimensiones} cajas llegaron sin dimensiones completas.")

    return cajas, avisos


COLUMNAS = [
    "archivo", "awb", "fecha_despacho", "origen", "destino", "hawb",
    "codigo_cultivo", "nombre_cultivo", "numero_dae", "codigo_cliente",
    "nombre_cliente", "codigo_pieza", "codigo_producto", "descripcion_producto",
    "descripcion_variedad", "empaque", "factura", "unidades", "piezas", "kilos",
    "po", "largo_cm", "ancho_cm", "alto_cm", "carrier_miami", "fecha_carrier",
    "precio_xml", "valortotal_xml",
]

# largo_inch/ancho_inch/alto_inch son columnas generadas: las calcula Postgres.
_INSERT = f"""
    INSERT INTO expoflor_operaciones_cajas ({", ".join(COLUMNAS)})
    VALUES %s
    ON CONFLICT (codigo_pieza) DO UPDATE SET
        {", ".join(f"{c} = EXCLUDED.{c}" for c in COLUMNAS if c != "codigo_pieza")},
        importado_at = now()
    RETURNING (xmax = 0) AS insertado
"""

BATCH_SIZE = 500


def importar(cajas: list[dict]) -> dict:
    """Guarda las cajas. Reimportar el mismo archivo actualiza, no duplica:
    el codigo de barra es la identidad de la caja.

    Por lotes a proposito: fila por fila son ~750 viajes de ida y vuelta a
    Supabase y la peticion tarda minutos.
    """
    insertadas = 0
    total = 0

    with engine.begin() as conn:
        raw = conn.connection.cursor()
        for inicio in range(0, len(cajas), BATCH_SIZE):
            lote = cajas[inicio:inicio + BATCH_SIZE]
            tuplas = [tuple(caja[c] for c in COLUMNAS) for caja in lote]
            execute_values(raw, _INSERT, tuplas, page_size=BATCH_SIZE)
            filas = raw.fetchall()
            insertadas += sum(1 for f in filas if f[0])
            total += len(filas)

    return {"insertadas": insertadas, "actualizadas": total - insertadas}


def conciliar_con_ventas(facturas: list[int]) -> list[dict]:
    """Cruza las cajas importadas contra dartis_ventas por factura = id_pedido.

    Ventas esta agregada por especie, asi que se compara en totales: cajas
    (SUM(total_piezas)) y tallos (SUM(total_tallos)) por pedido.
    """
    if not facturas:
        return []

    with engine.connect() as conn:
        return [dict(f) for f in conn.execute(text("""
            WITH ops AS (
                SELECT factura, count(*) AS cajas_xml, sum(unidades) AS tallos_xml,
                       min(nombre_cliente) AS destinatario_xml
                FROM expoflor_operaciones_cajas
                WHERE factura = ANY(:facturas)
                GROUP BY factura
            ), ventas AS (
                SELECT id_pedido, sum(total_piezas) AS cajas_dartis,
                       sum(total_tallos) AS tallos_dartis,
                       sum(total_dolares) AS dolares_dartis,
                       min(cliente) AS cliente, min(destinatario) AS destinatario
                FROM dartis_ventas
                WHERE id_pedido = ANY(:facturas) AND active = true
                GROUP BY id_pedido
            )
            SELECT o.factura, o.cajas_xml, o.tallos_xml, o.destinatario_xml,
                   v.cajas_dartis, v.tallos_dartis, v.dolares_dartis,
                   v.cliente, v.destinatario,
                   (v.id_pedido IS NULL) AS sin_venta,
                   round(o.cajas_xml - COALESCE(v.cajas_dartis, 0), 2) AS dif_cajas,
                   (o.tallos_xml - COALESCE(v.tallos_dartis, 0))        AS dif_tallos
            FROM ops o LEFT JOIN ventas v ON v.id_pedido = o.factura
            ORDER BY abs(o.tallos_xml - COALESCE(v.tallos_dartis, 0)) DESC, o.factura
        """), {"facturas": facturas}).mappings().all()]


def resumen(cajas: list[dict]) -> dict:
    """Totales del archivo, para mostrar antes de confirmar la importacion."""
    return {
        "total_cajas": len(cajas),
        "total_tallos": sum(c["unidades"] or 0 for c in cajas),
        "awbs": sorted({c["awb"] for c in cajas if c["awb"]}),
        "hawbs": sorted({c["hawb"] for c in cajas if c["hawb"]}),
        "facturas": sorted({c["factura"] for c in cajas if c["factura"] is not None}),
        "carriers": sorted({c["carrier_miami"] for c in cajas if c["carrier_miami"]}),
        "cajas_sin_po": sum(1 for c in cajas if not c["po"]),
    }
