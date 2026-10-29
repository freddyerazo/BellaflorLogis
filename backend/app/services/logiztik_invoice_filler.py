"""
A partir del PDF original del reporte de flete de Logiztik-Group Ecuador,
cruza su AWB contra dartis_ventas y estampa un sello centrado con el
id_comercializadora y el cliente encontrados -- NO se escribe nada en los
campos DETAIL/ORDER NUMBER del encabezado del reporte (se probo primero y
el usuario pidio sacarlo; el sello centrado es lo unico que queda).

El PDF es generado por un motor de reportes (nombre de archivo con prefijo
"rpt") con layout fijo: las etiquetas (INVOICE NUMBER:, AWB NUMBER:, ...) y
sus valores viven siempre en la misma fila relativa entre si, pero en el
STREAM del PDF el texto de las etiquetas y el de los valores no quedan
adyacentes (el motor de reportes los dibuja en pasadas separadas) -- por
eso no sirve un regex sobre el texto plano para leer el AWB. En su lugar
se ubica cada etiqueta por su propio texto (con pdfplumber) y se toma como
valor las palabras que caen en la MISMA fila (solape vertical) a su
derecha. Esto tolera que el reporte cambie ligeramente de version sin
romper la deteccion, a diferencia de coordenadas absolutas hardcodeadas.
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
                SELECT DISTINCT cliente, id_comercializadora, especie
                FROM dartis_ventas
                WHERE guia_madre = :awb OR guia_hija = :awb
                ORDER BY cliente
                """
            ),
            {"awb": awb_number},
        ).mappings().all()
    return [dict(f) for f in filas]


def armar_campos_sello(filas: list[dict]) -> tuple[str, str, str]:
    clientes = sorted({f["cliente"] for f in filas if f["cliente"]})
    comercializadoras = sorted(
        {str(f["id_comercializadora"]) for f in filas if f["id_comercializadora"]}
    )
    especies = sorted({f["especie"] for f in filas if f["especie"]})
    detail = ", ".join(clientes) if clientes else "SIN CRUCE EN DARTIS"
    order_number = ", ".join(comercializadoras) if comercializadoras else "-"
    especie = ", ".join(especies) if especies else "-"
    return detail, order_number, especie


def _tamano_fuente_ajustado(texto: str, ancho_disponible: float, fuente="Helvetica", inicial=9.0, minimo=6.0) -> float:
    """Reduce el tamano de fuente de a medio punto hasta que el texto entre
    en el ancho disponible -- evita que un DETAIL con varios clientes se
    salga de la columna cuando un AWB agrupa mas de un cliente."""
    tamano = inicial
    while tamano > minimo and stringWidth(texto, fuente, tamano) > ancho_disponible:
        tamano -= 0.5
    return tamano


def _envolver_texto(texto: str, fuente: str, tamano: float, ancho_disponible: float) -> list[str]:
    """Parte el texto en varias lineas que entren en ancho_disponible --
    un AWB puede agrupar muchas especies o clientes distintos (hasta 16 en
    un caso real) y encoger la letra hasta que entre en una sola linea la
    vuelve ilegible o la corta contra el borde de la pagina."""
    palabras = texto.split(" ")
    lineas = []
    actual = ""
    for palabra in palabras:
        candidato = f"{actual} {palabra}".strip()
        if not actual or stringWidth(candidato, fuente, tamano) <= ancho_disponible:
            actual = candidato
        else:
            lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas


# Sello centrado con id_comercializadora + cliente, pedido por el usuario
# ademas del llenado de DETAIL/ORDER NUMBER: va al 75% de la pagina medido
# desde arriba, para que sea visible de un vistazo sin tener que leer los
# campos chicos del encabezado.
PORCENTAJE_ALTURA_SELLO = 0.75


def _dibujar_sello_centrado(c, ancho, alto, order_number: str, detail: str, especie: str):
    margen = 20
    ancho_disponible = ancho - 2 * margen
    x_centro = ancho / 2
    y = alto * (1 - PORCENTAJE_ALTURA_SELLO)

    titulo = "FINANCE INFORMATION"
    campos = [
        f"Number invoice Bellaflor Group: {order_number}",
        f"Client Bellaflor: {detail}",
        f"Specie: {especie}",
    ]

    tamano_titulo = _tamano_fuente_ajustado(titulo, ancho_disponible, fuente="Helvetica-Bold", inicial=13.0)
    # Tamano de dato fijo (no se encoge): un AWB con varios clientes o
    # especies se resuelve envolviendo cada campo en mas de una linea, no
    # achicando la letra hasta ser ilegible.
    tamano_dato = 10.5
    interlineado_titulo = tamano_titulo * 1.5
    interlineado = tamano_dato * 1.3

    c.setFont("Helvetica-Bold", tamano_titulo)
    c.drawCentredString(x_centro, y, titulo)
    y -= interlineado_titulo

    c.setFont("Helvetica-Bold", tamano_dato)
    for campo in campos:
        for linea in _envolver_texto(campo, "Helvetica-Bold", tamano_dato, ancho_disponible):
            c.drawCentredString(x_centro, y, linea)
            y -= interlineado


def rellenar_factura(pdf_bytes: bytes, detail: str, order_number: str, especie: str) -> bytes:
    """Devuelve una copia del PDF original con el sello centrado (ver
    _dibujar_sello_centrado) -- no toca el encabezado del reporte."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    primera_pagina = reader.pages[0]
    ancho = float(primera_pagina.mediabox.width)
    alto = float(primera_pagina.mediabox.height)

    overlay_buf = io.BytesIO()
    c = canvas.Canvas(overlay_buf, pagesize=(ancho, alto))
    c.setFillColor(black)
    _dibujar_sello_centrado(c, ancho, alto, order_number, detail, especie)
    c.save()
    overlay_buf.seek(0)

    overlay_reader = PdfReader(overlay_buf)
    writer = PdfWriter()

    primera_pagina.merge_page(overlay_reader.pages[0])
    writer.add_page(primera_pagina)
    for p in reader.pages[1:]:
        writer.add_page(p)

    salida = io.BytesIO()
    writer.write(salida)
    return salida.getvalue()


def procesar_factura_logiztik(pdf_bytes: bytes) -> dict:
    """Punto de entrada: lee AWB/invoice del PDF, cruza con Dartis, estampa
    el sello centrado y devuelve el PDF resultante junto con lo encontrado."""
    campos = leer_campos_factura(pdf_bytes)
    filas = buscar_cruce_dartis(campos.awb_number)
    detail, order_number, especie = armar_campos_sello(filas)
    pdf_relleno = rellenar_factura(pdf_bytes, detail, order_number, especie)
    clientes_encontrados = len({f["cliente"] for f in filas if f["cliente"]})
    return {
        "invoice_number": campos.invoice_number,
        "awb_number": campos.awb_number,
        "detail": detail,
        "order_number": order_number,
        "especie": especie,
        "clientes_encontrados": clientes_encontrados,
        "pdf_bytes": pdf_relleno,
    }
