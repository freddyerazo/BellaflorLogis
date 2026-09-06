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
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from psycopg2.extras import execute_values
from sqlalchemy import text

from app.database.connection import engine

logger = logging.getLogger(__name__)

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
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
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
        for i, fila in enumerate(lote):
            registro = {"fila_sheet": inicio + i}
            for j, col in enumerate(COLUMNAS_RAW):
                registro[col] = (fila[j].strip() if j < len(fila) and fila[j] else None)
            filas.append(registro)
        if len(lote) < LOTE_FILAS:
            break
        inicio = fin + 1
    return filas


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
