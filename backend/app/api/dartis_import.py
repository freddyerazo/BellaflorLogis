"""
API para importar archivos Excel de Dartis desde el frontend.

POST /api/dartis/upload
  - file_recetas : Excel de Ventas Recetas (obligatorio)
  - file_ventas  : Excel de Ventas clasico (obligatorio)

Regla: se suben los dos archivos juntos. Primero se procesa Recetas
(inserta registros), luego Ventas (enriquece vendedor y agencia_carga).
"""

import asyncio
import tempfile
from pathlib import Path

import openpyxl
from fastapi import APIRouter, File, HTTPException, UploadFile
from psycopg2.extras import execute_values
from sqlalchemy import text

from app.database.connection import engine

router = APIRouter(prefix="/dartis", tags=["Dartis Import"])

RECETAS_DATA_START = 7
VENTAS_DATA_START  = 7


# -- Helpers ------------------------------------------------------------------
def _safe_str(val):
    return str(val).strip() if val is not None else None

def _safe_int(val):
    try: return int(val)
    except: return None

def _safe_float(val):
    try: return float(val)
    except: return None

def _safe_date(val):
    if val is None: return None
    if hasattr(val, "date"): return val.date()
    return val

def _load_wb(upload: UploadFile):
    """Guarda el archivo en un temporal y abre el workbook."""
    suffix = Path(upload.filename).suffix or ".xlsx"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(upload.file.read())
    tmp.flush()
    return openpyxl.load_workbook(tmp.name, data_only=True, read_only=True)

def _load_wb_bytes(data: bytes, filename: str):
    """Carga un workbook desde bytes ya leídos."""
    suffix = Path(filename).suffix or ".xlsx"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(data)
    tmp.flush()
    return openpyxl.load_workbook(tmp.name, data_only=True, read_only=True)


# -- Logica importacion -------------------------------------------------------
BATCH_SIZE = 500

def _import_recetas(ws, conn) -> dict:
    rows = list(ws.iter_rows(values_only=True))[RECETAS_DATA_START:]
    postcosechas = set()
    params = []
    errores = 0

    for row in rows:
        if not any(row):
            continue
        try:
            id_pedido = _safe_int(row[3])
            if not id_pedido:
                continue
            pc = _safe_str(row[7])
            if pc:
                postcosechas.add(pc)
            params.append({
                "fecha":        _safe_date(row[0]),
                "dae":          _safe_str(row[1]),
                "id_com":       _safe_int(row[2]),
                "id_pedido":    id_pedido,
                "empresa":      _safe_str(row[4]),
                "cliente":      _safe_str(row[5]),
                "destinatario": _safe_str(row[6]),
                "postcosecha":  pc,
                "especie":      _safe_str(row[8]),
                "guia_madre":   _safe_str(row[9]),
                "guia_hija":    _safe_str(row[10]),
                "tipo_caja":    _safe_str(row[11]),
                "total_piezas": _safe_float(row[12]),
                "total_tallos": _safe_int(row[13]),
                "total_dolares":_safe_float(row[14]),
            })
        except Exception:
            errores += 1

    # Agrupar por clave única (incluye especie: una misma guia puede
    # transportar varias especies distintas). Si dos lineas comparten
    # la clave completa (mismo pedido+guia+caja+especie), son lotes
    # separados del mismo producto y se suman sus cantidades.
    dedup = {}
    for p in params:
        key = (p["id_pedido"], p["guia_madre"], p["guia_hija"], p["tipo_caja"], p["especie"])
        if key in dedup:
            existing = dedup[key]
            existing["total_piezas"] = (existing["total_piezas"] or 0) + (p["total_piezas"] or 0)
            existing["total_tallos"] = (existing["total_tallos"] or 0) + (p["total_tallos"] or 0)
            existing["total_dolares"] = (existing["total_dolares"] or 0) + (p["total_dolares"] or 0)
        else:
            dedup[key] = p
    params = list(dedup.values())

    tuples = [
        (p["fecha"], p["dae"], p["id_com"], p["id_pedido"],
         p["empresa"], p["cliente"], p["destinatario"], p["postcosecha"], p["especie"],
         p["guia_madre"], p["guia_hija"], p["tipo_caja"],
         p["total_piezas"], p["total_tallos"], p["total_dolares"])
        for p in params
    ]

    raw = conn.connection.cursor()

    # Dartis a veces exporta una linea sin guia (todavia no asignada) y luego,
    # en una reimportacion posterior, la misma linea ya con guia. Como la guia
    # es parte de la clave unica, ON CONFLICT no reconoce esa fila como la
    # misma -- se duplicaria. Se completa la guia en la fila vieja ANTES del
    # upsert principal, para que el ON CONFLICT de mas abajo si la reconozca.
    con_guia = [p for p in params if p["guia_madre"] or p["guia_hija"]]
    if con_guia:
        raw.execute("""
            CREATE TEMP TABLE tmp_recetas_guias (
                id_pedido INTEGER, tipo_caja TEXT, especie TEXT, fecha DATE,
                guia_madre TEXT, guia_hija TEXT
            ) ON COMMIT DROP
        """)
        execute_values(raw, "INSERT INTO tmp_recetas_guias VALUES %s", [
            (p["id_pedido"], p["tipo_caja"], p["especie"], p["fecha"], p["guia_madre"], p["guia_hija"])
            for p in con_guia
        ], page_size=2000)
        raw.execute("""
            UPDATE dartis_ventas dv
            SET    guia_madre = t.guia_madre, guia_hija = t.guia_hija
            FROM   tmp_recetas_guias t
            WHERE  dv.id_pedido = t.id_pedido AND dv.tipo_caja = t.tipo_caja
              AND  dv.especie = t.especie AND dv.fecha = t.fecha
              AND  dv.guia_madre IS NULL AND dv.guia_hija IS NULL
        """)

    execute_values(raw, """
        INSERT INTO dartis_ventas (
            fecha, dae, id_comercializadora, id_pedido,
            empresa, cliente, destinatario, postcosecha, especie,
            guia_madre, guia_hija, tipo_caja,
            total_piezas, total_tallos, total_dolares
        ) VALUES %s
        ON CONFLICT (id_pedido, guia_madre, guia_hija, tipo_caja, especie) DO UPDATE SET
            fecha               = EXCLUDED.fecha,
            dae                 = EXCLUDED.dae,
            id_comercializadora = EXCLUDED.id_comercializadora,
            empresa             = EXCLUDED.empresa,
            cliente             = EXCLUDED.cliente,
            destinatario        = EXCLUDED.destinatario,
            postcosecha         = EXCLUDED.postcosecha,
            especie             = EXCLUDED.especie,
            total_piezas        = EXCLUDED.total_piezas,
            total_tallos        = EXCLUDED.total_tallos,
            total_dolares       = EXCLUDED.total_dolares,
            importado_at        = now()
    """, tuples, page_size=1000)

    sin_finca = _sync_postcosechas(conn, postcosechas)
    clientes_result = _sync_customers(conn, {p["cliente"] for p in params if p.get("cliente")})

    return {
        "insertados_o_actualizados": len(tuples),
        "errores": errores,
        "postcosechas_sin_finca": sin_finca,
        "clientes_vinculados": clientes_result["vinculados"],
        "clientes_nuevos": clientes_result["nuevos"],
    }


