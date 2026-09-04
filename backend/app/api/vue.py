"""API del registro VUE (Ventanilla Unica Ecuatoriana).

Guarda que productos esta autorizada cada empresa a exportar y hacia que
paises, a partir del archivo "Lista de Producto.xls" que se descarga de la VUE.

El archivo es POR RUC: cada empresa descarga el suyo, asi que se sube uno por
empresa. ACTUALIZA, NO BORRA — un archivo parcial no prueba que una
autorizacion se haya revocado, asi que las filas que dejan de aparecer se
conservan.

Se usa en la verificacion diaria del modulo Agrocalidad: junto con "¿tiene los
requisitos averiguados?" se responde "¿esta autorizado en la VUE?".
"""

import logging
import tempfile
from pathlib import Path

import xlrd
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from psycopg2.extras import execute_values
from sqlalchemy import text

from app.database.connection import engine

router = APIRouter(prefix="/vue", tags=["VUE"])
logger = logging.getLogger(__name__)

# El archivo trae 3 filas de encabezado: titulos legibles, nombres de campo y
# codigos de catalogo. Los datos empiezan en la cuarta.
FILA_CAMPOS = 1
DATOS_DESDE = 3

# Nombres tecnicos de la segunda fila. Se mapea por nombre y no por posicion,
# por lo mismo que en Dartis: si la VUE agrega una columna, leer por indice
# fijo corrompe todo en silencio.
VUE_CAMPOS = {
    "ruc":                 ("reg_agro",),
    "actividad_comercial": ("prdt_act_cd",),
    "tipo_producto":       ("prdt_type_cd",),
    "subpartida":          ("hc",),
    "codigo_producto":     ("prdt_cd",),
    "nombre_producto":     ("prdt_nm",),
    "nombre_cientifico":   ("prdt_stn",),
    "pais_cod":            ("org_ntn_cd",),
}


def _texto(v) -> str | None:
    if v is None:
        return None
    t = str(v).strip()
    # xlrd devuelve los numeros como float: "1790986640001.0" no sirve de RUC
    if t.endswith(".0") and t[:-2].isdigit():
        t = t[:-2]
    return t or None


def _mapear(hoja) -> dict:
    """Ubica las columnas por nombre tecnico. Devuelve {campo: indice}."""
    fila = [_texto(hoja.cell_value(FILA_CAMPOS, j)) or "" for j in range(hoja.ncols)]
    norm = [f.strip().lower() for f in fila]
    indices = {}
    for campo, nombres in VUE_CAMPOS.items():
        for n in nombres:
            if n in norm:
                indices[campo] = norm.index(n)
                break
    return indices


@router.get("/registros")
def registros():
    """Que empresas tienen registro VUE cargado y desde cuando."""
    with engine.connect() as conn:
        por_empresa = conn.execute(text("""
            SELECT ruc,
                   max(empresa)                     AS empresa,
                   count(*)                         AS autorizaciones,
                   count(DISTINCT codigo_producto)  AS productos,
                   count(DISTINCT pais_cod)         AS paises,
                   count(*) FILTER (WHERE country_id IS NULL) AS paises_sin_resolver,
                   max(actualizado_at)              AS actualizado_at,
                   max(archivo)                     AS ultimo_archivo
            FROM vue_productos
            GROUP BY ruc
            ORDER BY max(actualizado_at) DESC
        """)).mappings().all()

        # Las empresas que exportan segun Dartis, para saber cuales faltan.
        empresas_ventas = conn.execute(text("""
            SELECT empresa, count(*) lineas, sum(total_dolares) dolares
            FROM dartis_ventas WHERE active AND empresa IS NOT NULL
            GROUP BY empresa ORDER BY sum(total_dolares) DESC NULLS LAST
        """)).mappings().all()

    return {"registros": por_empresa, "empresas_ventas": empresas_ventas}


