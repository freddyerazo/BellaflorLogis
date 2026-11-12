"""Lectura del Google Sheet de EntregasLocales hacia `entregas_locales_raw`.

Lee la hoja DIRECTO con la API de Google Sheets y una cuenta de servicio de
solo lectura -- NO pasa por el Apps Script Web App del bot. Esa decision es
deliberada: el proyecto original (bot de Telegram + GAS, carpeta hermana
IngresosLocales / repo freddyerazo/EntregasLocales) no se toca, ni su codigo
ni su despliegue. Aca somos un lector mas de la misma hoja.

Ademas, el endpoint `?action=datos` que usa la pestaña vieja de BLIS excluye
a proposito la columna Q ("Texto Completo (OCR)"), que es justamente el
insumo que este modulo necesita para reinterpretar los recibos.

La llave natural es el numero de fila del Sheet (`fila_sheet`): permite
sincronizar de forma idempotente -- releer la hoja y hacer UPSERT por ese
numero nunca duplica una fila ya traida.
"""

import logging
import os
import re
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from psycopg2.extras import execute_values
from sqlalchemy import text

from app.database.connection import engine

logger = logging.getLogger(__name__)

# La columna P ("Ver Foto") es `=HYPERLINK("https://drive.google.com/...","📷
# Ver Foto")`. Leida con el renderizado normal de la API (igual que el propio
# doGet() del bot con getValues()), Sheets devuelve el VALOR CALCULADO de la
# formula -- el texto "📷 Ver Foto" -- y la URL real se pierde. Para
# recuperarla hay que pedir esa columna con valueRenderOption=FORMULA.
_RE_HYPERLINK = re.compile(r'HYPERLINK\(\s*"([^"]+)"', re.IGNORECASE)


def _url_desde_formula(valor) -> str | None:
    """`valor` casi siempre es texto ("=HYPERLINK(...)" o "📷 Ver Foto"), pero
    con valueRenderOption=FORMULA una celda sin formula a veces vuelve como
    numero/booleano tal cual -- de ahi el str() antes de buscar el patron."""
    if valor is None or valor == "":
        return None
    m = _RE_HYPERLINK.search(str(valor))
    return m.group(1) if m else None

SHEET_ID = os.getenv("ENTREGAS_LOCALES_SHEET_ID", "")
SA_JSON = os.getenv("ENTREGAS_LOCALES_SA_JSON", "google-sheets-sa.json")
HOJA = os.getenv("ENTREGAS_LOCALES_HOJA", "Hoja 1")

# La hoja tiene 17 columnas (A-Q). El orden importa: es el que definio
# `configurarEncabezados()` en el codigo.js del bot original.
COLUMNAS_RAW = [
    "fecha_registro",       # A - cuando llego la foto al bot
    "hora_registro",        # B
    "fecha_documento",      # C - fecha impresa en el recibo
    "hora_documento",       # D
    "empresa_logistica",    # E
    "nombre_chofer",        # F
    "cedula",               # G
    "placa",                # H
    "finca_exportador",     # I
    "nombre_cliente",       # J
    "numero_guia_ingreso",  # K
    "detalle_cajas",        # L
    "total_fulls_pcs",      # M
    "temperatura",          # N
    "observaciones",        # O
    "ver_foto_url",         # P
    "texto_ocr",            # Q - el insumo para reinterpretar
]

# La API corta las respuestas grandes: leer las ~3.500 filas con la columna
# de OCR completa en una sola llamada hace que el servidor cierre la conexion
# (probado: ConnectionResetError). Se pide por lotes.
LOTE_FILAS = 500


def _ruta_credenciales() -> Path:
    ruta = Path(SA_JSON)
    if not ruta.is_absolute():
        # backend/app/services/ -> backend/
        ruta = Path(__file__).resolve().parents[2] / SA_JSON
    return ruta


def configurado() -> bool:
    return bool(SHEET_ID) and _ruta_credenciales().exists()


