"""Entregas de agencias de carga locales (courier distinto de UPS/FedEx),
via la hoja publica de Google Sheets del bot "EntregasLocales" (OCR +
Telegram) y su cruce con las facturas de dartis_ventas.

Clonado de REPORTEUPSFEDEX (EntregasLocalesConnector + funciones de
emparejamiento). El mapeo "texto crudo en la Sheet" -> "nombre canonico
DARTIS" ahora vive en la tabla courier_agency_mapping (antes un CSV).
"""

import difflib
import io
import os
import re
import unicodedata
from datetime import date, datetime
from typing import Optional

import httpx
from sqlalchemy import text

from app.database.connection import engine

ENTREGAS_SHEET_URL = os.getenv(
    "ENTREGAS_SHEET_URL",
    "https://docs.google.com/spreadsheets/d/1QmMrXu_LVAIQBFmyl7MyvteaEMKoteNJjBfpWnlAjDM/export?format=csv",
)
GOOGLE_SHEETS_ID = "1QmMrXu_LVAIQBFmyl7MyvteaEMKoteNJjBfpWnlAjDM"
GOOGLE_SHEETS_API_KEY = os.getenv("GOOGLE_SHEETS_API_KEY", "")

_COLUMNAS = {
    "fecha_documento": ["fechadocumento"],
    "empresa_logistica": ["empresalogistica"],
    "cliente": ["nombredelcliente"],
    "finca_exportador": ["fincaexportador"],
    "ocr_texto": ["textocompletoocr"],
}

FOTO_HYPERLINK_RE = re.compile(r'HYPERLINK\(\s*"([^"]+)"', re.IGNORECASE)
AGENCIA_OCULTA_RE = re.compile(
    r'AGENCIA\s*:?\s*\n?\s*(?:\d+\s*\n?)?([A-Z][A-Z.\s]{2,30}?)\s*\n?\s*FINCA', re.IGNORECASE
)

_cache: list[dict] = []


def _norm_header(v) -> str:
    s = unicodedata.normalize("NFKD", str(v or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


def normalizar_texto(v, quitar_espacios: bool = False) -> str:
    s = unicodedata.normalize("NFKD", str(v or "")).encode("ascii", "ignore").decode()
    s = s.upper()
    s = re.sub(r"\bCIA\.?\s*LTDA\.?\b", "", s)
    s = re.sub(r"\bS\.?A\.?S?\.?\b", "", s)
    s = re.sub(r"[.\-+/,&|]", " ", s)
    s = re.sub(r"\s+", "" if quitar_espacios else " ", s).strip()
    return s


def coincide_texto(a: str, b: str) -> bool:
    """Contencion de substring normalizado; si no hay contencion exacta,
    cae a similitud difusa (difflib) para tolerar ruido de OCR — umbral 0.75."""
    if not a or not b or len(a) < 4 or len(b) < 4:
        return False
    if a in b or b in a:
        return True
    if len(a) >= 10 and len(b) >= 10:
        ratio = difflib.SequenceMatcher(None, a.replace(" ", ""), b.replace(" ", "")).ratio()
        return ratio >= 0.75
    return False


def cargar_mapeo_agencias() -> dict[str, str]:
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT variante_en_sheet, mapeo_propuesto_dartis FROM courier_agency_mapping"
        )).all()
    return {normalizar_texto(v, quitar_espacios=True): d for v, d in rows}


def _agencia_oculta_en_ocr(ocr_texto: str) -> str:
    m = AGENCIA_OCULTA_RE.search((ocr_texto or "").upper())
    return m.group(1).strip() if m else ""


def _agencia_embebida_en_cliente(texto_cliente: str, agencias_dartis: set[str]) -> Optional[str]:
    texto_norm = normalizar_texto(texto_cliente)
    if not texto_norm:
        return None
    for agencia in agencias_dartis:
        primera_palabra = normalizar_texto(agencia).split(" ")[0]
        if len(primera_palabra) >= 8 and texto_norm.startswith(primera_palabra):
            return agencia
    return None