def _enrich_ventas(ws, conn) -> dict:
    rows = list(ws.iter_rows(values_only=True))[VENTAS_DATA_START:]
    agencias = set()
    params = []
    errores = 0

    for row in rows:
        if not any(row):
            continue
        try:
            id_pedido = _safe_int(row[1])
            if not id_pedido:
                continue
            ag = _safe_str(row[4])
            if ag:
                agencias.add(ag)
            params.append({
                "id_pedido":    id_pedido,
                "agencia_carga": ag,
                "vendedor":     _safe_str(row[5]),
            })
        except Exception:
            errores += 1

    # Un mismo id_pedido puede repetirse (embarques divididos). Sin
    # deduplicar, el UPDATE...FROM deja el resultado indefinido cuando
    # hay varias filas fuente para el mismo pedido. Se conserva la
    # última aparición en el archivo (mismo criterio que en recetas).
    dedup = {}
    for p in params:
        dedup[p["id_pedido"]] = p
    params = list(dedup.values())

    tuples = [(p["id_pedido"], p["agencia_carga"], p["vendedor"]) for p in params]

    raw = conn.connection.cursor()
    raw.execute("""
        CREATE TEMP TABLE tmp_ventas_enrich (
            id_pedido    INTEGER,
            agencia_carga TEXT,
            vendedor      TEXT
        ) ON COMMIT DROP
    """)
    execute_values(raw, "INSERT INTO tmp_ventas_enrich VALUES %s", tuples, page_size=2000)
    raw.execute("""
        UPDATE dartis_ventas dv
        SET    vendedor      = t.vendedor,
               agencia_carga = t.agencia_carga
        FROM   tmp_ventas_enrich t
        WHERE  dv.id_pedido = t.id_pedido
    """)
    afectadas = raw.rowcount

    nuevas_ag = _sync_agencias(conn, agencias)

    return {
        "filas_procesadas": len(tuples),
        "actualizadas": afectadas,
        "errores": errores,
        "agencias_nuevas": nuevas_ag,
    }