def _servicio():
    creds = service_account.Credentials.from_service_account_file(
        str(_ruta_credenciales()),
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def leer_sheet() -> list[dict]:
    """Devuelve una fila por registro del Sheet, con su numero de fila real."""
    servicio = _servicio()
    valores = servicio.spreadsheets().values()

    filas: list[dict] = []
    inicio = 2  # la 1 son los encabezados
    while True:
        fin = inicio + LOTE_FILAS - 1
        resp = valores.get(spreadsheetId=SHEET_ID, range=f"'{HOJA}'!A{inicio}:Q{fin}").execute()
        lote = resp.get("values", [])

        # Segunda lectura, solo de la columna P, pidiendo la FORMULA en vez
        # del valor calculado -- es la unica forma de recuperar la URL real
        # detras de "📷 Ver Foto". Una columna sola (sin el OCR de la Q) es
        # liviana, no hace falta paginar como el resto.
        resp_p = valores.get(
            spreadsheetId=SHEET_ID,
            range=f"'{HOJA}'!P{inicio}:P{fin}",
            valueRenderOption="FORMULA",
        ).execute()
        formulas_p = resp_p.get("values", [])

        for i, fila in enumerate(lote):
            registro = {"fila_sheet": inicio + i}
            for j, col in enumerate(COLUMNAS_RAW):
                registro[col] = (fila[j].strip() if j < len(fila) and fila[j] else None)
            formula = formulas_p[i][0] if i < len(formulas_p) and formulas_p[i] else None
            url_real = _url_desde_formula(formula)
            if url_real:
                registro["ver_foto_url"] = url_real
            filas.append(registro)
        if len(lote) < LOTE_FILAS:
            break
        inicio = fin + 1
    return filas


# Columnas que se pueden corregir a mano desde BLIS y reescribir en el Sheet
# real. A proposito NO incluye "ver_foto_url" (es una formula HYPERLINK;
# escribirla como texto plano le borraria el link a la foto) ni "texto_ocr"
# (insumo crudo del LLM, no se edita a mano).
COLUMNA_LETRA = {
    "fecha_registro":     "A",
    "hora_registro":      "B",
    "fecha_documento":    "C",
    "hora_documento":     "D",
    "empresa_logistica":  "E",
    "nombre_chofer":      "F",
    "cedula":             "G",
    "placa":              "H",
    "finca_exportador":   "I",
    "nombre_cliente":     "J",
    "numero_guia_ingreso": "K",
    "detalle_cajas":      "L",
    "total_fulls_pcs":    "M",
    "temperatura":        "N",
    "observaciones":      "O",
}
CAMPOS_EDITABLES = set(COLUMNA_LETRA)


def escribir_celdas(fila_sheet: int, campos: dict) -> None:
    """Escribe uno o mas campos de una fila YA EXISTENTE de vuelta en el
    Sheet real. Unico lugar donde BLIS deja de ser solo lectura sobre este
    Sheet -- a proposito acotado a filas que el bot ya escribio (nunca la
    ultima fila, que puede seguir "en construccion" si el bot esta a mitad
    de guardar una foto nueva en ese mismo instante).
    """
    datos = [
        {
            "range": f"'{HOJA}'!{COLUMNA_LETRA[campo]}{fila_sheet}",
            "values": [[valor if valor is not None else ""]],
        }
        for campo, valor in campos.items() if campo in COLUMNA_LETRA
    ]
    if not datos:
        return
    servicio = _servicio()
    servicio.spreadsheets().values().batchUpdate(
        spreadsheetId=SHEET_ID,
        body={"valueInputOption": "RAW", "data": datos},
    ).execute()


def actualizar_raw(fila_sheet: int, campos: dict) -> dict:
    """Corrige campos de una fila ya sincronizada: guarda en Supabase y
    escribe la misma celda en el Sheet real.

    Se identifica por `fila_sheet` (el numero de fila real del Sheet) y no
    por el id interno de Supabase -- es la llave que ya conocen las dos
    pantallas que necesitan editar (el proxy en vivo del bot trae `_fila`,
    que es el mismo numero).

    Si falla la escritura al Sheet, el cambio en Supabase NO se revierte --
    mejor un dato corregido en BLIS pero momentaneamente desalineado con el
    Sheet, que perder la correccion por un problema transitorio de Google.
    """
    campos = {k: v for k, v in campos.items() if k in CAMPOS_EDITABLES}
    if not campos:
        raise ValueError("Ningun campo editable en la solicitud.")

    with engine.begin() as conn:
        set_clause = ", ".join(f"{c} = :{c}" for c in campos)
        fila = conn.execute(text(f"""
            UPDATE entregas_locales_raw SET {set_clause}
            WHERE fila_sheet = :fila_sheet
            RETURNING id, fila_sheet
        """), {**campos, "fila_sheet": fila_sheet}).mappings().first()

    if not fila:
        raise LookupError(
            f"La fila {fila_sheet} del Sheet todavia no esta sincronizada en "
            "Supabase -- usa \"1. Traer del Sheet\" primero."
        )

    sheet_ok, sheet_error = True, None
    try:
        escribir_celdas(fila["fila_sheet"], campos)
    except Exception as e:
        sheet_ok, sheet_error = False, str(e)
        logger.warning(
            "entregas_locales_raw (fila %s) actualizado en Supabase pero "
            "fallo escribir al Sheet: %s", fila_sheet, e,
        )

    return {
        "id": fila["id"],
        "fila_sheet": fila["fila_sheet"],
        "campos_actualizados": list(campos.keys()),
        "sheet_actualizado": sheet_ok,
        "sheet_error": sheet_error,
    }


def mapa_urls_fotos() -> dict[int, str]:
    """{numero de fila del Sheet -> URL real de Drive}, para pantallas que no
    pasan por `entregas_locales_raw` (ej. la pestaña vieja, proxy directo al
    bot) y necesitan la foto igual. Una sola llamada liviana, sin paginar."""
    if not configurado():
        return {}
    servicio = _servicio()
    resp = servicio.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range=f"'{HOJA}'!P2:P",
        valueRenderOption="FORMULA",
    ).execute()
    mapa: dict[int, str] = {}
    for i, fila in enumerate(resp.get("values", [])):
        url = _url_desde_formula(fila[0] if fila else None)
        if url:
            mapa[2 + i] = url
    return mapa