def _parsear_fecha(valor: str) -> Optional[date]:
    try:
        return datetime.strptime((valor or "").strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def _parsear(texto_csv: str) -> list[dict]:
    import csv

    mapa_agencias = cargar_mapeo_agencias()
    agencias_dartis_conocidas = set(mapa_agencias.values())
    lector = csv.reader(io.StringIO(texto_csv))
    encabezados = next(lector, [])
    hnorm = [_norm_header(h) for h in encabezados]
    idx = {}
    for logico, alias in _COLUMNAS.items():
        idx[logico] = next((i for i, h in enumerate(hnorm) if h in alias), None)
    if idx["empresa_logistica"] is None or idx["cliente"] is None:
        return []

    def cel(fila, k):
        return fila[idx[k]].strip() if idx[k] is not None and idx[k] < len(fila) else ""

    out = []
    for fila_sheet, fila in enumerate(lector, start=2):
        if not fila:
            continue
        agencia_raw = cel(fila, "empresa_logistica")
        if not agencia_raw:
            continue
        ocr_texto_crudo = cel(fila, "ocr_texto")
        agencia_para_mapeo = agencia_raw
        if ("/" not in agencia_raw and "|" not in agencia_raw
                and normalizar_texto(agencia_raw, quitar_espacios=True).startswith("FLORALTECH")):
            oculta = _agencia_oculta_en_ocr(ocr_texto_crudo)
            if oculta:
                agencia_para_mapeo = oculta
        clientes = [c.strip() for c in cel(fila, "cliente").split("|") if c.strip()]
        fincas = [c.strip() for c in cel(fila, "finca_exportador").split("|") if c.strip()]
        agencia_dartis_default = mapa_agencias.get(normalizar_texto(agencia_para_mapeo, quitar_espacios=True))

        lineas = []
        for i, finca in enumerate(fincas):
            cliente_i = clientes[i] if i < len(clientes) else ""
            agencia_linea = (_agencia_embebida_en_cliente(cliente_i, agencias_dartis_conocidas)
                              or agencia_dartis_default)
            lineas.append({"finca_norm": normalizar_texto(finca), "agencia_dartis": agencia_linea})
        out.append({
            "fila_sheet": fila_sheet,
            "fecha_documento": _parsear_fecha(cel(fila, "fecha_documento")),
            "agencia_raw": agencia_raw,
            "agencia_dartis": agencia_dartis_default,
            "clientes": clientes,
            "fincas": fincas,
            "lineas": lineas,
            "ocr_norm": normalizar_texto(ocr_texto_crudo),
        })
    return out


async def _fetch_fotos(client: httpx.AsyncClient) -> dict[int, str]:
    if not GOOGLE_SHEETS_API_KEY:
        return {}
    try:
        r = await client.get(
            f"https://sheets.googleapis.com/v4/spreadsheets/{GOOGLE_SHEETS_ID}/values/P2:P",
            params={"valueRenderOption": "FORMULA", "key": GOOGLE_SHEETS_API_KEY},
        )
        r.raise_for_status()
        valores = r.json().get("values", [])
    except Exception:
        return {}
    fotos = {}
    for i, fila in enumerate(valores, start=2):
        texto = str(fila[0]) if fila else ""
        m = FOTO_HYPERLINK_RE.search(texto)
        if m:
            fotos[i] = m.group(1)
    return fotos


async def fetch() -> list[dict]:
    """Nunca lanza excepcion: si falla la red, devuelve el ultimo cache
    bueno (o [] si nunca hubo). No se gatea por DEMO_MODE."""
    global _cache
    if not ENTREGAS_SHEET_URL:
        return []
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            r = await client.get(ENTREGAS_SHEET_URL)
            r.raise_for_status()
            entregas = _parsear(r.text)
            fotos = await _fetch_fotos(client)
            for e in entregas:
                e["foto_url"] = fotos.get(e["fila_sheet"])
            _cache = entregas
    except Exception:
        pass
    return _cache


def indexar_entregas_por_agencia(entregas: list[dict]) -> dict[str, list[dict]]:
    indice: dict[str, list[dict]] = {}
    for entrega in entregas:
        agencias_vistas = {l["agencia_dartis"].upper() for l in entrega["lineas"] if l["agencia_dartis"]}
        if not agencias_vistas and entrega.get("agencia_dartis"):
            agencias_vistas = {entrega["agencia_dartis"].upper()}
        for agencia in agencias_vistas:
            indice.setdefault(agencia, []).append(entrega)
    return indice


def emparejar_entrega_local(fila_dartis: dict, entregas_por_agencia: dict[str, list[dict]]) -> Optional[dict]:
    """Los TRES datos son obligatorios: agencia, finca (misma linea del
    recibo) y fecha exacta. El cliente es una senal opcional para desempatar."""
    agencia_dartis = (fila_dartis.get("courier_raw") or "").strip().upper()
    candidatos_agencia = entregas_por_agencia.get(agencia_dartis) if agencia_dartis else None
    if not candidatos_agencia:
        return None
    finca = normalizar_texto(fila_dartis.get("empresa"))
    cliente = normalizar_texto(fila_dartis.get("cliente"))
    destinatario = normalizar_texto(fila_dartis.get("destinatario"))
    fecha_dartis = fila_dartis.get("fecha_dartis")
    if not fecha_dartis:
        return None
    if isinstance(fecha_dartis, str):
        try:
            fecha_dartis = date.fromisoformat(fecha_dartis)
        except ValueError:
            return None

    candidatos = []
    for entrega in candidatos_agencia:
        if entrega["fecha_documento"] != fecha_dartis:
            continue
        if not any(coincide_texto(finca, l["finca_norm"]) and (l["agencia_dartis"] or "").upper() == agencia_dartis
                   for l in entrega["lineas"]):
            continue
        ocr = entrega.get("ocr_norm", "")
        cliente_en_ocr = bool((cliente and cliente in ocr) or (destinatario and destinatario in ocr))
        candidatos.append((not cliente_en_ocr, entrega, cliente_en_ocr))
    if not candidatos:
        return None
    candidatos.sort(key=lambda x: x[0])
    mejor = candidatos[0]
    return {**mejor[1], "cliente_confirmado_ocr": mejor[2]}
