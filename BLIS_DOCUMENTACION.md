# BLIS — Bellaflor Logistics Intelligence System
## Documentación Técnica Completa con Código · v1.0 · Agosto 2026

---

## Índice

1. [Descripción del proyecto](#1-descripción-del-proyecto)
2. [Stack tecnológico](#2-stack-tecnológico)
3. [Estructura del proyecto](#3-estructura-del-proyecto)
4. [Variables de entorno](#4-variables-de-entorno)
5. [Configuración de deploy — render.yaml](#5-configuración-de-deploy--renderyaml)
6. [requirements.txt](#6-requirementstxt)
7. [Backend — main.py](#7-backend--mainpy)
8. [Backend — database/connection.py](#8-backend--databaseconnectionpy)
9. [Backend — database/helpers.py](#9-backend--databasehelperspy)
10. [Backend — API health.py y db_test.py](#10-backend--api-healthpy-y-db_testpy)
11. [Backend — API dashboard.py](#11-backend--api-dashboardpy)
12. [Backend — API ingresos_locales.py](#12-backend--api-ingresos_localespy)
13. [Backend — API dartis_import.py](#13-backend--api-dartis_importpy)
14. [Backend — API cotizacion.py](#14-backend--api-cotizacionpy)
15. [Backend — API species.py](#15-backend--api-speciespy)
16. [Backend — API airlines.py](#16-backend--api-airlinespy)
17. [Backend — API airline_tariffs.py](#17-backend--api-airline_tariffspy)
18. [Backend — API airports.py](#18-backend--api-airportspy)
19. [Backend — API customers.py](#19-backend--api-customerspy)
20. [Backend — API cargo_agencies.py](#20-backend--api-cargo_agenciespy)
21. [Backend — API farms.py](#21-backend--api-farmspy)
22. [Schemas Pydantic](#22-schemas-pydantic)
23. [Frontend — layout.js](#23-frontend--layoutjs)
24. [Frontend — sidebar.html](#24-frontend--sidebarhtml)
25. [Frontend — ingresos-locales.html y .js](#25-frontend--ingresos-localeshtml-y-js)
26. [Frontend — dartis-import.html y .js](#26-frontend--dartis-importhtml-y-js)
27. [Frontend — dashboard.html](#27-frontend--dashboardhtml)
28. [Base de datos — tablas y relaciones](#28-base-de-datos--tablas-y-relaciones)
29. [Migración aplicada](#29-migración-aplicada)
30. [Despliegue en Render.com](#30-despliegue-en-rendercom)
31. [Desarrollo local — paso a paso](#31-desarrollo-local--paso-a-paso)
32. [GitHub](#32-github)
33. [Troubleshooting](#33-troubleshooting)

---

## 1. Descripción del proyecto

BLIS es una plataforma web interna de Bellaflor Group para análisis, simulación y gestión de costos logísticos de exportación de flores. Centraliza datos de múltiples fuentes — Dartis (sistema de ventas), Google Apps Script (ingresos locales), y una base de datos propia en Supabase — en una interfaz de administración unificada.

**URL de producción:** `https://blis-hxu1.onrender.com`  
**Repositorio:** `https://github.com/freddyerazo/BellaflorLogis`  
**Plan actual:** Free (spin-down tras 15 min) → Starter $7/mes para siempre activo

---

## 2. Stack tecnológico

| Capa | Tecnología | Versión |
|---|---|---|
| Backend | FastAPI | 0.141+ |
| Servidor ASGI | Uvicorn | 0.52+ |
| ORM | SQLAlchemy Core | 2.x |
| Driver PostgreSQL | psycopg2-binary | 2.9+ |
| Base de datos | PostgreSQL (Supabase) | 15 |
| Excel parsing | openpyxl | 3.1+ |
| HTTP cliente | httpx | 0.28+ |
| Multipart | python-multipart | — |
| Frontend | HTML + JS vanilla | ES2022 |
| Iconos | Phosphor Icons | 2.1.1 |
| Deploy | Render.com | — |
| Versiones | GitHub | — |

---

## 3. Estructura del proyecto

```
BLIS/
├── backend/
│   ├── requirements.txt              # dependencias Python (fuente de verdad para Render)
│   └── app/
│       ├── main.py
│       ├── api/
│       │   ├── health.py
│       │   ├── db_test.py
│       │   ├── dashboard.py
│       │   ├── cotizacion.py
│       │   ├── dartis_import.py
│       │   ├── ingresos_locales.py
│       │   ├── species.py
│       │   ├── varieties.py
│       │   ├── product_sizes.py
│       │   ├── box_types.py
│       │   ├── airports.py
│       │   ├── countries.py
│       │   ├── customers.py
│       │   ├── airlines.py
│       │   ├── airline_tariffs.py
│       │   ├── cargo_agencies.py
│       │   ├── farms.py
│       │   ├── roles.py
│       │   └── profiles.py
│       ├── schemas/
│       │   ├── species.py
│       │   ├── varieties.py
│       │   ├── product_sizes.py
│       │   ├── box_types.py
│       │   ├── airports.py
│       │   ├── customers.py
│       │   ├── airlines.py
│       │   ├── airline_tariffs.py
│       │   ├── cargo_agencies.py
│       │   └── farms.py
│       └── database/
│           ├── connection.py
│           └── helpers.py
├── frontend/
│   ├── index.html
│   ├── css/styles.css
│   ├── js/layout.js
│   ├── components/sidebar.html
│   └── pages/
│       ├── dashboard.html / dashboard.js
│       ├── ingresos-locales.html / ingresos-locales.js
│       ├── dartis-import.html / dartis-import.js
│       ├── cotizaciones.html
│       ├── clientes.html
│       ├── especies.html
│       ├── variedades.html
│       ├── grados.html
│       ├── tipos-caja.html
│       ├── aeropuertos.html
│       ├── aerolineas.html
│       ├── tarifas-aerolinea.html
│       ├── cargo-agencies.html
│       ├── farms.html
│       └── configuracion.html
├── database/
│   ├── schema/schema_v1.sql
│   ├── views/views_v1.sql
│   └── seeds/seeds_v1.sql
├── requirements.txt
├── render.yaml
└── .gitignore
```

---

## 4. Variables de entorno

Archivo `backend/.env` — **nunca se commitea al repositorio**.

```env
DATABASE_URL=postgresql://postgres.xxxx:password@aws-0-us-east-1.pooler.supabase.com:5432/postgres
INGRESOS_LOCALES_URL=https://script.google.com/macros/s/.../exec
```

| Variable | Descripción |
|---|---|
| `DATABASE_URL` | Cadena de conexión PostgreSQL de Supabase. Obtenida en: Supabase → Project Settings → Database → Connection string (mode: Session) |
| `INGRESOS_LOCALES_URL` | URL pública del Web App de Google Apps Script de IngresosLocales. Se regenera cada vez que se publica el GAS. |

> ⚠️ Nunca compartir el valor de `DATABASE_URL` en el chat ni en el código.

---

## 5. Configuración de deploy — render.yaml

```yaml
services:
  - type: web
    name: blis-api
    runtime: python
    buildCommand: pip install -r backend/requirements.txt
    startCommand: cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
    plan: free
    envVars:
      - key: DATABASE_URL
        sync: false
      - key: INGRESOS_LOCALES_URL
        sync: false
      - key: PYTHON_VERSION
        value: 3.11.0
```

**Notas importantes:**
- `buildCommand` usa `backend/requirements.txt` (ruta desde la raíz del repo)
- `startCommand` hace `cd backend` antes de lanzar uvicorn para que Python encuentre el módulo `app`
- Las variables con `sync: false` se ingresan manualmente en Render → Environment

---

## 6. requirements.txt

### `backend/requirements.txt` (usado por Render)

```
fastapi
uvicorn[standard]
sqlalchemy
psycopg2-binary
python-dotenv
supabase
pydantic
alembic
openpyxl
python-multipart
```

### `requirements.txt` (raíz, usado localmente)

```
fastapi
uvicorn[standard]
sqlalchemy
psycopg2-binary
python-dotenv
supabase
pydantic
alembic
openpyxl
python-multipart
```

> `python-multipart` es requerido por FastAPI para recibir archivos con `File(...)`.  
> `uvicorn[standard]` incluye `uvloop` y `httptools` para mejor performance en Linux.

---

## 7. Backend — main.py

```python
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.health import router as health_router
from app.api.db_test import router as db_router
from app.api.species import router as species_router
from app.api.varieties import router as varieties_router
from app.api.product_sizes import router as product_sizes_router
from app.api.box_types import router as box_router
from app.api.airports import router as airports_router
from app.api.countries import router as countries_router
from app.api.customers import router as customers_router
from app.api.airlines import router as airlines_router
from app.api.roles import router as roles_router
from app.api.profiles import router as profiles_router
from app.api.dashboard import router as dashboard_router
from app.api.cotizacion import router as cotizacion_router
from app.api.airline_tariffs import router as airline_tariffs_router
from app.api.cargo_agencies import router as cargo_agencies_router
from app.api.farms import router as farms_router
from app.api.dartis_import import router as dartis_router
from app.api.ingresos_locales import router as ingresos_locales_router

app = FastAPI(
    title="BLIS API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(db_router)
app.include_router(species_router, prefix="/api")
app.include_router(varieties_router, prefix="/api")
app.include_router(product_sizes_router, prefix="/api")
app.include_router(box_router, prefix="/api")
app.include_router(airports_router, prefix="/api")
app.include_router(countries_router, prefix="/api")
app.include_router(customers_router, prefix="/api")
app.include_router(airlines_router, prefix="/api")
app.include_router(roles_router, prefix="/api")
app.include_router(profiles_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(cotizacion_router, prefix="/api")
app.include_router(airline_tariffs_router, prefix="/api")
app.include_router(cargo_agencies_router, prefix="/api")
app.include_router(farms_router, prefix="/api")
app.include_router(dartis_router, prefix="/api")
app.include_router(ingresos_locales_router, prefix="/api")

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
```

---

## 8. Backend — database/connection.py

```python
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
```

---

## 9. Backend — database/helpers.py

```python
from uuid import UUID


def build_set_clause(data: dict) -> str:
    return ", ".join(f"{key} = :{key}" for key in data)


def jsonable_params(data: dict) -> dict:
    return {
        key: (str(value) if isinstance(value, UUID) else value)
        for key, value in data.items()
    }
```

---

## 10. Backend — API health.py y db_test.py

### health.py

```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health():
    return {
        "status": "ok",
        "system": "BLIS"
    }
```

### db_test.py

```python
from fastapi import APIRouter
from sqlalchemy import text

from app.database.connection import engine

router = APIRouter()

@router.get("/db-test")
def db_test():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT NOW()"))
            row = result.fetchone()
            return {
                "status": "connected",
                "database_time": str(row[0])
            }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
```

---

## 11. Backend — API dashboard.py

```python
from fastapi import APIRouter
from sqlalchemy import text

from app.database.connection import engine

router = APIRouter()


@router.get("/dashboard/summary")
def dashboard_summary():
    with engine.connect() as conn:
        summary = conn.execute(
            text("""
                SELECT
                    (SELECT COUNT(*) FROM species)          AS species,
                    (SELECT COUNT(*) FROM varieties)        AS varieties,
                    (SELECT COUNT(*) FROM product_sizes)    AS product_sizes,
                    (SELECT COUNT(*) FROM box_types)        AS box_types,
                    (SELECT COUNT(*) FROM airports)         AS airports,
                    (SELECT COUNT(*) FROM airlines)         AS airlines,
                    (SELECT COUNT(*) FROM customers)        AS customers,
                    (SELECT COUNT(*) FROM markets)          AS markets,
                    (SELECT COUNT(*) FROM providers)        AS providers,
                    (SELECT COUNT(*) FROM incoterms)        AS incoterms,
                    (SELECT COUNT(*) FROM cost_components)  AS cost_components,
                    (SELECT COUNT(*) FROM roles)            AS roles,
                    (SELECT COUNT(*) FROM profiles)         AS profiles,
                    (SELECT COUNT(*) FROM scenario_headers) AS scenarios
            """)
        ).mappings().first()

        top_species = conn.execute(
            text("""
                SELECT s.name AS species_name, COUNT(v.id) AS variety_count
                FROM species s
                LEFT JOIN varieties v ON v.species_id = s.id AND v.active = true
                WHERE s.active = true
                GROUP BY s.id, s.name
                ORDER BY variety_count DESC
                LIMIT 5
            """)
        ).mappings().all()

        box_distribution = conn.execute(
            text("""
                SELECT box_code, box_name, length_cm, width_cm, height_cm
                FROM box_types
                WHERE active = true
                ORDER BY length_cm DESC
                LIMIT 8
            """)
        ).mappings().all()

        last_scenario = conn.execute(
            text("""
                SELECT
                    sh.scenario_code,
                    sh.scenario_name,
                    sh.created_at,
                    COUNT(sd.id) AS detail_lines,
                    SUM(sd.boxes) AS total_boxes,
                    SUM(sd.chargeable_weight_kg) AS total_chargeable_kg,
                    (
                        SELECT SUM(scr.amount)
                        FROM scenario_cost_results scr
                        WHERE scr.scenario_id = sh.id
                    ) AS total_cost_usd
                FROM scenario_headers sh
                LEFT JOIN scenario_details sd ON sd.scenario_id = sh.id
                GROUP BY sh.id, sh.scenario_code, sh.scenario_name, sh.created_at
                ORDER BY sh.created_at DESC
                LIMIT 1
            """)
        ).mappings().first()

        cost_breakdown = []
        if last_scenario:
            cost_breakdown = conn.execute(
                text("""
                    SELECT cc.component_name, scr.amount, scr.currency_code
                    FROM scenario_cost_results scr
                    JOIN cost_components cc ON cc.id = scr.cost_component_id
                    JOIN scenario_headers sh ON sh.id = scr.scenario_id
                    ORDER BY sh.created_at DESC, scr.amount DESC
                    LIMIT 10
                """)
            ).mappings().all()

        return {
            "summary": dict(summary),
            "top_species": [dict(r) for r in top_species],
            "box_distribution": [dict(r) for r in box_distribution],
            "last_scenario": dict(last_scenario) if last_scenario else None,
            "cost_breakdown": [dict(r) for r in cost_breakdown],
        }
```

---

## 12. Backend — API ingresos_locales.py

```python
import os
import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException

load_dotenv()

router = APIRouter()


def _get_gas_url() -> str:
    return os.getenv("INGRESOS_LOCALES_URL", "")


@router.get("/ingresos-locales/datos")
async def get_datos():
    """Proxy hacia el endpoint JSON del GAS de IngresosLocales."""
    gas_url = _get_gas_url()
    if not gas_url:
        raise HTTPException(
            status_code=501,
            detail="INGRESOS_LOCALES_URL no configurada en .env"
        )
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=120) as client:
            resp = await client.get(gas_url)
            resp.raise_for_status()
            return resp.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="GAS no respondio en 120s — intenta de nuevo")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Error GAS: {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
```

---

## 13. Backend — API dartis_import.py

```python
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

    # Deduplicar por clave única — ON CONFLICT falla si hay duplicados en el mismo batch
    dedup = {}
    for p in params:
        key = (p["id_pedido"], p["guia_madre"], p["guia_hija"], p["tipo_caja"])
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
    execute_values(raw, """
        INSERT INTO dartis_ventas (
            fecha, dae, id_comercializadora, id_pedido,
            empresa, cliente, destinatario, postcosecha, especie,
            guia_madre, guia_hija, tipo_caja,
            total_piezas, total_tallos, total_dolares
        ) VALUES %s
        ON CONFLICT (id_pedido, guia_madre, guia_hija, tipo_caja) DO UPDATE SET
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
    - Actualiza customer_id en dartis_ventas con un solo UPDATE masivo.
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

    faltantes = sorted(cl for cl in clientes if cl.lower() not in existentes)

    if faltantes:
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
```

---

## 14. Backend — API cotizacion.py

```python
from fastapi import APIRouter
from sqlalchemy import text

from app.database.connection import engine

router = APIRouter()


@router.get("/cotizacion/catalogo")
def get_catalogo():
    """Devuelve todos los catálogos necesarios para el wizard de cotización."""
    with engine.connect() as conn:

        paises_origen = conn.execute(text("""
            SELECT DISTINCT c.id, c.code, c.name
            FROM countries c
            INNER JOIN airports a  ON a.country_id = c.id
            INNER JOIN airline_tariffs t ON t.origin_airport_id = a.id
                AND t.active = true
                AND t.valid_from <= CURRENT_DATE
                AND (t.valid_to IS NULL OR t.valid_to >= CURRENT_DATE)
            WHERE c.active = true
            ORDER BY c.name
        """)).mappings().all()

        paises_destino = conn.execute(text("""
            SELECT DISTINCT c.id, c.code, c.name
            FROM countries c
            INNER JOIN airports a  ON a.country_id = c.id
            INNER JOIN airline_tariffs t ON t.destination_airport_id = a.id
                AND t.active = true
                AND t.valid_from <= CURRENT_DATE
                AND (t.valid_to IS NULL OR t.valid_to >= CURRENT_DATE)
            WHERE c.active = true
            ORDER BY c.name
        """)).mappings().all()

        especies = conn.execute(text(
            "SELECT * FROM species WHERE active = true ORDER BY name"
        )).mappings().all()

        variedades = conn.execute(text(
            "SELECT id, species_id, code, name FROM varieties WHERE active = true ORDER BY name"
        )).mappings().all()

        grados = conn.execute(text("""
            SELECT ps.id, ps.size_code, ps.description, s.name AS species_name
            FROM product_sizes ps
            JOIN species s ON s.id = ps.species_id
            WHERE ps.active = true
            ORDER BY s.name, ps.size_code
        """)).mappings().all()

        box_types = conn.execute(text(
            "SELECT * FROM box_types WHERE active = true ORDER BY length_cm DESC"
        )).mappings().all()

        aerolineas = conn.execute(text(
            "SELECT * FROM airlines WHERE active = true ORDER BY airline_name"
        )).mappings().all()

        rutas_activas = conn.execute(text("""
            SELECT DISTINCT
                t.airline_id,
                t.origin_airport_id,
                t.destination_airport_id
            FROM airline_tariffs t
            WHERE t.active = true
                AND t.valid_from <= CURRENT_DATE
                AND (t.valid_to IS NULL OR t.valid_to >= CURRENT_DATE)
        """)).mappings().all()

        aeropuertos = conn.execute(text("""
            SELECT a.*, c.code AS country_code, c.name AS country_name
            FROM airports a
            LEFT JOIN countries c ON c.id = a.country_id
            WHERE a.active = true
            ORDER BY a.city
        """)).mappings().all()

        proveedores = []
        try:
            proveedores = conn.execute(text(
                "SELECT * FROM providers WHERE active = true ORDER BY id"
            )).mappings().all()
        except Exception:
            pass

        incoterms_list = []
        try:
            incoterms_list = conn.execute(text(
                "SELECT * FROM incoterms ORDER BY id"
            )).mappings().all()
        except Exception:
            pass

        fx_rates = []
        try:
            fx_rates = conn.execute(text(
                "SELECT * FROM exchange_rates ORDER BY rate_date DESC LIMIT 10"
            )).mappings().all()
        except Exception:
            pass

    return {
        "paises_origen":  [dict(r) for r in paises_origen],
        "paises_destino": [dict(r) for r in paises_destino],
        "especies":       [dict(r) for r in especies],
        "variedades":     [dict(r) for r in variedades],
        "grados":         [dict(r) for r in grados],
        "box_types":      [dict(r) for r in box_types],
        "aerolineas":     [dict(r) for r in aerolineas],
        "rutas_activas":  [dict(r) for r in rutas_activas],
        "aeropuertos":    [dict(r) for r in aeropuertos],
        "proveedores":    [dict(r) for r in proveedores],
        "incoterms":      [dict(r) for r in incoterms_list],
        "exchange_rates": [dict(r) for r in fx_rates],
    }
```

---

## 15. Backend — API species.py

```python
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.database.connection import engine
from app.database.helpers import build_set_clause, jsonable_params
from app.schemas.species import SpeciesCreate, SpeciesUpdate

router = APIRouter()


@router.get("/species")
def list_species():
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT * FROM species ORDER BY code")
        ).mappings().all()


@router.post("/species", status_code=201)
def create_species(payload: SpeciesCreate):
    with engine.begin() as conn:
        return conn.execute(
            text("INSERT INTO species (code, name) VALUES (:code, :name) RETURNING *"),
            payload.model_dump(),
        ).mappings().first()


@router.put("/species/{species_id}")
def update_species(species_id: str, payload: SpeciesUpdate):
    data = jsonable_params(payload.model_dump(exclude_unset=True))
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    set_clause = build_set_clause(data)
    data["id"] = species_id
    with engine.begin() as conn:
        row = conn.execute(
            text(f"UPDATE species SET {set_clause}, updated_at = now() WHERE id = :id RETURNING *"),
            data,
        ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Species not found")
    return row


@router.delete("/species/{species_id}")
def delete_species(species_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            text("UPDATE species SET active = false, inactive_date = now(), updated_at = now() WHERE id = :id RETURNING *"),
            {"id": species_id},
        ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Species not found")
    return row
```

---

## 16. Backend — API airlines.py

```python
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.database.connection import engine
from app.database.helpers import build_set_clause, jsonable_params
from app.schemas.airlines import AirlineCreate, AirlineUpdate

router = APIRouter()


@router.get("/airlines")
def list_airlines():
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT * FROM airlines ORDER BY airline_code")
        ).mappings().all()


@router.post("/airlines", status_code=201)
def create_airline(payload: AirlineCreate):
    with engine.begin() as conn:
        return conn.execute(
            text("INSERT INTO airlines (airline_code, airline_name) VALUES (:airline_code, :airline_name) RETURNING *"),
            payload.model_dump(),
        ).mappings().first()


@router.put("/airlines/{airline_id}")
def update_airline(airline_id: str, payload: AirlineUpdate):
    data = jsonable_params(payload.model_dump(exclude_unset=True))
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    set_clause = build_set_clause(data)
    data["id"] = airline_id
    with engine.begin() as conn:
        row = conn.execute(
            text(f"UPDATE airlines SET {set_clause}, updated_at = now() WHERE id = :id RETURNING *"),
            data,
        ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Airline not found")
    return row


@router.delete("/airlines/{airline_id}")
def delete_airline(airline_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            text("UPDATE airlines SET active = false, inactive_date = now(), updated_at = now() WHERE id = :id RETURNING *"),
            {"id": airline_id},
        ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Airline not found")
    return row
```

---

## 17. Backend — API airline_tariffs.py

```python
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.database.connection import engine
from app.database.helpers import build_set_clause, jsonable_params
from app.schemas.airline_tariffs import AirlineTariffCreate, AirlineTariffUpdate

router = APIRouter()


@router.get("/airline-tariffs")
def list_airline_tariffs():
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                t.id, t.airline_id, t.origin_airport_id, t.destination_airport_id,
                t.cost_per_kg, t.minimum_charge, t.currency_code,
                t.valid_from, t.valid_to, t.active, t.created_at,
                al.airline_code, al.airline_name,
                ao.iata_code AS origin_iata,  ao.city AS origin_city,
                ad.iata_code AS destination_iata, ad.city AS destination_city
            FROM airline_tariffs t
            JOIN airlines al ON al.id = t.airline_id
            JOIN airports ao ON ao.id = t.origin_airport_id
            JOIN airports ad ON ad.id = t.destination_airport_id
            ORDER BY al.airline_name, ao.iata_code, ad.iata_code, t.valid_from DESC
        """)).mappings().all()
        return [dict(r) for r in rows]


@router.post("/airline-tariffs", status_code=201)
def create_airline_tariff(payload: AirlineTariffCreate):
    data = jsonable_params(payload.model_dump())
    with engine.begin() as conn:
        row = conn.execute(text("""
            INSERT INTO airline_tariffs
                (airline_id, origin_airport_id, destination_airport_id,
                 cost_per_kg, minimum_charge, currency_code, valid_from, valid_to)
            VALUES
                (:airline_id, :origin_airport_id, :destination_airport_id,
                 :cost_per_kg, :minimum_charge, :currency_code, :valid_from, :valid_to)
            RETURNING *
        """), data).mappings().first()
        return dict(row)


@router.put("/airline-tariffs/{tariff_id}")
def update_airline_tariff(tariff_id: str, payload: AirlineTariffUpdate):
    data = jsonable_params(payload.model_dump(exclude_unset=True))
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    set_clause = build_set_clause(data)
    data["id"] = tariff_id
    with engine.begin() as conn:
        row = conn.execute(
            text(f"UPDATE airline_tariffs SET {set_clause} WHERE id = :id RETURNING *"),
            data,
        ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Tarifa no encontrada")
    return dict(row)


@router.delete("/airline-tariffs/{tariff_id}")
def delete_airline_tariff(tariff_id: str):
    with engine.begin() as conn:
        row = conn.execute(text("""
            UPDATE airline_tariffs SET active = false WHERE id = :id RETURNING *
        """), {"id": tariff_id}).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Tarifa no encontrada")
    return dict(row)
```

---

## 18. Backend — API airports.py

```python
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.database.connection import engine
from app.database.helpers import build_set_clause, jsonable_params
from app.schemas.airports import AirportCreate, AirportUpdate

router = APIRouter()


@router.get("/airports")
def list_airports():
    with engine.connect() as conn:
        return conn.execute(
            text("""
                SELECT a.*, c.code AS country_code, c.name AS country_name
                FROM airports a
                LEFT JOIN countries c ON c.id = a.country_id
                ORDER BY a.iata_code
            """)
        ).mappings().all()


@router.post("/airports", status_code=201)
def create_airport(payload: AirportCreate):
    data = jsonable_params(payload.model_dump())
    with engine.begin() as conn:
        return conn.execute(
            text("INSERT INTO airports (iata_code, airport_name, city, country_id) VALUES (:iata_code, :airport_name, :city, :country_id) RETURNING *"),
            data,
        ).mappings().first()


@router.put("/airports/{airport_id}")
def update_airport(airport_id: str, payload: AirportUpdate):
    data = jsonable_params(payload.model_dump(exclude_unset=True))
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    set_clause = build_set_clause(data)
    data["id"] = airport_id
    with engine.begin() as conn:
        row = conn.execute(
            text(f"UPDATE airports SET {set_clause}, updated_at = now() WHERE id = :id RETURNING *"),
            data,
        ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Airport not found")
    return row


@router.delete("/airports/{airport_id}")
def delete_airport(airport_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            text("UPDATE airports SET active = false, updated_at = now() WHERE id = :id RETURNING *"),
            {"id": airport_id},
        ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Airport not found")
    return row
```

---

## 19. Backend — API customers.py

```python
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.database.connection import engine
from app.database.helpers import build_set_clause, jsonable_params
from app.schemas.customers import CustomerCreate, CustomerUpdate

router = APIRouter()


@router.get("/customers")
def list_customers():
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT * FROM customers ORDER BY customer_code")
        ).mappings().all()


@router.post("/customers", status_code=201)
def create_customer(payload: CustomerCreate):
    with engine.begin() as conn:
        return conn.execute(
            text("""
                INSERT INTO customers (customer_code, customer_name, contact_name, email, phone)
                VALUES (:customer_code, :customer_name, :contact_name, :email, :phone)
                RETURNING *
            """),
            payload.model_dump(),
        ).mappings().first()


@router.put("/customers/{customer_id}")
def update_customer(customer_id: str, payload: CustomerUpdate):
    data = jsonable_params(payload.model_dump(exclude_unset=True))
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    set_clause = build_set_clause(data)
    data["id"] = customer_id
    with engine.begin() as conn:
        row = conn.execute(
            text(f"UPDATE customers SET {set_clause}, updated_at = now() WHERE id = :id RETURNING *"),
            data,
        ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return row


@router.delete("/customers/{customer_id}")
def delete_customer(customer_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            text("UPDATE customers SET active = false, inactive_date = now(), updated_at = now() WHERE id = :id RETURNING *"),
            {"id": customer_id},
        ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return row
```

---

## 20. Backend — API cargo_agencies.py

```python
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.database.connection import engine
from app.database.helpers import build_set_clause, jsonable_params
from app.schemas.cargo_agencies import CargoAgencyCreate, CargoAgencyUpdate

router = APIRouter()


@router.get("/cargo-agencies")
def list_cargo_agencies():
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT * FROM cargo_agencies ORDER BY name")
        ).mappings().all()


@router.get("/cargo-agencies/{agency_id}")
def get_cargo_agency(agency_id: str):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM cargo_agencies WHERE id = :id"), {"id": agency_id}
        ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Cargo agency not found")
    return row


@router.post("/cargo-agencies", status_code=201)
def create_cargo_agency(payload: CargoAgencyCreate):
    with engine.begin() as conn:
        return conn.execute(
            text("INSERT INTO cargo_agencies (code, name, ocr_variants, type, country) VALUES (:code, :name, :ocr_variants, :type, :country) RETURNING *"),
            {"code": payload.code, "name": payload.name, "ocr_variants": payload.ocr_variants or [], "type": payload.type, "country": payload.country},
        ).mappings().first()


@router.put("/cargo-agencies/{agency_id}")
def update_cargo_agency(agency_id: str, payload: CargoAgencyUpdate):
    data = jsonable_params(payload.model_dump(exclude_unset=True))
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    set_clause = build_set_clause(data)
    data["id"] = agency_id
    with engine.begin() as conn:
        row = conn.execute(
            text(f"UPDATE cargo_agencies SET {set_clause}, updated_at = now() WHERE id = :id RETURNING *"),
            data,
        ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Cargo agency not found")
    return row


@router.delete("/cargo-agencies/{agency_id}")
def delete_cargo_agency(agency_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            text("UPDATE cargo_agencies SET active = false, inactive_date = now(), updated_at = now() WHERE id = :id RETURNING *"),
            {"id": agency_id},
        ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Cargo agency not found")
    return row


@router.get("/cargo-agencies/resolve/{ocr_name}")
def resolve_agency_by_ocr(ocr_name: str):
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT * FROM cargo_agencies WHERE active = true
                AND (LOWER(name) = LOWER(:name) OR :name = ANY(ocr_variants)
                     OR LOWER(:name) = ANY(SELECT LOWER(v) FROM unnest(ocr_variants) v))
                LIMIT 1
            """),
            {"name": ocr_name},
        ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="No matching agency found")
    return row
```

---

## 21. Backend — API farms.py

```python
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.database.connection import engine
from app.database.helpers import build_set_clause, jsonable_params
from app.schemas.farms import FarmCreate, FarmUpdate

router = APIRouter()


@router.get("/farms")
def list_farms():
    with engine.connect() as conn:
        return conn.execute(text("SELECT * FROM farms ORDER BY name")).mappings().all()


@router.get("/farms/{farm_id}")
def get_farm(farm_id: str):
    with engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM farms WHERE id = :id"), {"id": farm_id}).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Farm not found")
    return row


@router.post("/farms", status_code=201)
def create_farm(payload: FarmCreate):
    with engine.begin() as conn:
        return conn.execute(
            text("INSERT INTO farms (code, name, ocr_variants, dartis_postcosecha) VALUES (:code, :name, :ocr_variants, :dartis_postcosecha) RETURNING *"),
            {"code": payload.code, "name": payload.name, "ocr_variants": payload.ocr_variants or [], "dartis_postcosecha": payload.dartis_postcosecha},
        ).mappings().first()


@router.put("/farms/{farm_id}")
def update_farm(farm_id: str, payload: FarmUpdate):
    data = jsonable_params(payload.model_dump(exclude_unset=True))
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    set_clause = build_set_clause(data)
    data["id"] = farm_id
    with engine.begin() as conn:
        row = conn.execute(
            text(f"UPDATE farms SET {set_clause}, updated_at = now() WHERE id = :id RETURNING *"),
            data,
        ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Farm not found")
    return row


@router.delete("/farms/{farm_id}")
def delete_farm(farm_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            text("UPDATE farms SET active = false, inactive_date = now(), updated_at = now() WHERE id = :id RETURNING *"),
            {"id": farm_id},
        ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Farm not found")
    return row


@router.get("/farms/resolve/{ocr_name}")
def resolve_farm_by_ocr(ocr_name: str):
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT * FROM farms WHERE active = true
                AND (LOWER(name) = LOWER(:name) OR :name = ANY(ocr_variants)
                     OR LOWER(:name) = ANY(SELECT LOWER(v) FROM unnest(ocr_variants) v))
                LIMIT 1
            """),
            {"name": ocr_name},
        ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="No matching farm found")
    return row
```

---

## 22. Schemas Pydantic

### schemas/species.py

```python
from typing import Optional
from pydantic import BaseModel

class SpeciesCreate(BaseModel):
    code: str
    name: str

class SpeciesUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    active: Optional[bool] = None
```

### schemas/customers.py

```python
from typing import Optional
from pydantic import BaseModel

class CustomerCreate(BaseModel):
    customer_code: str
    customer_name: str
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

class CustomerUpdate(BaseModel):
    customer_code: Optional[str] = None
    customer_name: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    active: Optional[bool] = None
```

### schemas/cargo_agencies.py

```python
from typing import List, Optional
from pydantic import BaseModel

class CargoAgencyCreate(BaseModel):
    code: str
    name: str
    ocr_variants: Optional[List[str]] = []
    type: Optional[str] = "aerea"
    country: Optional[str] = "Ecuador"

class CargoAgencyUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    ocr_variants: Optional[List[str]] = None
    type: Optional[str] = None
    country: Optional[str] = None
    active: Optional[bool] = None
```

### schemas/farms.py

```python
from typing import List, Optional
from pydantic import BaseModel

class FarmCreate(BaseModel):
    code: str
    name: str
    ocr_variants: Optional[List[str]] = []
    dartis_postcosecha: Optional[str] = None

class FarmUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    ocr_variants: Optional[List[str]] = None
    dartis_postcosecha: Optional[str] = None
    active: Optional[bool] = None
```

### schemas/airline_tariffs.py

```python
from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel

class AirlineTariffCreate(BaseModel):
    airline_id: str
    origin_airport_id: str
    destination_airport_id: str
    cost_per_kg: Decimal
    minimum_charge: Optional[Decimal] = None
    currency_code: Optional[str] = "USD"
    valid_from: date
    valid_to: Optional[date] = None

class AirlineTariffUpdate(BaseModel):
    airline_id: Optional[str] = None
    origin_airport_id: Optional[str] = None
    destination_airport_id: Optional[str] = None
    cost_per_kg: Optional[Decimal] = None
    minimum_charge: Optional[Decimal] = None
    currency_code: Optional[str] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    active: Optional[bool] = None
```

---

## 23. Frontend — layout.js

```javascript
async function initLayout() {
  const sidebarContainer = document.getElementById("sidebar");
  if (!sidebarContainer) return;

  try {
    const response = await fetch("/components/sidebar.html");
    sidebarContainer.innerHTML = await response.text();

    const currentPage = document.body.dataset.page;

    sidebarContainer.querySelectorAll("a[data-page]").forEach((link) => {
      if (link.dataset.page === currentPage) {
        link.classList.add("active");
        const group = link.closest("details.nav-group");
        if (group) {
          group.setAttribute("open", "");
          group.classList.add("has-active");
        }
      }
    });

  } catch (err) {
    sidebarContainer.innerHTML = `<p class="error">Error al cargar el menú</p>`;
  }
}

initLayout();
```

---

## 24. Frontend — sidebar.html

```html
<div class="sidebar-header">
  <span class="sidebar-logo">BLIS</span>
  <span class="sidebar-subtitle">Logistics Intelligence</span>
</div>
<nav class="sidebar-nav">
  <a href="/pages/dashboard.html" data-page="dashboard"><i class="ph ph-house-simple"></i>Dashboard</a>
  <a href="/pages/dartis-import.html" data-page="dartis-import"><i class="ph ph-upload-simple"></i>Importar Ventas Dartis</a>
  <a href="/pages/cotizaciones.html" data-page="cotizaciones"><i class="ph ph-file-text"></i>Cotizaciones</a>
  <a href="/pages/ingresos-locales.html" data-page="ingresos-locales"><i class="ph ph-truck"></i>Ingresos Locales</a>

  <details class="nav-group" id="navgroup-config">
    <summary class="nav-group-toggle">
      <span class="nav-group-label"><i class="ph ph-sliders"></i>Configuración</span>
      <i class="ph ph-caret-right nav-group-arrow"></i>
    </summary>
    <div class="nav-group-items">
      <a href="/pages/especies.html" data-page="especies"><i class="ph ph-flower"></i>Especies</a>
      <a href="/pages/variedades.html" data-page="variedades"><i class="ph ph-sparkle"></i>Variedades</a>
      <a href="/pages/grados.html" data-page="grados"><i class="ph ph-arrows-out-line-vertical"></i>Grados</a>
      <a href="/pages/tipos-caja.html" data-page="tipos-caja"><i class="ph ph-package"></i>Tipos de Caja</a>
      <a href="/pages/aeropuertos.html" data-page="aeropuertos"><i class="ph ph-airplane-landing"></i>Aeropuertos</a>
      <a href="/pages/clientes.html" data-page="clientes"><i class="ph ph-users"></i>Clientes</a>
      <a href="/pages/aerolineas.html" data-page="aerolineas"><i class="ph ph-airplane-takeoff"></i>Aerolíneas</a>
      <a href="/pages/cargo-agencies.html" data-page="cargo-agencies"><i class="ph ph-truck"></i>Agencias de Carga</a>
      <a href="/pages/farms.html" data-page="farms"><i class="ph ph-plant"></i>Fincas Exportadoras</a>
      <a href="/pages/tarifas-aerolinea.html" data-page="tarifas-aerolinea"><i class="ph ph-currency-dollar-simple"></i>Tarifas Aerolínea</a>
      <a href="/pages/configuracion.html" data-page="configuracion"><i class="ph ph-shield-check"></i>Permisos</a>
    </div>
  </details>
</nav>
```

---

## 25. Frontend — ingresos-locales.html y .js

### ingresos-locales.html

```html
<!DOCTYPE html>
<html lang="es" data-theme="">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>BLIS · Ingresos Locales</title>
  <link rel="stylesheet" href="/css/styles.css">
  <script src="https://unpkg.com/@phosphor-icons/web@2.1.1/src/index.js" defer></script>
</head>
<body data-page="ingresos-locales">
  <div id="sidebar" class="sidebar"></div>
  <main class="content" id="content"></main>
  <script type="module" src="/js/layout.js"></script>
  <script type="module" src="/pages/ingresos-locales.js?v=4"></script>
</body>
</html>
```

### ingresos-locales.js (completo)

```javascript
let todosLosDatos = [];
let datosFiltrados = [];

async function init() {
  const content = document.getElementById("content");
  content.innerHTML = `
    <div class="dashboard-loading">
      <span></span>
      <p style="font-size:16px;font-weight:600;margin-top:16px">Cargando registros desde Google Sheets…</p>
      <p style="font-size:13px;margin-top:8px;color:#397c55;background:#edf7f0;padding:8px 16px;border-radius:8px;border:1px solid #c3e6cb">
        ⏳ La primera carga del día puede tardar <strong>1–2 minutos</strong> (GAS en espera).<br>
        Por favor aguarda — la tabla aparecerá automáticamente.
      </p>
    </div>`;

  try {
    const resp = await fetch("/api/ingresos-locales/datos");
    if (resp.status === 501) {
      content.innerHTML = `
        <div class="dashboard-error">
          <strong>URL no configurada</strong>
          <p>Agrega <code>INGRESOS_LOCALES_URL=&lt;url-del-gas&gt;</code> en el archivo <code>backend/.env</code> y reinicia el servidor.</p>
        </div>`;
      return;
    }
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    todosLosDatos = (await resp.json()).reverse();
    renderPage();
  } catch (err) {
    content.innerHTML = `
      <div class="dashboard-error">
        <strong>Error al cargar los registros</strong>
        <p>${err.message}</p>
        <button class="btn btn-primary" onclick="location.reload()">Reintentar</button>
      </div>`;
  }
}

function renderPage() {
  const content = document.getElementById("content");
  content.innerHTML = `
    <section class="il-hero">
      <div>
        <h1><i class="ph ph-truck"></i> Ingresos Locales</h1>
        <p>Registros de entregas en finca — datos en tiempo real desde Google Sheets.</p>
      </div>
      <div class="il-hero-time">
        Actualizado: <strong id="il-updated">—</strong>
        <button class="btn btn-sm btn-outline" id="btn-refresh">
          <i class="ph ph-arrows-clockwise"></i> Actualizar
        </button>
      </div>
    </section>
    <div class="il-resumen" id="il-resumen"></div>
    <div class="card il-filtros">
      <div class="il-filtro-campo" style="flex:2; min-width:200px">
        <label>Buscar</label>
        <div class="search-input-wrap">
          <i class="ph ph-magnifying-glass"></i>
          <input type="text" id="il-buscar" placeholder="Guía, finca, cliente, chofer...">
        </div>
      </div>
      <div class="il-filtro-campo">
        <label>Empresa</label>
        <select id="il-filtro-empresa"><option value="">Todas</option></select>
      </div>
      <div class="il-filtro-campo">
        <label>Fecha</label>
        <input type="date" id="il-filtro-fecha">
      </div>
      <button class="btn btn-outline" id="btn-limpiar">
        <i class="ph ph-x"></i> Limpiar
      </button>
    </div>
    <div class="card" style="padding:0; overflow:hidden">
      <div class="il-tabla-header">
        <h2>Registros de entregas</h2>
        <span class="badge badge-gray" id="il-contador">—</span>
      </div>
      <div style="overflow-x:auto">
        <div id="il-tabla-body"></div>
      </div>
    </div>
    <div class="il-overlay" id="il-overlay">
      <div class="il-modal">
        <h3>Compartir entrega</h3>
        <div class="il-modal-guia" id="il-modal-guia">—</div>
        <div class="il-modal-detalle" id="il-modal-detalle"></div>
        <div class="il-link-row">
          <input type="text" id="il-link-input" readonly>
          <button class="btn btn-primary btn-sm" id="btn-copiar">Copiar</button>
        </div>
        <p class="il-copiado" id="il-copiado">✓ Enlace copiado</p>
        <button class="btn btn-outline" style="width:100%" id="btn-cerrar-modal">Cerrar</button>
      </div>
    </div>`;

  document.getElementById("il-updated").textContent =
    new Date().toLocaleTimeString("es-EC", { hour: "2-digit", minute: "2-digit" });

  poblarResumen();
  poblarFiltroEmpresas();
  aplicarFiltros();

  document.getElementById("il-buscar").addEventListener("input", aplicarFiltros);
  document.getElementById("il-filtro-empresa").addEventListener("change", aplicarFiltros);
  document.getElementById("il-filtro-fecha").addEventListener("change", aplicarFiltros);
  document.getElementById("btn-limpiar").addEventListener("click", limpiarFiltros);
  document.getElementById("btn-refresh").addEventListener("click", () => init());
  document.getElementById("btn-copiar").addEventListener("click", copiarLink);
  document.getElementById("btn-cerrar-modal").addEventListener("click", cerrarModal);
  document.getElementById("il-overlay").addEventListener("click", (e) => {
    if (e.target === document.getElementById("il-overlay")) cerrarModal();
  });

  const fila = new URLSearchParams(window.location.search).get("fila");
  if (fila) {
    const reg = todosLosDatos.find(r => String(r._fila) === fila);
    if (reg) abrirModal(reg);
  }
}

function poblarResumen() {
  const hoyStr = new Date().toLocaleDateString("es-EC", {
    day: "2-digit", month: "2-digit", year: "numeric"
  }).replace(/\//g, "/");
  const mesNum = new Date().getMonth();
  const hoy = todosLosDatos.filter(r => String(r["Fecha Documento"]).trim() === hoyStr);
  const mes = todosLosDatos.filter(r => {
    const p = String(r["Fecha Documento"]).split("/");
    return p.length === 3 && parseInt(p[1]) - 1 === mesNum;
  });
  const empresasHoy = [...new Set(hoy.map(r => r["Empresa Logística"]).filter(Boolean))];
  let fullsHoy = 0;
  hoy.forEach(r => {
    const v = String(r["Total Fulls / PCS"] || "").split("/")[0].trim();
    const n = parseFloat(v);
    if (!isNaN(n)) fullsHoy += n;
  });
  document.getElementById("il-resumen").innerHTML = `
    <div class="il-card il-card--accent">
      <div class="il-card-label">Hoy</div>
      <div class="il-card-valor">${hoy.length}</div>
      <div class="il-card-sub">recibos del día</div>
    </div>
    <div class="il-card">
      <div class="il-card-label">Total mes</div>
      <div class="il-card-valor">${mes.length}</div>
      <div class="il-card-sub">recibos</div>
    </div>
    <div class="il-card">
      <div class="il-card-label">Empresas</div>
      <div class="il-card-valor">${empresasHoy.length}</div>
      <div class="il-card-sub">activas hoy</div>
    </div>
    <div class="il-card">
      <div class="il-card-label">Fulls hoy</div>
      <div class="il-card-valor">${fullsHoy.toFixed(2)}</div>
      <div class="il-card-sub">total entregados</div>
    </div>`;
}

function poblarFiltroEmpresas() {
  const empresas = [...new Set(todosLosDatos.map(r => r["Empresa Logística"]).filter(Boolean))].sort();
  const sel = document.getElementById("il-filtro-empresa");
  empresas.forEach(e => {
    const opt = document.createElement("option");
    opt.value = e; opt.textContent = e;
    sel.appendChild(opt);
  });
}

function aplicarFiltros() {
  const texto   = document.getElementById("il-buscar").value.toLowerCase();
  const empresa = document.getElementById("il-filtro-empresa").value;
  const fecha   = document.getElementById("il-filtro-fecha").value;
  datosFiltrados = todosLosDatos.filter(r => {
    const campos = [r["N° Guía / Ingreso"], r["Finca / Exportador"], r["Nombre del Cliente"],
      r["Nombre del Chofer"], r["Placa Vehículo"]].join(" ").toLowerCase();
    return (!texto || campos.includes(texto))
      && (!empresa || r["Empresa Logística"] === empresa)
      && (!fecha || coincideFecha(r["Fecha Documento"], fecha));
  });
  renderTabla();
}

function coincideFecha(fechaReg, fechaInput) {
  if (!fechaReg || !fechaInput) return false;
  const p = String(fechaReg).split("/");
  if (p.length !== 3) return false;
  return `${p[2]}-${p[1].padStart(2,"0")}-${p[0].padStart(2,"0")}` === fechaInput;
}

function limpiarFiltros() {
  document.getElementById("il-buscar").value = "";
  document.getElementById("il-filtro-empresa").value = "";
  document.getElementById("il-filtro-fecha").value = "";
  aplicarFiltros();
}

function renderTabla() {
  const tbody = document.getElementById("il-tabla-body");
  document.getElementById("il-contador").textContent =
    datosFiltrados.length + " registro" + (datosFiltrados.length !== 1 ? "s" : "");
  if (datosFiltrados.length === 0) {
    tbody.innerHTML = `<div class="il-empty"><i class="ph ph-leaf" style="font-size:40px"></i><p>Sin resultados.</p></div>`;
    return;
  }
  let html = `<table class="il-tabla"><thead><tr>
    <th>Fecha</th><th>Empresa</th><th>Guía / Ingreso</th>
    <th>Finca</th><th>Cliente</th><th>Fulls</th><th>Temp.</th><th></th>
  </tr></thead><tbody>`;
  datosFiltrados.forEach((r, i) => {
    const empresa = r["Empresa Logística"] || "—";
    const tempNum = parseFloat(String(r["Temperatura (°C)"] || "").replace(/[^0-9.\-]/g, ""));
    const tempCls = isNaN(tempNum) ? "" : tempNum > 5 ? "il-temp-alt" : "il-temp-ok";
    const finca   = (r["Finca / Exportador"] || "—");
    const cliente = (r["Nombre del Cliente"] || "—");
    html += `<tr class="il-row" data-idx="${i}">
      <td>${r["Fecha Documento"] || "—"}</td>
      <td><span class="il-badge ${badgeEmpresa(empresa)}">${empresa}</span></td>
      <td><strong>${r["N° Guía / Ingreso"] || "—"}</strong></td>
      <td title="${finca}">${finca.length > 22 ? finca.slice(0,22)+"…" : finca}</td>
      <td title="${cliente}">${cliente.length > 20 ? cliente.slice(0,20)+"…" : cliente}</td>
      <td>${r["Total Fulls / PCS"] || "—"}</td>
      <td class="${tempCls}">${r["Temperatura (°C)"] || "—"}</td>
      <td><button class="btn btn-sm btn-outline il-btn-compartir" data-idx="${i}">
        <i class="ph ph-share-network"></i>
      </button></td>
    </tr>`;
  });
  html += "</tbody></table>";
  tbody.innerHTML = html;
  tbody.querySelectorAll(".il-row").forEach(row => {
    row.addEventListener("click", (e) => {
      if (!e.target.closest("button")) abrirModal(datosFiltrados[row.dataset.idx]);
    });
  });
  tbody.querySelectorAll(".il-btn-compartir").forEach(btn => {
    btn.addEventListener("click", (e) => { e.stopPropagation(); abrirModal(datosFiltrados[btn.dataset.idx]); });
  });
}

function badgeEmpresa(empresa) {
  const e = (empresa || "").toLowerCase();
  if (e.includes("one") || e.includes("teamcargo"))    return "il-badge-one";
  if (e.includes("pacific"))                            return "il-badge-pac";
  if (e.includes("value"))                              return "il-badge-val";
  if (e.includes("logiztik") || e.includes("alliance")) return "il-badge-log";
  if (e.includes("ldsexport") || e.includes("lds"))     return "il-badge-lds";
  if (e.includes("fresh"))                              return "il-badge-fresh";
  return "il-badge-otra";
}

function abrirModal(reg) {
  if (!reg) return;
  document.getElementById("il-modal-guia").textContent = "Guía / Ingreso: " + (reg["N° Guía / Ingreso"] || "—");
  document.getElementById("il-modal-detalle").innerHTML = `
    <strong>Empresa:</strong> ${reg["Empresa Logística"] || "—"}<br>
    <strong>Fecha:</strong> ${reg["Fecha Documento"] || "—"} ${reg["Hora Registro"] || ""}<br>
    <strong>Chofer:</strong> ${reg["Nombre del Chofer"] || "—"} · ${reg["Placa Vehículo"] || "—"}<br>
    <strong>Finca:</strong> ${reg["Finca / Exportador"] || "—"}<br>
    <strong>Cliente:</strong> ${reg["Nombre del Cliente"] || "—"}<br>
    <strong>Cajas:</strong> ${reg["Detalle Cajas"] || "—"}<br>
    <strong>Fulls:</strong> ${reg["Total Fulls / PCS"] || "—"}<br>
    <strong>Temperatura:</strong> ${reg["Temperatura (°C)"] || "—"}`;
  const url = window.location.href.split("?")[0] + "?fila=" + reg["_fila"];
  document.getElementById("il-link-input").value = url;
  document.getElementById("il-copiado").style.display = "none";
  document.getElementById("il-overlay").classList.add("il-overlay--open");
}

function cerrarModal() {
  document.getElementById("il-overlay").classList.remove("il-overlay--open");
}

function copiarLink() {
  const input = document.getElementById("il-link-input");
  navigator.clipboard.writeText(input.value).then(() => {
    document.getElementById("il-copiado").style.display = "block";
  }).catch(() => {
    input.select();
    document.execCommand("copy");
    document.getElementById("il-copiado").style.display = "block";
  });
}

init();
setInterval(init, 180000); // refresca cada 3 minutos
```

---

## 26. Frontend — dartis-import.html y .js

### dartis-import.html

```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>BLIS · Importar Ventas Dartis</title>
  <link rel="stylesheet" href="/css/styles.css" />
</head>
<body data-page="dartis-import">
  <div id="sidebar" class="sidebar"></div>
  <main class="content" id="content">
    <div class="page-header">
      <h1><i class="ph ph-upload-simple"></i> Importar Ventas Dartis</h1>
      <p class="page-subtitle">Sube los dos archivos Excel de Dartis para registrar las ventas del período.</p>
    </div>
    <div class="import-card">
      <div class="import-rule">
        <i class="ph ph-info"></i>
        <span>Se deben subir <strong>ambos archivos</strong> al mismo tiempo: Ventas Recetas y Ventas clásico.</span>
      </div>
      <form id="importForm">
        <div class="file-fields">
          <div class="file-field">
            <label for="file_recetas">
              <i class="ph ph-file-xls"></i> Ventas Recetas
              <span class="file-hint">Archivo con detalle por especie, guía y tipo de caja</span>
            </label>
            <div class="file-drop" id="drop_recetas" data-target="file_recetas">
              <i class="ph ph-upload-simple"></i>
              <span id="label_recetas">Arrastra el archivo o haz clic para seleccionar</span>
              <input type="file" id="file_recetas" name="file_recetas" accept=".xlsx,.xls" required />
            </div>
          </div>
          <div class="file-field">
            <label for="file_ventas">
              <i class="ph ph-file-xls"></i> Ventas
              <span class="file-hint">Archivo con agencia de carga y vendedor por pedido</span>
            </label>
            <div class="file-drop" id="drop_ventas" data-target="file_ventas">
              <i class="ph ph-upload-simple"></i>
              <span id="label_ventas">Arrastra el archivo o haz clic para seleccionar</span>
              <input type="file" id="file_ventas" name="file_ventas" accept=".xlsx,.xls" required />
            </div>
          </div>
        </div>
        <div class="import-actions">
          <button type="submit" id="btnUpload" class="btn btn-primary" disabled>
            <i class="ph ph-upload-simple"></i> Importar
          </button>
        </div>
      </form>
      <div id="progressSection" class="hidden">
        <div class="progress-bar"><div id="progressFill" class="progress-fill"></div></div>
        <p id="progressMsg" class="progress-msg">Procesando archivos...</p>
      </div>
      <div id="resultSection" class="hidden"></div>
    </div>
  </main>
  <script type="module" src="/js/layout.js"></script>
  <script type="module" src="/pages/dartis-import.js"></script>
</body>
</html>
```

### dartis-import.js

```javascript
const API = "/api/dartis/upload";

document.querySelectorAll(".file-drop").forEach(zone => {
  const inputId = zone.dataset.target;
  const input   = document.getElementById(inputId);
  const label   = document.getElementById("label_" + inputId.replace("file_", ""));

  zone.addEventListener("click", () => input.click());
  zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("drag-over"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
  zone.addEventListener("drop", e => {
    e.preventDefault();
    zone.classList.remove("drag-over");
    if (e.dataTransfer.files[0]) {
      input.files = e.dataTransfer.files;
      updateLabel(label, zone, e.dataTransfer.files[0].name);
      checkReady();
    }
  });
  input.addEventListener("change", () => {
    if (input.files[0]) { updateLabel(label, zone, input.files[0].name); checkReady(); }
  });
});

function updateLabel(label, zone, name) {
  label.textContent = name;
  zone.classList.add("file-selected");
}

function checkReady() {
  const r = document.getElementById("file_recetas").files[0];
  const v = document.getElementById("file_ventas").files[0];
  document.getElementById("btnUpload").disabled = !(r && v);
}

document.getElementById("importForm").addEventListener("submit", async e => {
  e.preventDefault();
  const btn = document.getElementById("btnUpload");
  btn.disabled = true;
  showProgress("Enviando archivos...");

  const form = new FormData();
  form.append("file_recetas", document.getElementById("file_recetas").files[0]);
  form.append("file_ventas",  document.getElementById("file_ventas").files[0]);

  try {
    const res = await fetch(API, { method: "POST", body: form });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Error en el servidor");
    }
    const data = await res.json();
    hideProgress();
    showResult(data);
  } catch (err) {
    hideProgress();
    showError(err.message);
  } finally {
    btn.disabled = false;
  }
});

function showProgress(msg) {
  document.getElementById("progressSection").classList.remove("hidden");
  document.getElementById("resultSection").classList.add("hidden");
  document.getElementById("progressMsg").textContent = msg;
  let w = 0;
  window._prog = setInterval(() => {
    w = Math.min(w + 3, 90);
    document.getElementById("progressFill").style.width = w + "%";
  }, 200);
}

function hideProgress() {
  clearInterval(window._prog);
  document.getElementById("progressFill").style.width = "100%";
  setTimeout(() => document.getElementById("progressSection").classList.add("hidden"), 400);
}

function showResult(data) {
  const r = data.recetas;
  const v = data.ventas;
  const agNuevas = [...(r.agencias_nuevas || []), ...(v.agencias_nuevas || [])];
  const sinFinca = r.postcosechas_sin_finca || [];

  let html = `
    <div class="result-box success">
      <h3><i class="ph ph-check-circle"></i> Importación completada</h3>
      <div class="result-cols">
        <div class="result-col">
          <h4><i class="ph ph-file-xls"></i> Ventas Recetas</h4>
          <p><span class="badge badge-green">${r.insertados_o_actualizados}</span> registros importados</p>
          <p><span class="badge badge-blue">${r.clientes_vinculados}</span> clientes vinculados</p>
          ${r.clientes_nuevos ? `<p><span class="badge badge-orange">${r.clientes_nuevos}</span> clientes nuevos creados</p>` : ""}
          ${r.errores ? `<p><span class="badge badge-red">${r.errores}</span> errores</p>` : ""}
        </div>
        <div class="result-col">
          <h4><i class="ph ph-file-xls"></i> Ventas</h4>
          <p><span class="badge badge-blue">${v.actualizadas}</span> registros enriquecidos</p>
          ${v.errores ? `<p><span class="badge badge-red">${v.errores}</span> errores</p>` : ""}
        </div>
      </div>`;

  if (agNuevas.length) {
    html += `<div class="result-alert alert-info">
      <i class="ph ph-truck"></i> <strong>${agNuevas.length} agencia(s) nueva(s) agregada(s):</strong>
      <ul>${agNuevas.map(a => `<li>${a}</li>`).join("")}</ul>
    </div>`;
  }
  if (sinFinca.length) {
    html += `<div class="result-alert alert-warn">
      <i class="ph ph-warning"></i> <strong>Postcosechas sin finca asignada:</strong>
      <ul>${sinFinca.map(p => `<li>${p}</li>`).join("")}</ul>
    </div>`;
  }
  html += `</div>`;

  const section = document.getElementById("resultSection");
  section.innerHTML = html;
  section.classList.remove("hidden");
}

function showError(msg) {
  const section = document.getElementById("resultSection");
  section.innerHTML = `
    <div class="result-box error">
      <h3><i class="ph ph-x-circle"></i> Error al importar</h3>
      <p>${msg}</p>
    </div>`;
  section.classList.remove("hidden");
}
```

---

## 27. Frontend — dashboard.html

```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>BLIS · Dashboard</title>
  <link rel="stylesheet" href="/css/styles.css" />
</head>
<body data-page="dashboard">
  <div id="sidebar" class="sidebar"></div>
  <main class="content" id="content"></main>
  <script type="module" src="/js/layout.js"></script>
  <script type="module" src="/pages/dashboard.js"></script>
</body>
</html>
```

---

## 28. Base de datos — tablas y relaciones

| Tabla | Campos principales |
|---|---|
| `species` | id (UUID), code, name, active, created_at, updated_at, inactive_date |
| `varieties` | id, species_id (FK), code, name, active |
| `product_sizes` | id, species_id (FK), size_code, description, active |
| `box_types` | id, box_code, box_name, length_cm, width_cm, height_cm, reference_weight_kg, active |
| `airports` | id, iata_code, airport_name, city, country_id (FK), active |
| `countries` | id, code, name, active |
| `airlines` | id, airline_code, airline_name, active |
| `airline_tariffs` | id, airline_id (FK), origin_airport_id (FK), destination_airport_id (FK), cost_per_kg, minimum_charge, currency_code, valid_from, valid_to, active |
| `cargo_agencies` | id, code, name, dartis_name, ocr_variants (TEXT[]), type, country, active |
| `customers` | id, customer_code, customer_name, dartis_name, contact_name, email, phone, active |
| `farms` | id, code, name, ocr_variants (TEXT[]), dartis_postcosecha, active |
| `farm_postcosecha` | id, farm_id (FK), postcosecha |
| `dartis_ventas` | id, fecha, dae, id_comercializadora, id_pedido (UNIQUE con guias), empresa, cliente, **customer_id** (FK), destinatario, postcosecha, especie, guia_madre, guia_hija, tipo_caja, total_piezas, total_tallos, total_dolares, vendedor, agencia_carga, importado_at |
| `roles` | id, name |
| `profiles` | id, user_id, role_id (FK), full_name |
| `markets` | id, code, name |
| `providers` | id, name, active |
| `incoterms` | id, code, name |
| `cost_components` | id, component_name, category |
| `scenario_headers` | id, scenario_code, scenario_name, created_at |
| `scenario_details` | id, scenario_id (FK), boxes, chargeable_weight_kg |
| `scenario_cost_results` | id, scenario_id (FK), cost_component_id (FK), amount, currency_code |
| `exchange_rates` | id, currency_code, rate, rate_date |

**Clave única en dartis_ventas:**
```sql
UNIQUE (id_pedido, guia_madre, guia_hija, tipo_caja)
```

---

## 29. Migración aplicada

Ejecutada directamente en Supabase SQL Editor:

```sql
-- Agrega la columna customer_id a dartis_ventas para vincular con clientes
ALTER TABLE dartis_ventas
  ADD COLUMN IF NOT EXISTS customer_id UUID REFERENCES customers(id);
```

---

## 30. Despliegue en Render.com

### Datos del servicio

| Campo | Valor |
|---|---|
| Service ID | `srv-da39og5g1s2s73d4jmlg` |
| URL | `https://blis-hxu1.onrender.com` |
| Plan | Free (spin-down 15 min) → Starter $7/mes para siempre activo |
| Runtime | Python 3 |
| Build command | `pip install -r backend/requirements.txt` |
| Start command | `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Branch | `main` |
| Auto-deploy | Sí — cada `git push` a main dispara un redeploy |

### Variables de entorno en Render

Render → BLIS → **Environment** → Add Environment Variable:

| Key | Value |
|---|---|
| `DATABASE_URL` | `postgresql://...` (de Supabase) |
| `INGRESOS_LOCALES_URL` | `https://script.google.com/macros/s/.../exec` |

### Errores resueltos durante el deploy

| Error | Causa | Solución aplicada |
|---|---|---|
| `ModuleNotFoundError: No module named 'app'` | uvicorn corría desde raíz del repo | Start command: `cd backend && uvicorn ...` |
| `Could not parse SQLAlchemy URL` | `DATABASE_URL` no configurada en Render | Agregar variable en Environment |
| `Form data requires python-multipart` | Paquete faltante en requirements | Agregar `python-multipart` al `backend/requirements.txt` + Clear cache & deploy |
| Deploy usaba cache viejo | Render cachea paquetes pip | Manual Deploy → ▼ → **Clear build cache & deploy** |
| `We are unable to access your GitHub repository` | Repo privado | Cambiar a público temporalmente → conectar → volver a privado |

---

## 31. Desarrollo local — paso a paso

### Paso 1: Clonar el repositorio

```bash
git clone https://github.com/freddyerazo/BellaflorLogis.git
cd BellaflorLogis
```

### Paso 2: Crear entorno virtual

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# o en Linux/Mac:
source .venv/bin/activate
```

### Paso 3: Instalar dependencias

```bash
pip install -r backend/requirements.txt
```

### Paso 4: Configurar variables de entorno

```bash
# Crear archivo backend/.env con:
DATABASE_URL=postgresql://postgres.xxxx:password@aws-0-us-east-1.pooler.supabase.com:5432/postgres
INGRESOS_LOCALES_URL=https://script.google.com/macros/s/.../exec
```

### Paso 5: Iniciar el servidor

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

La aplicación estará disponible en `http://localhost:8000`.

El frontend se sirve como archivos estáticos desde `../frontend/` gracias a:
```python
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
```

### Paso 6: Verificar conexión

```
GET http://localhost:8000/health        → {"status":"ok","system":"BLIS"}
GET http://localhost:8000/db-test       → {"status":"connected","database_time":"..."}
```

---

## 32. GitHub

| Campo | Valor |
|---|---|
| Repositorio | `https://github.com/freddyerazo/BellaflorLogis` |
| Branch principal | `main` |
| Visibilidad | Privado |
| Auto-deploy | Push a `main` → Render redeploya automáticamente |

### .gitignore

```
backend/.env
.venv/
.venv-1/
__pycache__/
*.pyc
backups/
docs/*.docx
```

### Flujo de trabajo git

```bash
# Ver estado
git status

# Agregar cambios
git add <archivo>

# Commit
git commit -m "descripcion del cambio"

# Push → dispara autodeploy en Render
git push origin main
```

---

## 33. Troubleshooting

### Backend

| Problema | Causa probable | Solución |
|---|---|---|
| `ModuleNotFoundError: No module named 'app'` | uvicorn no está en `backend/` | `cd backend` antes de uvicorn |
| `Could not parse SQLAlchemy URL` | `DATABASE_URL` vacía | Verificar `.env` o variable en Render |
| `Form data requires python-multipart` | Paquete no instalado | `pip install python-multipart` |
| Import Dartis cuelga | Código síncrono en endpoint async | Usar `run_in_executor` (ya implementado) |
| `ON CONFLICT command cannot affect row a second time` | Duplicados en el Excel con misma clave | Deduplicar con dict Python antes del bulk insert (ya implementado) |
| GAS no responde en 120s | Cold start de GAS | Normal en primera carga del día — reintentar |

### Frontend

| Problema | Causa probable | Solución |
|---|---|---|
| Página en blanco / scroll necesario | HTML structure incorrecta | Body debe tener `display:flex` con sidebar + main como hijos directos |
| "URL no configurada" en Ingresos Locales | `INGRESOS_LOCALES_URL` no configurada | Agregar variable en Render → Environment |
| Contadores "undefined" en resultado de import | Nombre de key incorrecto en JS | Verificar que el JS use `insertados_o_actualizados` y `actualizadas` |

### Render

| Problema | Solución |
|---|---|
| Deploy falla con cache viejo | Manual Deploy → ▼ → Clear build cache & deploy |
| No puede acceder al repo | Repo debe estar público O conectado via GitHub App en Render Settings |
| Spin-down en free tier | Actualizar a Starter ($7/mes) o aceptar 50s de cold start |

---

*Documentación generada: Agosto 2026 · Bellaflor Group · freddyerazo@unach.edu.ec*