@router.post("/upload")
async def upload_vue(
    file: UploadFile = File(..., description="Lista de Producto.xls descargado de la VUE"),
    empresa: str | None = Form(None, description="Nombre de la empresa, para rotular el registro"),
):
    """Importa un archivo de la VUE. Actualiza lo existente y agrega lo nuevo.

    El RUC sale del propio archivo, asi que no hace falta indicarlo: subir el
    archivo de otra empresa no pisa el de la primera.
    """
    datos = await file.read()
    sufijo = Path(file.filename or "").suffix.lower() or ".xls"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=sufijo)
    tmp.write(datos)
    tmp.flush()

    try:
        libro = xlrd.open_workbook(tmp.name)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"No se pudo abrir el archivo. La VUE entrega un .xls antiguo; "
                   f"si lo abriste y guardaste como .xlsx ya no sirve. Detalle: {e}")

    hoja = libro.sheet_by_index(0)
    idx = _mapear(hoja)

    faltan = [c for c in ("ruc", "codigo_producto", "subpartida", "pais_cod") if c not in idx]
    if faltan:
        raise HTTPException(
            status_code=400,
            detail=f"El archivo no tiene las columnas esperadas de la VUE: faltan {faltan}. "
                   f"Debe ser el 'Lista de Producto' con la fila de nombres tecnicos "
                   f"(reg_agro, prdt_cd, hc, org_ntn_cd).")

    def col(fila, campo):
        i = idx.get(campo)
        return _texto(hoja.cell_value(fila, i)) if i is not None else None

    filas, rucs, descartadas = {}, set(), 0
    for f in range(DATOS_DESDE, hoja.nrows):
        ruc = col(f, "ruc")
        codigo = col(f, "codigo_producto")
        subpartida = col(f, "subpartida")
        pais = col(f, "pais_cod")
        if not (ruc and codigo and subpartida and pais):
            descartadas += 1
            continue
        rucs.add(ruc)
        # Deduplica dentro del propio archivo: el de Expoflor trae 524 filas
        # con 493 combinaciones unicas, hay repetidos exactos.
        filas[(ruc, codigo, subpartida, pais)] = {
            "ruc": ruc,
            "empresa": (empresa or "").strip() or None,
            "actividad_comercial": col(f, "actividad_comercial"),
            "tipo_producto": col(f, "tipo_producto"),
            "codigo_producto": codigo,
            "subpartida": subpartida,
            "partida": subpartida[:10],
            "nombre_producto": col(f, "nombre_producto"),
            "nombre_cientifico": col(f, "nombre_cientifico"),
            "pais_cod": pais.upper(),
        }

    if not filas:
        raise HTTPException(status_code=400,
                            detail="El archivo no trae ninguna fila de datos utilizable.")

    with engine.begin() as conn:
        # El pais se resuelve contra countries.cod_agroca (ISO alfa-2).
        catalogo = {r[0]: str(r[1]) for r in conn.execute(text("""
            SELECT cod_agroca, id FROM countries WHERE cod_agroca IS NOT NULL
        """)).all()}

        sin_pais = set()
        tuplas = []
        for v in filas.values():
            cid = catalogo.get(v["pais_cod"])
            if not cid:
                sin_pais.add(v["pais_cod"])
            tuplas.append((
                v["ruc"], v["empresa"], v["actividad_comercial"], v["tipo_producto"],
                v["codigo_producto"], v["subpartida"], v["partida"],
                v["nombre_producto"], v["nombre_cientifico"], v["pais_cod"], cid,
                file.filename,
            ))

        antes = conn.execute(text("SELECT count(*) FROM vue_productos")).scalar()

        cursor = conn.connection.cursor()
        execute_values(cursor, """
            INSERT INTO vue_productos (
                ruc, empresa, actividad_comercial, tipo_producto,
                codigo_producto, subpartida, partida,
                nombre_producto, nombre_cientifico, pais_cod, country_id, archivo
            ) VALUES %s
            ON CONFLICT (ruc, codigo_producto, subpartida, pais_cod) DO UPDATE SET
                empresa           = COALESCE(EXCLUDED.empresa, vue_productos.empresa),
                actividad_comercial = EXCLUDED.actividad_comercial,
                tipo_producto     = EXCLUDED.tipo_producto,
                partida           = EXCLUDED.partida,
                nombre_producto   = EXCLUDED.nombre_producto,
                nombre_cientifico = EXCLUDED.nombre_cientifico,
                country_id        = EXCLUDED.country_id,
                archivo           = EXCLUDED.archivo,
                actualizado_at    = now()
        """, tuplas, page_size=1000)

        despues = conn.execute(text("SELECT count(*) FROM vue_productos")).scalar()

    return {
        "archivo": file.filename,
        "rucs": sorted(rucs),
        "filas_en_archivo": hoja.nrows - DATOS_DESDE,
        "autorizaciones_unicas": len(filas),
        "descartadas_sin_datos": descartadas,
        "nuevas": despues - antes,
        "actualizadas": len(filas) - (despues - antes),
        "paises_sin_equivalencia": sorted(sin_pais),
    }