def _sync_agencias(conn, agencias: set) -> list:
    existentes = {
        r[0] for r in conn.execute(
            text("SELECT dartis_name FROM cargo_agencies WHERE dartis_name IS NOT NULL")
        )
    }
    agregadas = []
    for ag in sorted(agencias):
        if not ag or ag in existentes:
            continue
        base = "".join(c for c in ag if c.isalpha())[:3].upper()
        codigo = base
        n = 1
        while conn.execute(text("SELECT 1 FROM cargo_agencies WHERE code = :c"), {"c": codigo}).first():
            codigo = base[:2] + str(n)
            n += 1
        conn.execute(text("""
            INSERT INTO cargo_agencies (code, name, dartis_name, ocr_variants, type)
            VALUES (:code, :name, :dartis_name, '{}', 'aerea')
            ON CONFLICT (code) DO NOTHING
        """), {"code": codigo, "name": ag, "dartis_name": ag})
        agregadas.append(ag)
    return agregadas


def _sync_postcosechas(conn, postcosechas: set) -> list:
    existentes = {
        r[0].lower() for r in conn.execute(text("SELECT postcosecha FROM farm_postcosecha"))
    }
    return [pc for pc in sorted(postcosechas) if pc and pc.lower() not in existentes]


def _sync_customers(conn, clientes: set) -> dict:
    """Vincula clientes de Dartis con la tabla customers.
    - Busca por dartis_name (case-insensitive).
    - Crea automáticamente los que no existan (batch insert).
    - Actualiza customer_id en dartis_ventas con un solo UPDATE.
    """
    if not clientes:
        return {"vinculados": 0, "nuevos": 0}

    clientes = {cl for cl in clientes if cl}

    # Mapa dartis_name.lower() -> id de los ya existentes
    existentes = {
        r[0]: r[1]
        for r in conn.execute(text(
            "SELECT LOWER(dartis_name), id FROM customers WHERE dartis_name IS NOT NULL AND dartis_name != ''"
        ))
    }

    # Clientes que faltan
    faltantes = sorted(cl for cl in clientes if cl.lower() not in existentes)

    if faltantes:
        # Códigos existentes para evitar duplicados (carga en bulk)
        codigos_usados = {
            r[0] for r in conn.execute(text("SELECT customer_code FROM customers"))
        }

        nuevos_params = []
        for cl in faltantes:
            base = "".join(c for c in cl if c.isalnum())[:6].upper()
            codigo = base
            n = 1
            while codigo in codigos_usados:
                codigo = base[:5] + str(n)
                n += 1
            codigos_usados.add(codigo)
            nuevos_params.append({"code": codigo, "name": cl, "dartis_name": cl})

        raw = conn.connection.cursor()
        execute_values(raw, """
            INSERT INTO customers (customer_code, customer_name, dartis_name, active)
            VALUES %s
            ON CONFLICT DO NOTHING
        """, [(p["code"], p["name"], p["dartis_name"], True) for p in nuevos_params])

    # UPDATE masivo en dartis_ventas usando JOIN
    conn.execute(text("""
        UPDATE dartis_ventas dv
        SET    customer_id = c.id
        FROM   customers c
        WHERE  LOWER(TRIM(c.dartis_name)) = LOWER(TRIM(dv.cliente))
          AND  dv.customer_id IS DISTINCT FROM c.id
    """))

    vinculados = conn.execute(text(
        "SELECT COUNT(*) FROM dartis_ventas WHERE customer_id IS NOT NULL"
    )).scalar()

    return {"vinculados": vinculados, "nuevos": len(faltantes)}


# -- Endpoint -----------------------------------------------------------------
@router.post("/upload")
async def upload_dartis(
    file_recetas: UploadFile = File(..., description="Excel Ventas Recetas de Dartis"),
    file_ventas:  UploadFile = File(..., description="Excel Ventas clasico de Dartis"),
):
    """
    Sube los dos archivos Excel de Dartis en un solo paso:
    1. Procesa Ventas Recetas -> inserta/actualiza en dartis_ventas
    2. Procesa Ventas clasico -> enriquece vendedor y agencia_carga por id_pedido
    """
    contenido_recetas = await file_recetas.read()
    contenido_ventas  = await file_ventas.read()
    nombre_recetas    = file_recetas.filename
    nombre_ventas     = file_ventas.filename

    def _procesar():
        try:
            wb_recetas = _load_wb_bytes(contenido_recetas, nombre_recetas)
            wb_ventas  = _load_wb_bytes(contenido_ventas,  nombre_ventas)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error leyendo archivos: {e}")

        with engine.begin() as conn:
            resultado_recetas = _import_recetas(wb_recetas.active, conn)
            resultado_ventas  = _enrich_ventas(wb_ventas.active, conn)

        return {
            "recetas": {"archivo": nombre_recetas, **resultado_recetas},
            "ventas":  {"archivo": nombre_ventas,  **resultado_ventas},
        }

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _procesar)
