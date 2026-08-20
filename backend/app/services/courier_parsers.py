"""Parseo de manifiestos de courier: CSV de UPS y PDF de FedEx.

Clonado de REPORTEUPSFEDEX (UPSCsvConnector._leer_csv y
_parsear_manifiesto_fedex), adaptado para devolver listas de filas
(una por bulto) en vez de un dict en memoria — se insertan directo en
courier_ups_manifest / se upsertean en courier_fedex_envios.
"""

import csv
import io
import re

PO_RE = re.compile(r"PO:\s*(\d+)")

UPS_COLUMNAS = {
    "tracking":   ["trackingnumber", "tracking"],
    "referencia": ["referencenumber(s)", "referencenumbers", "reference"],
    "estado":     ["status"],
    "fecha":      ["manifestdate"],
    "shipto":     ["shiptoname"],
    "destino":    ["shipto"],
    "servicio":   ["service"],
    "entrega":    ["scheduleddelivery"],
}


def _norm_header(v) -> str:
    return str(v or "").strip().lower().replace(" ", "").replace("_", "")


def _extraer_po(referencia: str) -> str:
    m = PO_RE.search(referencia)
    return m.group(1) if m else ""


def parse_ups_csv(contenido: bytes) -> list[dict]:
    """Devuelve una fila por bulto: {factura, tracking, estado,
    fecha_manifiesto, ship_to, destino, servicio, entrega_programada}.
    Filas sin token PO:<numero> en 'Reference Number(s)' se descartan
    (no se puede cruzar con dartis_ventas.id_pedido)."""
    texto = contenido.decode("utf-8-sig", errors="replace")
    muestra = texto[:4096]
    delim = "\t" if muestra.count("\t") > muestra.count(",") else ","
    lector = csv.reader(io.StringIO(texto), delimiter=delim)
    encabezados = next(lector, [])
    hnorm = [_norm_header(h) for h in encabezados]
    idx = {}
    for logico, alias in UPS_COLUMNAS.items():
        idx[logico] = next((i for i, h in enumerate(hnorm) if h in alias), None)
    if idx["tracking"] is None or idx["referencia"] is None:
        raise ValueError(
            f"El CSV de UPS no tiene columnas 'Tracking Number' / "
            f"'Reference Number(s)'. Encabezados: {encabezados}"
        )

    def cel(fila, k):
        return str(fila[idx[k]]).strip() if idx[k] is not None and idx[k] < len(fila) else ""

    filas = []
    for fila in lector:
        if not fila or not cel(fila, "tracking"):
            continue
        po = _extraer_po(cel(fila, "referencia"))
        if not po:
            continue
        filas.append({
            "factura": int(po),
            "tracking": cel(fila, "tracking"),
            "referencia": cel(fila, "referencia"),
            "estado": cel(fila, "estado"),
            "fecha_manifiesto": cel(fila, "fecha"),
            "ship_to": cel(fila, "shipto"),
            "destino": cel(fila, "destino"),
            "servicio": cel(fila, "servicio"),
            "entrega_programada": cel(fila, "entrega"),
        })
    return filas


def parse_fedex_pdf(contenido: bytes) -> list[dict]:
    """Extrae de un PDF 'IPD Visa Manifest' de FedEx los envios
    individuales (cada uno delimitado por un bloque que empieza en 'CRN:')."""
    import pdfplumber

    with pdfplumber.open(io.BytesIO(contenido)) as pdf:
        texto = "\n".join(p.extract_text() or "" for p in pdf.pages)

    m_awb = re.search(r"AWB:\s*(\d+)", texto)
    m_fecha = re.search(r"SHIP DATE:\s*([\d/]+)", texto)
    awb = m_awb.group(1) if m_awb else ""
    fecha_envio = m_fecha.group(1) if m_fecha else ""

    filas = []
    for bloque in re.split(r"(?=CRN:\s*\d+)", texto)[1:]:
        m_crn = re.search(r"CRN:\s*(\d+)", bloque)
        if not m_crn:
            continue
        m_nombre = re.search(r"NME:\s*([^\n]+)", bloque)
        m_ciudad = re.search(r"CITY:\s*([^\n]+?)\s+ST/PV", bloque)
        m_ref = re.search(r"REF:\s*([A-Z0-9]+\s+[A-Z]{2}\d+)", bloque)
        m_po = re.search(r"PO:\s*(\d+)", bloque)
        filas.append({
            "tracking": m_crn.group(1).strip(),
            "factura": int(m_po.group(1)) if m_po else None,
            "referencia": m_ref.group(1) if m_ref else "",
            "destinatario": m_nombre.group(1).split("CMP:")[0].strip() if m_nombre else "",
            "ciudad": m_ciudad.group(1).strip() if m_ciudad else "",
            "awb": awb,
            "fecha_envio": fecha_envio,
        })
    return filas
