"""API del modulo Torre de Control: conciliacion de cajas de dartis_ventas
contra los manifiestos de UPS y FedEx.

Clonado de REPORTEUPSFEDEX (app.py). La conciliacion vive en
app.services.courier_reconciliation; este router solo expone los endpoints
y las subidas de archivo (que aqui parsean directo a Postgres, sin el hack
de persistir via `git commit` del original).

Alcance: solo UPS y FedEx. No se consulta tracking en vivo y las agencias de
carga locales quedan fuera del proceso — ver courier_reconciliation.
"""

import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, UploadFile
from psycopg2.extras import execute_values
from sqlalchemy import text

from app.database.connection import engine
from app.services import courier_duoplane
from app.services import courier_parsers
from app.services import courier_reconciliation as motor

router = APIRouter(prefix="/torre-control", tags=["Torre de Control"])

UTC = timezone.utc


@router.get("/estado")
def estado():
    """Snapshot completo: resumen + detalle de cajas (lo consume el tablero).

    `refresh_seconds` se agrega aqui (no vive en el snapshot persistido)
    porque el tablero lo usa solo para calcular la cuenta regresiva del
    proximo refresco automatico, que es un dato de configuracion del
    scheduler (app.main), no del resultado de la conciliacion.
    """
    return {**motor.obtener_snapshot(),
            "refresh_seconds": int(os.getenv("REFRESH_SECONDS", "300"))}


@router.get("/discrepancias")
def discrepancias():
    return motor.obtener_discrepancias()


@router.post("/refrescar")
async def refrescar_manual():
    return await motor.refrescar()


@router.post("/sincronizar-duoplane")
async def sincronizar_duoplane():
    return await courier_duoplane.sincronizar()


@router.post("/subir-ups")
async def subir_ups(archivo: UploadFile):
    if not archivo.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Se esperaba un archivo .csv")
    contenido = await archivo.read()
    try:
        filas, descartadas = courier_parsers.parse_ups_csv(contenido)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not filas:
        raise HTTPException(
            status_code=400,
            detail="El CSV no trajo ninguna fila con token 'PO:<numero>' en "
                   "'Reference Number(s)'. Sin ese token no hay como cruzar contra Dartis.")

    # Deduplica dentro del propio archivo: un UPSERT no admite la misma clave
    # dos veces en el mismo lote.
    por_tracking = {f["tracking"]: f for f in filas if f["tracking"]}

    columnas = ["factura", "tracking", "referencia", "estado", "fecha_manifiesto",
                "ship_to", "destino", "servicio", "entrega_programada", "archivo"]
    tuples = [tuple(f.get(c) if c != "archivo" else archivo.filename for c in columnas)
              for f in por_tracking.values()]

    with engine.begin() as conn:
        previos = {r[0] for r in conn.execute(text(
            "SELECT tracking FROM courier_ups_manifest")).all()}
        if tuples:
            raw = conn.connection.cursor()
            # UPSERT, no TRUNCATE. El manifiesto de UPS es acumulativo y se
            # vuelve a subir entero: vaciar la tabla antes de insertar borraba
            # todo el historial anterior y dejaba solo el ultimo archivo.
            execute_values(raw, f"""
                INSERT INTO courier_ups_manifest ({", ".join(columnas)}) VALUES %s
                ON CONFLICT (tracking) DO UPDATE SET
                    factura            = EXCLUDED.factura,
                    referencia         = EXCLUDED.referencia,
                    estado             = EXCLUDED.estado,
                    fecha_manifiesto   = EXCLUDED.fecha_manifiesto,
                    ship_to            = EXCLUDED.ship_to,
                    destino            = EXCLUDED.destino,
                    servicio           = EXCLUDED.servicio,
                    entrega_programada = EXCLUDED.entrega_programada,
                    archivo            = EXCLUDED.archivo,
                    actualizado_at     = now()
            """, tuples, page_size=1000)

    nuevos = sum(1 for t in por_tracking if t not in previos)
    return {
        "ok": True,
        "archivo": archivo.filename,
        "bultos_importados": len(por_tracking),
        "nuevos": nuevos,
        "actualizados": len(por_tracking) - nuevos,
        "descartados_sin_po": descartadas,
        "duplicados_en_archivo": len(filas) - len(por_tracking),
        "facturas": len({f["factura"] for f in por_tracking.values()}),
    }


@router.post("/subir-fedex")
async def subir_fedex(archivo: UploadFile):
    if not archivo.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Se esperaba un archivo .pdf")
    contenido = await archivo.read()
    try:
        filas = courier_parsers.parse_fedex_pdf(contenido)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo leer el PDF: {e}")

    # Un envio sin token "PO:" no se puede cruzar contra Dartis: se descarta,
    # pero se cuenta.
    sin_po = sum(1 for f in filas if f["tracking"] and f["factura"] is None)
    por_tracking = {f["tracking"]: f for f in filas
                    if f["tracking"] and f["factura"] is not None}

    columnas = ["tracking", "factura", "referencia", "destinatario", "ciudad",
                "awb", "fecha_envio", "fecha_registro", "archivo"]
    ahora = datetime.now(UTC)
    tuples = [
        (f["tracking"], f["factura"], f["referencia"], f["destinatario"],
         f["ciudad"], f["awb"], f["fecha_envio"], ahora, archivo.filename)
        for f in por_tracking.values()
    ]

    with engine.begin() as conn:
        previos = {r[0] for r in conn.execute(text(
            "SELECT tracking FROM courier_fedex_envios")).all()}
        if tuples:
            # Insercion en lote: fila por fila costaba dos round-trips por
            # envio (~195 ms cada uno contra Supabase), minutos para un PDF
            # grande. Cada PDF es un despacho puntual y sus datos no cambian
            # despues, asi que un tracking ya cargado no se vuelve a escribir.
            raw = conn.connection.cursor()
            execute_values(raw, f"""
                INSERT INTO courier_fedex_envios ({", ".join(columnas)}) VALUES %s
                ON CONFLICT (tracking) DO NOTHING
            """, tuples, page_size=1000)

    nuevos = sum(1 for t in por_tracking if t not in previos)
    return {
        "ok": True,
        "archivo": archivo.filename,
        "envios_en_pdf": len(filas),
        "nuevos": nuevos,
        "duplicados": len(por_tracking) - nuevos,
        "descartados_sin_po": sin_po,
        "facturas": len({f["factura"] for f in por_tracking.values()}),
    }