def sincronizar() -> dict:
    """Trae el Sheet completo y lo vuelca en `entregas_locales_raw`.

    UPSERT por `fila_sheet`: reejecutarlo no duplica nada, y actualiza las
    filas que el bot haya corregido despues (pasa: el OCR se reprocesa a
    mano en la hoja de vez en cuando).
    """
    if not configurado():
        raise RuntimeError(
            "Falta configurar ENTREGAS_LOCALES_SHEET_ID o el archivo de la "
            f"cuenta de servicio ({_ruta_credenciales()})."
        )

    filas = leer_sheet()
    if not filas:
        return {"leidas": 0, "nuevas": 0, "actualizadas": 0}

    columnas = ["fila_sheet", *COLUMNAS_RAW]
    tuplas = [tuple(f.get(c) for c in columnas) for f in filas]

    with engine.begin() as conn:
        antes = conn.execute(text("SELECT count(*) FROM entregas_locales_raw")).scalar()
        cursor = conn.connection.cursor()
        # Bulk insert en vez de fila por fila: cada round-trip a Supabase
        # cuesta ~195 ms, y son ~3.500 filas (ver rules/coding-style.md).
        execute_values(cursor, f"""
            INSERT INTO entregas_locales_raw ({", ".join(columnas)}) VALUES %s
            ON CONFLICT (fila_sheet) DO UPDATE SET
                {", ".join(f"{c} = EXCLUDED.{c}" for c in COLUMNAS_RAW)},
                sincronizado_at = now()
        """, tuplas, page_size=500)
        despues = conn.execute(text("SELECT count(*) FROM entregas_locales_raw")).scalar()

    nuevas = despues - antes
    return {
        "leidas": len(filas),
        "nuevas": nuevas,
        "actualizadas": len(filas) - nuevas,
        "total_en_tabla": despues,
    }
