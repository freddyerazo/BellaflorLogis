"""
Rellena los campos DETAIL y ORDER NUMBER (vacios en el PDF original del
reporte de flete de Logiztik-Group Ecuador) con el cliente y el
id_comercializadora que surgen de cruzar el AWB del reporte contra
dartis_ventas.

El PDF es generado por un motor de reportes (nombre de archivo con prefijo
"rpt") con layout fijo: las etiquetas (CLIENT:, AWB NUMBER:, DETAIL:, ...) y
sus valores viven siempre en la misma fila/columna relativa entre si, pero
en el STREAM del PDF el texto de las etiquetas y el de los valores no
quedan adyacentes (el motor de reportes los dibuja en pasadas separadas) --
por eso no sirve un regex sobre el texto plano. En su lugar se ubica cada
etiqueta por su propio texto (con pdfplumber) y se toma como valor las
palabras que caen en la MISMA fila (solape vertical) a su derecha. Esto
tolera que el reporte cambie ligeramente de version sin romper la
deteccion, a diferencia de coordenadas absolutas hardcodeadas.
"""

import io
from dataclasses import dataclass

import pdfplumber
from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import black
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from sqlalchemy import text

from app.database.connection import engine


@dataclass
class CamposFactura:
    invoice_number: str
    awb_number: str


def _ubicar_etiqueta(palabras, tokens):
    """Busca una secuencia exacta de tokens (ej. ["AWB", "NUMBER:"]) entre las
    palabras extraidas por pdfplumber y devuelve su caja combinada, o None."""
    n = len(tokens)
    for i in range(len(palabras) - n + 1):
        grupo = palabras[i : i + n]
        if [p["text"] for p in grupo] == tokens:
            return {
                "x0": min(p["x0"] for p in grupo),
                "x1": max(p["x1"] for p in grupo),
                "top": min(p["top"] for p in grupo),
                "bottom": max(p["bottom"] for p in grupo),
            }
    return None


def _palabras_misma_fila(palabras, caja_etiqueta):
    """Palabras que solapan verticalmente con la etiqueta y caen a su derecha,
    ordenadas de izquierda a derecha -- es la fila de "valor" de ese campo."""
    candidatas = [
        p
        for p in palabras
        if p["top"] < caja_etiqueta["bottom"]
        and p["bottom"] > caja_etiqueta["top"]
        and p["x0"] > caja_etiqueta["x1"] + 2
    ]
    candidatas.sort(key=lambda p: p["x0"])
    return candidatas


def _valor_misma_fila(palabras, caja_etiqueta) -> str:
    return " ".join(p["text"] for p in _palabras_misma_fila(palabras, caja_etiqueta))


