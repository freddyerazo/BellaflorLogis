"""API del modulo Torre de Control: conciliacion de cajas dartis_ventas
vs manifiestos de UPS/FedEx y entregas de agencias locales.

Clonado de REPORTEUPSFEDEX (app.py). El scraping/reconciliacion en vivo
se mueve a app.services.courier_reconciliation; este router solo expone
los endpoints y las subidas de archivo (que aqui parsean directo a
Postgres, sin el hack de persistir vía `git commit` del original).
"""

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, UploadFile
from psycopg2.extras import execute_values
from sqlalchemy import text

from app.database.connection import engine
from app.services import courier_duoplane, courier_fedex_client
from app.services import courier_parsers
from app.services import courier_reconciliation as motor

router = APIRouter(prefix="/torre-control", tags=["Torre de Control"])

UTC = timezone.utc
FEDEX_DIAS_REFRESCO_ESTADO = 5


@router.get("/estado")
def estado():
    return motor.obtener_snapshot()


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
        filas = courier_parsers.parse_ups_csv(contenido)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    columnas = ["factura", "tracking", "referencia", "estado", "fecha_manifiesto",
                "ship_to", "destino", "servicio", "entrega_programada"]
    tuples = [tuple(f[c] for c in columnas) for f in filas]

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE courier_ups_manifest"))
        if tuples:
            raw = conn.connection.cursor()
            execute_values(raw, f"""
                INSERT INTO courier_ups_manifest ({", ".join(columnas)}) VALUES %s
            """, tuples, page_size=1000)

    return {"ok": True, "archivo": archivo.filename, "bultos_importados": len(filas)}


@router.post("/subir-fedex")
async def subir_fedex(archivo: UploadFile):
    if not archivo.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Se esperaba un archivo .pdf")
    contenido = await archivo.read()
    try:
        filas = courier_parsers.parse_fedex_pdf(contenido)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo leer el PDF: {e}")

    nuevos = 0
    with engine.begin() as conn:
        for f in filas:
            if not f["tracking"]:
                continue
            existe = conn.execute(text(
                "SELECT 1 FROM courier_fedex_envios WHERE tracking = :t"
            ), {"t": f["tracking"]}).first()
            if existe:
                continue
            conn.execute(text("""
                INSERT INTO courier_fedex_envios
                    (tracking, factura, referencia, destinatario, ciudad, awb, fecha_envio)
                VALUES (:tracking, :factura, :referencia, :destinatario, :ciudad, :awb, :fecha_envio)
            """), f)
            nuevos += 1

    # Refresca estado real (API de FedEx) de los recien subidos + todo lo
    # despachado dentro de +/- FEDEX_DIAS_REFRESCO_ESTADO dias de hoy.
    hoy = datetime.now(UTC).date()
    limite_atras = hoy - timedelta(days=FEDEX_DIAS_REFRESCO_ESTADO)
    limite_adelante = hoy + timedelta(days=FEDEX_DIAS_REFRESCO_ESTADO)
    with engine.connect() as conn:
        candidatos = conn.execute(text(
            "SELECT tracking, fecha_envio, fecha_registro FROM courier_fedex_envios"
        )).all()

    a_consultar = {f["tracking"] for f in filas if f["tracking"]}
    for tracking, fecha_envio, fecha_registro in candidatos:
        fecha = _parsear_fecha_fedex(fecha_envio) or _parsear_fecha_fedex(str(fecha_registro) if fecha_registro else "")
        if fecha is None or limite_atras <= fecha <= limite_adelante:
            a_consultar.add(tracking)

    estados = await courier_fedex_client.consultar_estado_real(sorted(a_consultar))
    if estados:
        with engine.begin() as conn:
            for tracking, info in estados.items():
                conn.execute(text("""
                    UPDATE courier_fedex_envios
                    SET estado_fedex = :estado_fedex, fecha_entrega_fedex = :fecha_entrega_fedex
                    WHERE tracking = :tracking
                """), {"tracking": tracking, **info})

    return {
        "ok": True, "archivo": archivo.filename,
        "envios_en_pdf": len(filas), "nuevos": nuevos, "duplicados": len(filas) - nuevos,
        "estados_actualizados": len(estados),
    }


def _parsear_fecha_fedex(valor: str):
    for fmt in ("%m/%d/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime((valor or "").strip()[:19], fmt).date()
        except ValueError:
            continue
    return None