def leer_campos_factura(pdf_bytes: bytes) -> CamposFactura:
    """Ubica INVOICE NUMBER y AWB NUMBER en la primera pagina del reporte."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        palabras = pdf.pages[0].extract_words()

    caja_invoice = _ubicar_etiqueta(palabras, ["INVOICE", "NUMBER:"])
    caja_awb = _ubicar_etiqueta(palabras, ["AWB", "NUMBER:"])
    if not caja_invoice or not caja_awb:
        raise ValueError(
            "No se encontraron las etiquetas 'INVOICE NUMBER:' / 'AWB NUMBER:' "
            "en el PDF -- no parece ser el reporte de Logiztik-Group Ecuador esperado."
        )

    invoice_number = _valor_misma_fila(palabras, caja_invoice)
    awb_number = _valor_misma_fila(palabras, caja_awb)
    if not invoice_number or not awb_number:
        raise ValueError("No se pudo leer el valor de INVOICE NUMBER o AWB NUMBER en el PDF.")

    return CamposFactura(invoice_number=invoice_number, awb_number=awb_number)


def buscar_cruce_dartis(awb_number: str) -> list[dict]:
    """Cruza el AWB (puede venir registrado como guia_madre o como guia_hija
    segun el tipo de envio) contra dartis_ventas."""
    with engine.connect() as conn:
        filas = conn.execute(
            text(
                """
                SELECT DISTINCT cliente, id_comercializadora
                FROM dartis_ventas
                WHERE guia_madre = :awb OR guia_hija = :awb
                ORDER BY cliente
                """
            ),
            {"awb": awb_number},
        ).mappings().all()
    return [dict(f) for f in filas]


def armar_detail_y_order_number(filas: list[dict]) -> tuple[str, str]:
    clientes = sorted({f["cliente"] for f in filas if f["cliente"]})
    comercializadoras = sorted(
        {str(f["id_comercializadora"]) for f in filas if f["id_comercializadora"]}
    )
    detail = ", ".join(clientes) if clientes else "SIN CRUCE EN DARTIS"
    order_number = ", ".join(comercializadoras) if comercializadoras else "-"
    return detail, order_number


def _tamano_fuente_ajustado(texto: str, ancho_disponible: float, inicial=9.0, minimo=6.0) -> float:
    """Reduce el tamano de fuente de a medio punto hasta que el texto entre
    en el ancho disponible -- evita que un DETAIL con varios clientes se
    salga de la columna cuando un AWB agrupa mas de un cliente."""
    tamano = inicial
    while tamano > minimo and stringWidth(texto, "Helvetica", tamano) > ancho_disponible:
        tamano -= 0.5
    return tamano


def rellenar_factura(pdf_bytes: bytes, detail: str, order_number: str) -> bytes:
    """Devuelve una copia del PDF original con DETAIL y ORDER NUMBER escritos
    en su posicion correspondiente, calculada dinamicamente a partir de las
    etiquetas del propio documento (no coordenadas fijas)."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        pagina = pdf.pages[0]
        palabras = pagina.extract_words()
        ancho, alto = pagina.width, pagina.height

    caja_detail = _ubicar_etiqueta(palabras, ["DETAIL:"])
    caja_order = _ubicar_etiqueta(palabras, ["ORDER", "NUMBER:"])
    caja_client = _ubicar_etiqueta(palabras, ["CLIENT:"])
    caja_awb = _ubicar_etiqueta(palabras, ["AWB", "NUMBER:"])
    if not (caja_detail and caja_order and caja_client and caja_awb):
        raise ValueError("No se encontraron las etiquetas DETAIL:/ORDER NUMBER: en el PDF.")

    # Columna de valores: se toma la X del primer valor ya existente en la
    # misma columna (CLIENT: para la izquierda, AWB NUMBER: para la
    # derecha) en vez de un offset fijo, para seguir alineado aunque el
    # reporte cambie de version. Si esos campos vinieran vacios (no deberia
    # pasar en este reporte), se cae a un offset razonable.
    fila_client = _palabras_misma_fila(palabras, caja_client)
    x_columna_izquierda = fila_client[0]["x0"] if fila_client else caja_detail["x1"] + 26

    fila_awb = _palabras_misma_fila(palabras, caja_awb)
    x_columna_derecha = fila_awb[0]["x0"] if fila_awb else caja_order["x1"] + 13

    overlay_buf = io.BytesIO()
    c = canvas.Canvas(overlay_buf, pagesize=(ancho, alto))
    c.setFillColor(black)

    margen_derecho = 20
    y_detail = alto - caja_detail["bottom"] + 2
    tamano_detail = _tamano_fuente_ajustado(detail, (ancho - margen_derecho) - x_columna_izquierda)
    c.setFont("Helvetica", tamano_detail)
    c.drawString(x_columna_izquierda, y_detail, detail)

    y_order = alto - caja_order["bottom"] + 2
    tamano_order = _tamano_fuente_ajustado(order_number, (ancho - margen_derecho) - x_columna_derecha)
    c.setFont("Helvetica", tamano_order)
    c.drawString(x_columna_derecha, y_order, order_number)

    c.save()
    overlay_buf.seek(0)

    reader = PdfReader(io.BytesIO(pdf_bytes))
    overlay_reader = PdfReader(overlay_buf)
    writer = PdfWriter()

    primera_pagina = reader.pages[0]
    primera_pagina.merge_page(overlay_reader.pages[0])
    writer.add_page(primera_pagina)
    for p in reader.pages[1:]:
        writer.add_page(p)

    salida = io.BytesIO()
    writer.write(salida)
    return salida.getvalue()


def procesar_factura_logiztik(pdf_bytes: bytes) -> dict:
    """Punto de entrada: lee AWB/invoice del PDF, cruza con Dartis, rellena
    DETAIL/ORDER NUMBER y devuelve el PDF resultante junto con lo encontrado."""
    campos = leer_campos_factura(pdf_bytes)
    filas = buscar_cruce_dartis(campos.awb_number)
    detail, order_number = armar_detail_y_order_number(filas)
    pdf_relleno = rellenar_factura(pdf_bytes, detail, order_number)
    return {
        "invoice_number": campos.invoice_number,
        "awb_number": campos.awb_number,
        "detail": detail,
        "order_number": order_number,
        "clientes_encontrados": len(filas),
        "pdf_bytes": pdf_relleno,
    }
