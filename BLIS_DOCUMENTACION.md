# BLIS — Bellaflor Logistics Intelligence System
## Documentación Técnica Completa con Código · v2.1 · Agosto 2026

---

## Índice

1. [Descripción del proyecto](#1-descripción-del-proyecto)
2. [Stack tecnológico](#2-stack-tecnológico)
3. [Estructura del proyecto](#3-estructura-del-proyecto)
4. [Variables de entorno](#4-variables-de-entorno)
5. [Configuración de deploy — render.yaml](#5-configuración-de-deploy--renderyaml)
6. [requirements.txt](#6-requirementstxt)
7. [Backend — núcleo](#7-backend--núcleo)
8. [Backend — módulos de catálogo y operación](#8-backend--módulos-de-catálogo-y-operación)
9. [Backend — módulo Agrocalidad](#9-backend--módulo-agrocalidad)
10. [Backend — módulo Inventario LAG](#10-backend--módulo-inventario-lag)
11. [Backend — módulo Torre de Control](#11-backend--módulo-torre-de-control)
12. [Backend — módulo Auditoría de Etiquetas](#12-backend--módulo-auditoría-de-etiquetas)
13. [Schemas Pydantic](#13-schemas-pydantic)
14. [Frontend — núcleo](#14-frontend--núcleo)
15. [Frontend — páginas de catálogo y operación](#15-frontend--páginas-de-catálogo-y-operación)
16. [Frontend — páginas de los módulos clonados](#16-frontend--páginas-de-los-módulos-clonados)
17. [Base de datos — tablas y relaciones](#17-base-de-datos--tablas-y-relaciones)
18. [Migraciones aplicadas](#18-migraciones-aplicadas)
19. [Despliegue en Render.com](#19-despliegue-en-rendercom)
20. [Desarrollo local — paso a paso](#20-desarrollo-local--paso-a-paso)
21. [GitHub](#21-github)
22. [Troubleshooting](#22-troubleshooting)
23. [Módulo Proveedores (catálogo de exportadores Logiztik)](#23-módulo-proveedores-catálogo-de-exportadores-logiztik)

---

## 1. Descripción del proyecto

BLIS es la plataforma web interna de Bellaflor Group para análisis, simulación y gestión logística de exportación de flores. Centraliza datos de múltiples fuentes — Dartis (sistema de ventas/ERP de exportación), Google Apps Script (ingresos locales), y una base de datos propia en Supabase — en una interfaz de administración unificada.

Desde agosto de 2026, BLIS además **absorbe 4 herramientas que antes vivían como proyectos externos independientes** (cada una con su propio repo, deploy y a veces su propia base de datos), clonadas dentro de BLIS como módulos nuevos:

- **Agrocalidad** — consulta de requisitos fitosanitarios de exportación (clon de "Agrocalidad Consulta"). El scraping real (evade el anti-bot del sitio de Agrocalidad) sigue en GitHub Actions del repo `freddyerazo/AgrocalidadDartis`; BLIS orquesta y muestra el resultado.
- **Inventario LAG** — proxy en vivo sobre el WMS de Logiztik Alliance Group, bodega de Miami (clon de "InventarioApiLag"). Sin base de datos propia, todo se consulta en tiempo real.
- **Torre de Control** — conciliación de cajas Dartis vs manifiestos UPS/FedEx/agencias locales, con scheduler propio y sync a Duoplane (clon de "REPORTEUPSFEDEX").
- **Auditoría de Etiquetas** — auditoría física de despachos de clientes especiales vía el mismo bot de Telegram del proyecto original, ahora con backend en BLIS (clon de "Auditoria_LEsp").

El principio de diseño de estos 4 módulos: **`dartis_ventas` es la tabla base**. En vez de que cada módulo pida su propio archivo/Excel de ventas por separado, todos leen directo de `dartis_ventas` (ya normalizada y deduplicada correctamente, incluyendo `especie` en su clave única — ver el Troubleshooting §22 sobre el bug de pérdida de datos silenciosa que esto corrigió, encontrado y arreglado antes de empezar a clonar los módulos).

**URL de producción:** `https://blis-hxu1.onrender.com`
**Repositorio:** `https://github.com/freddyerazo/BellaflorLogis`
**Plan actual:** Free (spin-down tras 15 min) → Starter $7/mes para siempre activo

---

## 2. Stack tecnológico

| Capa | Tecnología | Notas |
|---|---|---|
| Backend | FastAPI | Un router por módulo, montado con prefix `/api` |
| Servidor ASGI | Uvicorn | `uvicorn[standard]` (uvloop + httptools) |
| ORM | SQLAlchemy Core | SQL crudo vía `text()`, sin capa de modelos ORM |
| Driver PostgreSQL | psycopg2-binary | + `execute_values` para bulk insert (ver §22) |
| Base de datos | PostgreSQL (Supabase) | Proyecto `kgpzhwocygonppblgmpm`, 51 tablas |
| Scheduler | APScheduler (`AsyncIOScheduler`) | Refresco periódico de Torre de Control |
| Excel parsing | openpyxl | Importación Dartis |
| PDF parsing | pdfplumber | Manifiestos FedEx (Torre de Control) |
| HTTP cliente async | httpx | Agrocalidad, Inventario LAG, Torre de Control, Telegram |
| HTTP cliente sync | requests | Google Drive API (junto con `google-auth`) |
| Auth Google | google-auth | JWT de cuenta de servicio para Drive API v3 |
| Multipart | python-multipart | Subida de archivos (Dartis, UPS, FedEx) |
| Frontend | HTML + JS vanilla | ES2022, sin build step, módulos ES6 |
| Iconos | Phosphor Icons | 2.1.1 |
| Deploy | Render.com | Web service, autodeploy en push a `main` |
| Versiones | GitHub | `freddyerazo/BellaflorLogis` |

---

## 3. Estructura del proyecto

```
BLIS/
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── main.py                    # FastAPI app + CORS + scheduler + monta frontend
│       ├── api/                       # un router por modulo
│       │   ├── health.py, db_test.py
│       │   ├── dashboard.py, cotizacion.py, dartis_import.py, ingresos_locales.py
│       │   ├── species.py, varieties.py, product_sizes.py, box_types.py
│       │   ├── airports.py, countries.py, customers.py, airlines.py, airline_tariffs.py
│       │   ├── cargo_agencies.py, farms.py, roles.py, profiles.py
│       │   ├── agrocalidad.py             # Fase 1
│       │   ├── inventario_lag.py          # Fase 2
│       │   ├── torre_control.py           # Fase 3
│       │   └── auditoria_etiquetas.py     # Fase 4
│       ├── services/                  # logica de negocio reutilizable (antes vacia)
│       │   ├── lag_client.py, lag_xml_utils.py, lag_inventario_completo.py
│       │   ├── courier_ups_client.py, courier_fedex_client.py, courier_parsers.py
│       │   ├── courier_entregas_locales.py, courier_duoplane.py, courier_reconciliation.py
│       │   ├── special_dispatches.py, google_drive.py, telegram_bot.py
│       ├── schemas/                   # Pydantic, un archivo por modulo
│       └── database/
│           ├── connection.py
│           └── helpers.py
├── frontend/
│   ├── index.html
│   ├── css/styles.css
│   ├── js/ (layout.js, api.js, crud-page.js)
│   ├── components/sidebar.html
│   └── pages/                         # un .html + un .js por modulo
│       ├── dashboard, ingresos-locales, dartis-import, cotizaciones, clientes,
│       │   especies, variedades, grados, tipos-caja, aeropuertos, aerolineas,
│       │   tarifas-aerolinea, cargo-agencies, farms, configuracion
│       ├── agrocalidad.html / .js             # Fase 1
│       ├── inventario-lag.html / .js          # Fase 2
│       ├── torre-control.html / .js           # Fase 3
│       └── auditoria-etiquetas.html / .js     # Fase 4
├── database/
│   ├── schema/schema_v1.sql
│   ├── views/views_v1.sql
│   ├── seeds/seeds_v1.sql
│   └── migrations/                    # 002 a 019 (ver §18)
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

# Agrocalidad (Fase 1) — dispara el workflow de GitHub Actions del repo original
GITHUB_TOKEN=
GITHUB_REPO=freddyerazo/AgrocalidadDartis

# Inventario LAG (Fase 2) — credenciales de Logiztik Alliance Group
LAG_ENV=test
LAG_CUSTOMER_CODE=
LAG_TOKEN=
LAG_SALES_API_KEY=
LAG_TIMEOUT=30

# Posteo de Inventario (dentro de Inventario LAG) — endpoint legacy PlaceOrder,
# host y token distintos al resto de LAG, SIN ambiente de pruebas (solo produccion)
LAG_PLACE_ORDER_BASE_URL=https://cloudus.logiztikalliance.com:5005/external/api
LAG_PLACE_ORDER_TOKEN=

# Torre de Control (Fase 3)
DEMO_MODE=true
REFRESH_SECONDS=300
UPS_CLIENT_ID=
UPS_CLIENT_SECRET=
UPS_BASE_URL=https://onlinetools.ups.com
FEDEX_CLIENT_ID=
FEDEX_CLIENT_SECRET=
FEDEX_BASE_URL=https://apis.fedex.com
DUOPLANE_API_KEY=
DUOPLANE_API_PASSWORD=
DUOPLANE_BASE_URL=https://app.duoplane.com
ENTREGAS_SHEET_URL=https://docs.google.com/spreadsheets/d/1QmMrXu_LVAIQBFmyl7MyvteaEMKoteNJjBfpWnlAjDM/export?format=csv
GOOGLE_SHEETS_API_KEY=

# Auditoria de Etiquetas (Fase 4)
TELEGRAM_BOT_TOKEN=
TELEGRAM_WEBHOOK_SECRET=
GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON=
GOOGLE_DRIVE_FOLDER_ID=

# Proveedores — gateway movil de Logiztik Alliance (app AllianceApp)
LOGIZTIK_MOBILE_BASE_URL=https://apigwtmb.logiztikalliance.com
LOGIZTIK_USER=
LOGIZTIK_PASS=
LOGIZTIK_ENTITY_ID=

```

| Variable | Módulo | Descripción |
|---|---|---|
| `DATABASE_URL` | núcleo | Cadena de conexión PostgreSQL de Supabase |
| `INGRESOS_LOCALES_URL` | Ingresos Locales | URL pública del Web App de Google Apps Script |
| `GITHUB_TOKEN` | Agrocalidad | PAT fine-grained, permiso `actions:write` sobre `AgrocalidadDartis` |
| `GITHUB_REPO` | Agrocalidad | `owner/repo` del proyecto original (default `freddyerazo/AgrocalidadDartis`) |
| `LAG_ENV`, `LAG_CUSTOMER_CODE`, `LAG_TOKEN`, `LAG_SALES_API_KEY` | Inventario LAG | Credenciales de Logiztik Alliance Group |
| `LAG_PLACE_ORDER_BASE_URL`, `LAG_PLACE_ORDER_TOKEN` | Posteo de Inventario | Endpoint legacy `PlaceOrder/ordernew`, host y token propios, **sin ambiente de pruebas** — cualquier posteo va directo a producción de LAG |
| `DEMO_MODE` | Torre de Control | `true` = tracking simulado, sin credenciales de courier |
| `REFRESH_SECONDS` | Torre de Control | Intervalo del scheduler (default 300s) |
| `UPS_CLIENT_ID/SECRET`, `FEDEX_CLIENT_ID/SECRET` | Torre de Control | OAuth2 client-credentials de cada courier |
| `DUOPLANE_API_KEY/PASSWORD` | Torre de Control | Basic Auth de la API de Duoplane |
| `ENTREGAS_SHEET_URL`, `GOOGLE_SHEETS_API_KEY` | Torre de Control | Google Sheet público de entregas de agencias locales |
| `TELEGRAM_BOT_TOKEN` | Auditoría de Etiquetas | Token del bot (se reutiliza el del proyecto original) |
| `TELEGRAM_WEBHOOK_SECRET` | Auditoría de Etiquetas | Valida `X-Telegram-Bot-Api-Secret-Token` en el webhook |
| `GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON`, `GOOGLE_DRIVE_FOLDER_ID` | Auditoría de Etiquetas | Cuenta de servicio con acceso de escritura a la carpeta de fotos |
| `LOGIZTIK_MOBILE_BASE_URL` | Proveedores | Base del gateway móvil de Logiztik (default `https://apigwtmb.logiztikalliance.com`) |
| `LOGIZTIK_USER`, `LOGIZTIK_PASS` | Proveedores | Credenciales SSO de Bellaflor para `POST /apisso/Account/Login` |
| `LOGIZTIK_ENTITY_ID` | Proveedores | Id de entidad/cliente (`idEntidad`, p.ej. `CLI013575`); si el login devuelve `entityId` se usa ese |

> ⚠️ Nunca compartir el valor de estas variables en el chat ni en el código. Las 4 fases nuevas quedaron implementadas y probadas en `DEMO_MODE`/sin credenciales reales — activar cada integración real es un paso de configuración pendiente, no de código.

---

## 5. Configuración de deploy — render.yaml

`render.yaml`
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
      - key: PYTHON_VERSION
        value: 3.11.0
```

**Notas importantes:**
- `buildCommand` usa `backend/requirements.txt` (ruta desde la raíz del repo)
- `startCommand` hace `cd backend` antes de lanzar uvicorn para que Python encuentre el módulo `app`
- Las variables con `sync: false` se ingresan manualmente en Render → Environment — **todas las variables nuevas de la sección 4 deben agregarse ahí manualmente**, `render.yaml` solo declara `DATABASE_URL`/`INGRESOS_LOCALES_URL`/`PYTHON_VERSION` explícitamente

---

## 6. requirements.txt

### `backend/requirements.txt` (usado por Render)

`backend/requirements.txt`
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
httpx
pdfplumber
apscheduler
google-auth
requests
```

### `requirements.txt` (raíz, usado localmente)

`requirements.txt`
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
httpx
pdfplumber
apscheduler
google-auth
requests
```

---

## 7. Backend — núcleo

### main.py

Registra los 24 routers y arranca el scheduler de Torre de Control en el evento `startup`.

`backend/app/main.py`
```python
import os
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
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
from app.api.agrocalidad import router as agrocalidad_router
from app.api.inventario_lag import router as inventario_lag_router
from app.api.torre_control import router as torre_control_router
from app.api.auditoria_etiquetas import router as auditoria_etiquetas_router
from app.api.truck_company import router as truck_company_router
from app.services import courier_reconciliation

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
app.include_router(agrocalidad_router, prefix="/api")
app.include_router(inventario_lag_router, prefix="/api")
app.include_router(torre_control_router, prefix="/api")
app.include_router(auditoria_etiquetas_router, prefix="/api")
app.include_router(truck_company_router, prefix="/api")

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

scheduler = AsyncIOScheduler()


@app.on_event("startup")
async def iniciar_torre_control():
    """Igual patron que el proyecto original: un refresco inicial y luego
    uno periodico cada REFRESH_SECONDS, protegidos por el mismo lock que
    usa el boton 'Actualizar ahora' (app/services/courier_reconciliation)."""
    await courier_reconciliation.refrescar()
    scheduler.add_job(
        courier_reconciliation.refrescar, "interval",
        seconds=int(os.getenv("REFRESH_SECONDS", "300")),
    )
    scheduler.start()
```

### database/connection.py

`backend/app/database/connection.py`
```python
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
```

### database/helpers.py

`backend/app/database/helpers.py`
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

### api/health.py

`backend/app/api/health.py`
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

### api/db_test.py

`backend/app/api/db_test.py`
```python
from fastapi import APIRouter
from sqlalchemy import text

from app.database.connection import engine

router = APIRouter()

@router.get("/db-test")
def db_test():

    try:

        with engine.connect() as conn:

            result = conn.execute(
                text("SELECT NOW()")
            )

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

## 8. Backend — módulos de catálogo y operación

Módulos ya existentes antes de las Fases 1-4 (sin cambios en esta ronda, incluidos aquí para referencia completa).

### api/dashboard.py

`backend/app/api/dashboard.py`
```python
from fastapi import APIRouter
from sqlalchemy import text

from app.database.connection import engine

router = APIRouter()


@router.get("/dashboard/summary")
def dashboard_summary():
    with engine.connect() as conn:
        summary = conn.execute(
            text(
                """
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
                """
            )
        ).mappings().first()

        # Top 5 especies por número de variedades
        top_species = conn.execute(
            text(
                """
                SELECT s.name AS species_name, COUNT(v.id) AS variety_count
                FROM species s
                LEFT JOIN varieties v ON v.species_id = s.id AND v.active = true
                WHERE s.active = true
                GROUP BY s.id, s.name
                ORDER BY variety_count DESC
                LIMIT 5
                """
            )
        ).mappings().all()

        # Distribución de tipos de caja (con dimensiones)
        box_distribution = conn.execute(
            text(
                """
                SELECT box_code, box_name, length_cm, width_cm, height_cm
                FROM box_types
                WHERE active = true
                ORDER BY length_cm DESC
                LIMIT 8
                """
            )
        ).mappings().all()

        # Último escenario calculado
        last_scenario = conn.execute(
            text(
                """
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
                """
            )
        ).mappings().first()

        # Componentes de costo del último escenario
        cost_breakdown = []
        if last_scenario:
            cost_breakdown = conn.execute(
                text(
                    """
                    SELECT cc.component_name, scr.amount, scr.currency_code
                    FROM scenario_cost_results scr
                    JOIN cost_components cc ON cc.id = scr.cost_component_id
                    JOIN scenario_headers sh ON sh.id = scr.scenario_id
                    ORDER BY sh.created_at DESC, scr.amount DESC
                    LIMIT 10
                    """
                )
            ).mappings().all()

        return {
            "summary": dict(summary),
            "top_species": [dict(r) for r in top_species],
            "box_distribution": [dict(r) for r in box_distribution],
            "last_scenario": dict(last_scenario) if last_scenario else None,
            "cost_breakdown": [dict(r) for r in cost_breakdown],
        }
```

### api/ingresos_locales.py

`backend/app/api/ingresos_locales.py`
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

### api/dartis_import.py

Corregido en esta sesión — ver Troubleshooting §22 (`especie` agregada a la clave única, bulk insert con `execute_values`).

`backend/app/api/dartis_import.py`
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
```

### api/cotizacion.py

`backend/app/api/cotizacion.py`
```python
from fastapi import APIRouter
from sqlalchemy import text

from app.database.connection import engine

router = APIRouter()


@router.get("/cotizacion/catalogo")
def get_catalogo():
    """Devuelve todos los catálogos necesarios para el wizard de cotización."""
    with engine.connect() as conn:

        # Países de ORIGEN con tarifa aérea activa y vigente
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

        # Países de DESTINO con tarifa aérea activa y vigente
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

        # species: id, code, name
        especies = conn.execute(text(
            "SELECT * FROM species WHERE active = true ORDER BY name"
        )).mappings().all()

        # varieties: id, species_id, code, name
        variedades = conn.execute(text(
            "SELECT id, species_id, code, name FROM varieties WHERE active = true ORDER BY name"
        )).mappings().all()

        # product_sizes: id, species_id, size_code, description
        grados = conn.execute(text("""
            SELECT ps.id, ps.size_code, ps.description, s.name AS species_name
            FROM product_sizes ps
            JOIN species s ON s.id = ps.species_id
            WHERE ps.active = true
            ORDER BY s.name, ps.size_code
        """)).mappings().all()

        # box_types: id, box_code, box_name, length_cm, width_cm, height_cm, reference_weight_kg
        box_types = conn.execute(text(
            "SELECT * FROM box_types WHERE active = true ORDER BY length_cm DESC"
        )).mappings().all()

        # airlines: id, airline_code, airline_name
        aerolineas = conn.execute(text(
            "SELECT * FROM airlines WHERE active = true ORDER BY airline_name"
        )).mappings().all()

        # rutas activas: qué aerolíneas tienen tarifa vigente por par de aeropuertos
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

        # airports: id, iata_code, airport_name, city, country_id
        aeropuertos = conn.execute(text("""
            SELECT a.*, c.code AS country_code, c.name AS country_name
            FROM airports a
            LEFT JOIN countries c ON c.id = a.country_id
            WHERE a.active = true
            ORDER BY a.city
        """)).mappings().all()

        # providers — columnas desconocidas, uso SELECT *
        proveedores = []
        try:
            proveedores = conn.execute(text(
                "SELECT * FROM providers WHERE active = true ORDER BY id"
            )).mappings().all()
        except Exception:
            pass

        # incoterms — columnas desconocidas, uso SELECT *
        incoterms_list = []
        try:
            incoterms_list = conn.execute(text(
                "SELECT * FROM incoterms ORDER BY id"
            )).mappings().all()
        except Exception:
            pass

        # exchange_rates — columnas desconocidas, uso SELECT *
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

### api/species.py (patrón CRUD estándar — igual para varieties, product_sizes, box_types, countries, roles, profiles)

`backend/app/api/species.py`
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
            text(
                """
                INSERT INTO species (code, name)
                VALUES (:code, :name)
                RETURNING *
                """
            ),
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
            text(
                """
                UPDATE species
                SET active = false, inactive_date = now(), updated_at = now()
                WHERE id = :id
                RETURNING *
                """
            ),
            {"id": species_id},
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Species not found")
    return row
```

### api/airlines.py

`backend/app/api/airlines.py`
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
            text(
                """
                INSERT INTO airlines (airline_code, airline_name)
                VALUES (:airline_code, :airline_name)
                RETURNING *
                """
            ),
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
            text(
                """
                UPDATE airlines
                SET active = false, inactive_date = now(), updated_at = now()
                WHERE id = :id
                RETURNING *
                """
            ),
            {"id": airline_id},
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Airline not found")
    return row
```

### api/airline_tariffs.py

`backend/app/api/airline_tariffs.py`
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

### api/airports.py

`backend/app/api/airports.py`
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
            text(
                """
                SELECT a.*, c.code AS country_code, c.name AS country_name
                FROM airports a
                LEFT JOIN countries c ON c.id = a.country_id
                ORDER BY a.iata_code
                """
            )
        ).mappings().all()


@router.post("/airports", status_code=201)
def create_airport(payload: AirportCreate):
    data = jsonable_params(payload.model_dump())
    with engine.begin() as conn:
        return conn.execute(
            text(
                """
                INSERT INTO airports (iata_code, airport_name, city, country_id)
                VALUES (:iata_code, :airport_name, :city, :country_id)
                RETURNING *
                """
            ),
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
            text(
                """
                UPDATE airports
                SET active = false, updated_at = now()
                WHERE id = :id
                RETURNING *
                """
            ),
            {"id": airport_id},
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Airport not found")
    return row
```

### api/customers.py

Desde la Fase 4 incluye el campo `es_cliente_especial` (migración 018).

`backend/app/api/customers.py`
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
            text(
                """
                INSERT INTO customers (customer_code, customer_name, contact_name, email, phone)
                VALUES (:customer_code, :customer_name, :contact_name, :email, :phone)
                RETURNING *
                """
            ),
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
            text(
                """
                UPDATE customers
                SET active = false, inactive_date = now(), updated_at = now()
                WHERE id = :id
                RETURNING *
                """
            ),
            {"id": customer_id},
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return row
```

### api/cargo_agencies.py

`backend/app/api/cargo_agencies.py`
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
            text("SELECT * FROM cargo_agencies WHERE id = :id"),
            {"id": agency_id},
        ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Cargo agency not found")
    return row


@router.post("/cargo-agencies", status_code=201)
def create_cargo_agency(payload: CargoAgencyCreate):
    with engine.begin() as conn:
        return conn.execute(
            text(
                """
                INSERT INTO cargo_agencies (code, name, ocr_variants, type, country)
                VALUES (:code, :name, :ocr_variants, :type, :country)
                RETURNING *
                """
            ),
            {
                "code": payload.code,
                "name": payload.name,
                "ocr_variants": payload.ocr_variants or [],
                "type": payload.type,
                "country": payload.country,
            },
        ).mappings().first()


@router.put("/cargo-agencies/{agency_id}")
def update_cargo_agency(agency_id: str, payload: CargoAgencyUpdate):
    raw = payload.model_dump(exclude_unset=True)
    if not raw:
        raise HTTPException(status_code=400, detail="No fields to update")

    data = jsonable_params(raw)
    set_clause = build_set_clause(data)
    data["id"] = agency_id

    with engine.begin() as conn:
        row = conn.execute(
            text(
                f"UPDATE cargo_agencies SET {set_clause}, updated_at = now() "
                f"WHERE id = :id RETURNING *"
            ),
            data,
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Cargo agency not found")
    return row


@router.delete("/cargo-agencies/{agency_id}")
def delete_cargo_agency(agency_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                UPDATE cargo_agencies
                SET active = false, inactive_date = now(), updated_at = now()
                WHERE id = :id
                RETURNING *
                """
            ),
            {"id": agency_id},
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Cargo agency not found")
    return row


@router.get("/cargo-agencies/resolve/{ocr_name}")
def resolve_agency_by_ocr(ocr_name: str):
    """Busca una agencia por variante OCR — útil para el bot de Telegram."""
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT * FROM cargo_agencies
                WHERE active = true
                  AND (
                    LOWER(name) = LOWER(:name)
                    OR :name = ANY(ocr_variants)
                    OR LOWER(:name) = ANY(
                        SELECT LOWER(v) FROM unnest(ocr_variants) v
                    )
                  )
                LIMIT 1
                """
            ),
            {"name": ocr_name},
        ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="No matching agency found")
    return row
```

### api/farms.py

`backend/app/api/farms.py`
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
        return conn.execute(
            text("SELECT * FROM farms ORDER BY name")
        ).mappings().all()


@router.get("/farms/{farm_id}")
def get_farm(farm_id: str):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM farms WHERE id = :id"),
            {"id": farm_id},
        ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Farm not found")
    return row


@router.post("/farms", status_code=201)
def create_farm(payload: FarmCreate):
    with engine.begin() as conn:
        return conn.execute(
            text(
                """
                INSERT INTO farms (code, name, ocr_variants, dartis_postcosecha)
                VALUES (:code, :name, :ocr_variants, :dartis_postcosecha)
                RETURNING *
                """
            ),
            {
                "code": payload.code,
                "name": payload.name,
                "ocr_variants": payload.ocr_variants or [],
                "dartis_postcosecha": payload.dartis_postcosecha,
            },
        ).mappings().first()


@router.put("/farms/{farm_id}")
def update_farm(farm_id: str, payload: FarmUpdate):
    raw = payload.model_dump(exclude_unset=True)
    if not raw:
        raise HTTPException(status_code=400, detail="No fields to update")

    data = jsonable_params(raw)
    set_clause = build_set_clause(data)
    data["id"] = farm_id

    with engine.begin() as conn:
        row = conn.execute(
            text(
                f"UPDATE farms SET {set_clause}, updated_at = now() "
                f"WHERE id = :id RETURNING *"
            ),
            data,
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Farm not found")
    return row


@router.delete("/farms/{farm_id}")
def delete_farm(farm_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                UPDATE farms
                SET active = false, inactive_date = now(), updated_at = now()
                WHERE id = :id
                RETURNING *
                """
            ),
            {"id": farm_id},
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Farm not found")
    return row


@router.get("/farms/resolve/{ocr_name}")
def resolve_farm_by_ocr(ocr_name: str):
    """Normaliza un nombre OCR al registro oficial de finca."""
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT * FROM farms
                WHERE active = true
                  AND (
                    LOWER(name) = LOWER(:name)
                    OR :name = ANY(ocr_variants)
                    OR LOWER(:name) = ANY(
                        SELECT LOWER(v) FROM unnest(ocr_variants) v
                    )
                  )
                LIMIT 1
                """
            ),
            {"name": ocr_name},
        ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="No matching farm found")
    return row
```

---

## 9. Backend — módulo Agrocalidad

Clon de **Agrocalidad Consulta**. El scraping real (Playwright, evade el anti-bot Imperva/Incapsula del sitio de Agrocalidad) sigue viviendo en GitHub Actions del repo `freddyerazo/AgrocalidadDartis` — BLIS no lo reimplementa, solo:
1. Encola la solicitud en `agrocalidad_requests` (misma Supabase que ya usaba el proyecto original).
2. Dispara el workflow `consultar.yml` vía la API REST de GitHub.
3. Permite hacer polling del resultado y consultar el historial ya guardado en `agrocalidad_requirements`.

### schemas/agrocalidad.py

`backend/app/schemas/agrocalidad.py`
```python
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

AREAS_VALIDAS = {"SA", "SV", "IAP", "IAV", "IAF"}
TIPOS_VALIDOS = {"Exportación", "Importación", "Tránsito", "Nacional"}


class AgrocalidadConsultaRequest(BaseModel):
    species_id: UUID
    country_id: UUID
    trade_type: str = "Exportación"
    area_code: str = "SV"


class AgrocalidadRequirement(BaseModel):
    id: UUID
    species_id: UUID
    country_id: UUID
    trade_type: str
    area_code: str
    matched_product_name: Optional[str] = None
    scientific_name: Optional[str] = None
    tariff_heading: Optional[str] = None
    agrocalidad_code: Optional[str] = None
    status: str
    requirements: Optional[str] = None
    queried_at: str


class AgrocalidadSolicitud(BaseModel):
    id: UUID
    status: str
    error_message: Optional[str] = None
    requirement: Optional[AgrocalidadRequirement] = None
```

### api/agrocalidad.py

`backend/app/api/agrocalidad.py`
```python
"""
API del modulo Agrocalidad: consulta de requisitos fitosanitarios de
exportacion (guia.agrocalidad.gob.ec).

El sitio de Agrocalidad esta protegido por Imperva/Incapsula y bloquea
cualquier peticion que no venga de un navegador real, por lo que el
scraping en si NO corre aqui: sigue viviendo en GitHub Actions del repo
freddyerazo/AgrocalidadDartis (workflow "Consultar Agrocalidad", ejecuta
worker_ci.py con Playwright). Este modulo solo:
  1. Encola la solicitud en public.agrocalidad_requests (misma Supabase).
  2. Dispara ese workflow via la API REST de GitHub.
  3. Permite hacer polling del resultado y consultar el historial ya
     guardado en public.agrocalidad_requirements.
"""

import os

import httpx
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.database.connection import engine
from app.schemas.agrocalidad import (
    AREAS_VALIDAS,
    TIPOS_VALIDOS,
    AgrocalidadConsultaRequest,
)

router = APIRouter(prefix="/agrocalidad", tags=["Agrocalidad"])

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO", "freddyerazo/AgrocalidadDartis")
GITHUB_WORKFLOW = "consultar.yml"


@router.get("/catalogo")
def get_catalogo():
    """Especies/paises disponibles y los choices fijos de tipo/area."""
    with engine.connect() as conn:
        especies = conn.execute(text(
            "SELECT id, code, name, name_agrocalidad FROM species "
            "WHERE active = true ORDER BY name"
        )).mappings().all()
        paises = conn.execute(text(
            "SELECT id, code, name, name_es FROM countries "
            "WHERE active = true ORDER BY name_es NULLS LAST, name"
        )).mappings().all()

    return {
        "especies": especies,
        "paises": paises,
        "tipos": sorted(TIPOS_VALIDOS),
        "areas": sorted(AREAS_VALIDAS),
    }


@router.get("/requisitos")
def list_requisitos(species_id: str | None = None, country_id: str | None = None):
    """Historial de requisitos ya consultados (sin relanzar el scraping)."""
    filtros = []
    params = {}
    if species_id:
        filtros.append("r.species_id = :species_id")
        params["species_id"] = species_id
    if country_id:
        filtros.append("r.country_id = :country_id")
        params["country_id"] = country_id
    where = f"WHERE {' AND '.join(filtros)}" if filtros else ""

    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT r.*, s.name AS species_name, c.name_es AS country_name
            FROM agrocalidad_requirements r
            JOIN species s ON s.id = r.species_id
            JOIN countries c ON c.id = r.country_id
            {where}
            ORDER BY r.queried_at DESC
            LIMIT 200
        """), params).mappings().all()
    return rows


@router.get("/solicitud/{request_id}")
def get_solicitud(request_id: str):
    with engine.connect() as conn:
        solicitud = conn.execute(text("""
            SELECT * FROM agrocalidad_requests WHERE id = :id
        """), {"id": request_id}).mappings().first()

        if solicitud is None:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada")

        solicitud = dict(solicitud)
        if solicitud.get("requirement_id"):
            requirement = conn.execute(text("""
                SELECT * FROM agrocalidad_requirements WHERE id = :id
            """), {"id": solicitud["requirement_id"]}).mappings().first()
            solicitud["requirement"] = requirement

    return solicitud


@router.post("/consultar", status_code=201)
def crear_consulta(payload: AgrocalidadConsultaRequest):
    if payload.trade_type not in TIPOS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"trade_type invalido: {payload.trade_type}")
    if payload.area_code not in AREAS_VALIDAS:
        raise HTTPException(status_code=400, detail=f"area_code invalido: {payload.area_code}")

    with engine.begin() as conn:
        solicitud = conn.execute(text("""
            INSERT INTO agrocalidad_requests (species_id, country_id, trade_type, area_code, status)
            VALUES (:species_id, :country_id, :trade_type, :area_code, 'pending')
            RETURNING *
        """), {
            "species_id": str(payload.species_id),
            "country_id": str(payload.country_id),
            "trade_type": payload.trade_type,
            "area_code": payload.area_code,
        }).mappings().first()

    _disparar_workflow(str(solicitud["id"]))
    return solicitud


def _disparar_workflow(request_id: str):
    if not GITHUB_TOKEN:
        # Sin token configurado: la solicitud queda encolada como "pending"
        # y puede procesarse manualmente desde GitHub Actions mientras tanto.
        return

    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{GITHUB_WORKFLOW}/dispatches"
    try:
        resp = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
            },
            json={"ref": "main", "inputs": {"request_id": request_id}},
            timeout=15,
        )
        resp.raise_for_status()
    except httpx.HTTPError as e:
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE agrocalidad_requests
                SET status = 'error', error_message = :msg, updated_at = now()
                WHERE id = :id
            """), {"id": request_id, "msg": f"No se pudo disparar el workflow: {e}"})
```

---

## 10. Backend — módulo Inventario LAG

Clon de **InventarioApiLag**. Proxy stateless sobre las APIs del WMS de Logiztik Alliance Group (bodega de Bellaflor en Miami) — sin tabla propia, todo se consulta en vivo. A diferencia del proyecto original no valida un `X-API-Key` propio: ese proyecto exponía el backend a un frontend externo en GitHub Pages; aquí el frontend lo sirve el propio backend de BLIS, igual que el resto de módulos.

**Pestaña "Posteo de Inventario" (agosto 2026)** — nueva sub-pestaña que llama al endpoint legacy `PlaceOrder/ordernew` de LAG (host y token propios, `cloudus.logiztikalliance.com:5005`, **sin ambiente de pruebas**: cualquier posteo desde BLIS impacta producción real de LAG de inmediato). Los 3 campos del formulario están conectados a datos reales de BLIS/LAG en vez de texto libre, cada uno vía el componente reutilizable `crearComboBuscable` (combo con buscador, en `inventario-lag.js`):

| Campo | Fuente | Detalle |
|---|---|---|
| Cliente | `GET /api/customers` | filtrado a solo los que tienen `customer_code_lag`; el combo muestra el nombre, el valor real enviado a LAG es el código |
| Carrier | `GET /api/truck-companies` | nueva tabla `truck_company` (ver abajo), el valor enviado es `id_logistic_carrier` |
| Box ID (por caja) | `GET /api/inventario-lag/pieces` | piezas disponibles en bodega Miami, consultadas en vivo a LAG y cacheadas una sola vez por formulario (todas las filas de caja comparten la misma promesa) para no repetir la llamada |

Antes de enviar, el formulario pide confirmación (`window.confirm`) mostrando cliente, carrier, fecha y cajas — dado que no hay sandbox, esta es la única red de seguridad antes de tocar producción de LAG.

### schemas/inventario_lag.py

`backend/app/schemas/inventario_lag.py`
```python
from typing import Literal, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Inventario
# ---------------------------------------------------------------------------


class PieceInInventory(BaseModel):
    barcode: str
    rack: str


class RackSummary(BaseModel):
    rack: str
    piezas: int


class InventoryResponse(BaseModel):
    total_piezas: int
    total_racks: int
    piezas: list[PieceInInventory]
    resumen_racks: list[RackSummary]


class PiezaDetalle(BaseModel):
    """Una pieza con las columnas equivalentes al reporte ResumenCodigosDeBarra del WMS.

    Combina Barcode Information V2 (detalle) con Pieces in Inventory (ubicacion).
    """

    status: str = ""
    barcode: str = ""
    shipment_nr: str = ""
    house: str = ""
    exporter: str = ""
    consignee: str = ""
    carrier: str = ""
    location: Optional[str] = None
    product: str = ""
    description: str = ""
    tipo: str = ""
    largo_cm: Optional[float] = None
    ancho_cm: Optional[float] = None
    alto_cm: Optional[float] = None
    largo_inch: Optional[float] = None
    ancho_inch: Optional[float] = None
    alto_inch: Optional[float] = None
    unidades: Optional[int] = None
    precio: Optional[float] = None
    peso: Optional[float] = None
    valor_caja: Optional[float] = None


class InventarioCompleto(BaseModel):
    total_piezas: int
    total_recibidas: int
    total_pendientes: int
    total_unidades: int
    valor_total: float
    guias_consultadas: list[str]
    avisos: list[str]
    piezas: list[PiezaDetalle]


# ---------------------------------------------------------------------------
# Ordenes de compra
# ---------------------------------------------------------------------------


class PurchaseOrderItem(BaseModel):
    farm_code: str = Field(max_length=32, description="Codigo del proveedor/finca")
    length: float
    width: float
    height: float
    gross_weight: float
    unit_of_measurement: Literal["CM", "INCH"] = "CM"
    barcode: Optional[str] = Field(default=None, max_length=11)
    box_size: Optional[str] = Field(default=None, max_length=16)
    product_code: Optional[str] = Field(default=None, max_length=32)
    product_description: Optional[str] = Field(default=None, max_length=128)
    packing: Optional[int] = None
    unit_price: Optional[float] = None
    ship_to_code: Optional[str] = Field(default=None, max_length=32)
    carrier_code: Optional[str] = Field(default=None, max_length=8)
    dispatch_date: Optional[str] = Field(default=None, description="Formato YYYY-MM-DD")
    comments: Optional[str] = Field(default=None, max_length=256)


class PurchaseOrderIn(BaseModel):
    consignee_code: str = Field(max_length=32)
    destination_port_code: str = Field(max_length=3, description="Codigo IATA")
    post_type: Literal["LOCAL", "FINAL"]
    warehouse_code: Optional[str] = Field(default=None, max_length=8, description="Requerido si post_type=LOCAL")
    po_number: Optional[str] = Field(default=None, max_length=32)
    origin_port_code: Optional[str] = Field(default=None, max_length=3)
    estimated_date: Optional[str] = Field(default=None, description="Formato YYYY-MM-DD")
    comments: Optional[str] = Field(default=None, max_length=256)
    accion: Literal["INSERT", "DELETE"] = "INSERT"
    items: list[PurchaseOrderItem] = Field(min_length=1)


class PurchaseOrderResult(BaseModel):
    is_success: bool
    errors: list[dict[str, str]] = []
    raw_response: str


# ---------------------------------------------------------------------------
# Ordenes de venta
# ---------------------------------------------------------------------------


class SalesOrderBox(BaseModel):
    boxId: str = Field(max_length=16)
    unitPrice: Optional[float] = None
    markCode: Optional[str] = Field(default=None, max_length=16)
    units: Optional[int] = None


class SalesOrderIn(BaseModel):
    customerId: str = Field(max_length=16)
    carrierId: str = Field(max_length=16)
    shipDate: str = Field(description="Formato MM/dd/yyyy")
    orderNumber: str = Field(max_length=16)
    idOrder: int
    poNumber: Optional[str] = Field(default=None, max_length=16)
    generateBOL: Optional[bool] = None
    boxIds: list[SalesOrderBox] = Field(min_length=1)


class SalesOrderCancelIn(BaseModel):
    idOrder: int


# ---------------------------------------------------------------------------
# Posteo de inventario (endpoint legacy PlaceOrder/ordernew)
# ---------------------------------------------------------------------------


class PlaceOrderBox(BaseModel):
    boxId: str = Field(max_length=16)
    stemPrice: Optional[float] = None


class PlaceOrderIn(BaseModel):
    customerId: str = Field(max_length=32)
    carrierId: str = Field(max_length=16)
    miamiShipDate: str = Field(description="Formato MM/dd/yyyy")
    printWmsLabels: bool = True
    boxIds: list[PlaceOrderBox] = Field(min_length=1)


class PlaceOrderResult(BaseModel):
    raw_response: str
```

### services/lag_client.py — OAuth2 + Track API de LAG + place_order (Posteo de Inventario)

`backend/app/services/lag_client.py`
```python
"""
Cliente para las APIs de Logiztik Alliance Group (LAG): el WMS que
almacena el inventario de cajas de Bellaflor en Miami.

Clonado de InventarioApiLag/backend/app/lag_client.py, adaptado al
estilo de BLIS (variables de entorno via os.getenv, sin pydantic-settings).
"""

import os

import httpx
from fastapi import HTTPException, status

LAG_ENV = os.getenv("LAG_ENV", "test")
LAG_CUSTOMER_CODE = os.getenv("LAG_CUSTOMER_CODE", "")
LAG_TOKEN = os.getenv("LAG_TOKEN", "")
LAG_SALES_API_KEY = os.getenv("LAG_SALES_API_KEY", "")
LAG_TIMEOUT = float(os.getenv("LAG_TIMEOUT", "30"))

LAG_BASE_URL = (
    "https://cloud.logiztikalliance.com:5005/logCloudWS"
    if LAG_ENV == "prod"
    else "https://training.logiztik.com:5005/logCloudWSPre"
)
LAG_SALES_BASE_URL = (
    "https://salesapi.logiztikalliance.com"
    if LAG_ENV == "prod"
    else "https://sandsalesapi1.logiztikalliance.com"
)

# Endpoint legacy "PlaceOrder/ordernew" (posteo de inventario). A diferencia
# del resto de APIs de LAG, no tiene ambiente de pruebas: solo existe este
# host de produccion, y token propio (distinto de LAG_TOKEN).
LAG_PLACE_ORDER_BASE_URL = os.getenv(
    "LAG_PLACE_ORDER_BASE_URL", "https://cloudus.logiztikalliance.com:5005/external/api"
)
LAG_PLACE_ORDER_TOKEN = os.getenv("LAG_PLACE_ORDER_TOKEN", "")


async def _request(method: str, url: str, **kwargs) -> httpx.Response:
    try:
        async with httpx.AsyncClient(timeout=LAG_TIMEOUT) as client:
            response = await client.request(method, url, **kwargs)
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Tiempo de espera agotado al contactar los servicios de LAG.",
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"No se pudo contactar los servicios de LAG: {exc}",
        )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LAG respondio {response.status_code}: {response.text[:500]}",
        )
    return response


def _json(response: httpx.Response):
    try:
        return response.json()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Respuesta no valida de LAG: {response.text[:500]}",
        )


async def create_purchase_order(xml_body: str) -> str:
    url = (
        f"{LAG_BASE_URL}/api/Pos/"
        f"InsertarPosXmlClientesAllianceNuevaVersion/{LAG_TOKEN}"
    )
    response = await _request(
        "POST", url, content=xml_body.encode("utf-8"), headers={"Content-Type": "application/xml"}
    )
    return response.text


async def get_pieces_in_inventory() -> list[dict]:
    """Piezas disponibles en la bodega de Miami.

    LAG no distingue en la respuesta entre "sin inventario", "token invalido" y
    "codigo de cliente invalido": los tres devuelven []. Los parametros faltantes
    devuelven una cadena vacia, y los errores de base de datos un objeto con
    la clave "mensaje". Aqui se normaliza todo eso.
    """
    url = (
        f"{LAG_BASE_URL}/api/ClientesExternosA/"
        f"ListarCodigosDeBarraDisponiblesUbicacion/{LAG_CUSTOMER_CODE}/{LAG_TOKEN}"
    )
    response = await _request("GET", url)

    if not response.text.strip():
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "LAG respondio vacio: faltan parametros. "
                "Revise LAG_CUSTOMER_CODE y LAG_TOKEN en la configuracion del servidor."
            ),
        )

    data = _json(response)

    if isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LAG reporto un error: {data.get('mensaje', data)}",
        )

    if not isinstance(data, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Formato inesperado en la respuesta de LAG: {response.text[:200]}",
        )

    return data


async def get_barcode_info(shipment_nr: str):
    url = (
        f"{LAG_BASE_URL}/api/v2/ClientesExternosA/"
        f"ListarCodigosDeBarraPorClienteNew/{LAG_CUSTOMER_CODE}/{shipment_nr}"
    )
    return _json(await _request("GET", url, params={"authenticationToken": LAG_TOKEN}))


async def get_shipment_info(date: str):
    url = (
        f"{LAG_BASE_URL}/api/ClientesExternosA/"
        f"ListarTotalesGuiasPorClienteV2/{LAG_CUSTOMER_CODE}/{date}"
    )
    return _json(await _request("GET", url, params={"authenticationToken": LAG_TOKEN}))


async def get_pieces_dispatched(date: str):
    url = (
        f"{LAG_BASE_URL}/api/ClientesExternosA/"
        f"ListarCodigosDeBarraDespachadosFecha/{LAG_CUSTOMER_CODE}/{LAG_TOKEN}/{date}"
    )
    return _json(await _request("GET", url))


async def create_sales_order(payload: dict):
    url = f"{LAG_SALES_BASE_URL}/Order/new"
    response = await _request(
        "POST", url, json=payload, headers={"apiKey": LAG_SALES_API_KEY}
    )
    return _json(response)


async def cancel_sales_order(id_order: int):
    url = f"{LAG_SALES_BASE_URL}/order/cancel"
    response = await _request(
        "POST",
        url,
        json={"idOrder": id_order},
        headers={"apiKey": LAG_SALES_API_KEY},
    )
    return _json(response)


async def place_order(customer_id: str, carrier_id: str, miami_ship_date: str,
                       boxes: list[dict], print_wms_labels: bool = True) -> str:
    """Posteo de inventario via el endpoint legacy PlaceOrder/ordernew.

    boxes: [{"box_id": str, "stem_price": float | None}, ...]. Sin
    documentacion oficial del formato de respuesta (texto/XML/JSON segun el
    caso) -- se devuelve el texto crudo tal cual, sin asumir su forma.
    """
    if not LAG_PLACE_ORDER_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LAG_PLACE_ORDER_TOKEN no configurado en el servidor.",
        )

    params = {
        "token": LAG_PLACE_ORDER_TOKEN,
        "customerId": customer_id,
        "carrierId": carrier_id,
        "miamiShipDate": miami_ship_date,
        "printWmsLabels": "1" if print_wms_labels else "0",
    }
    for i, box in enumerate(boxes):
        params[f"boxIds[{i}]"] = box["box_id"]
        if box.get("stem_price") is not None:
            params[f"stemPrice[{i}]"] = str(box["stem_price"])

    url = f"{LAG_PLACE_ORDER_BASE_URL}/PlaceOrder/ordernew"
    response = await _request("GET", url, params=params)
    return response.text
```

### services/lag_xml_utils.py — construcción/parseo del XML de órdenes de compra

`backend/app/services/lag_xml_utils.py`
```python
"""Construccion/parseo del XML que espera la API de ordenes de compra de LAG.

Clonado de InventarioApiLag/backend/app/xml_utils.py sin cambios de logica.
"""

import xml.etree.ElementTree as ET

from app.schemas.inventario_lag import PurchaseOrderIn


def _add(parent: ET.Element, tag: str, value) -> None:
    ET.SubElement(parent, tag).text = "" if value is None else str(value)


def build_purchase_order_xml(order: PurchaseOrderIn) -> str:
    root = ET.Element("XMLPosAlliance")
    po = ET.SubElement(root, "Po")

    header = ET.SubElement(po, "Header")
    _add(header, "WarehouseCode", order.warehouse_code)
    _add(header, "ConsigneeCode", order.consignee_code)
    _add(header, "PoNumber", order.po_number)
    _add(header, "OriginPortCode", order.origin_port_code)
    _add(header, "DestinationPortCode", order.destination_port_code)
    _add(header, "EstimatedDate", order.estimated_date)
    _add(header, "Comments", order.comments)
    _add(header, "PostType", order.post_type)
    _add(header, "Accion", order.accion)

    details = ET.SubElement(po, "Details")
    for item in order.items:
        detail = ET.SubElement(details, "Detail")
        _add(detail, "ShipToCode", item.ship_to_code)
        _add(detail, "CarrierCode", item.carrier_code)
        _add(detail, "DispatchDate", item.dispatch_date)
        _add(detail, "FarmCode", item.farm_code)
        _add(detail, "Barcode", item.barcode)
        _add(detail, "BoxSize", item.box_size)
        _add(detail, "ProductCode", item.product_code)
        _add(detail, "ProductDescription", item.product_description)
        _add(detail, "Packing", item.packing)
        _add(detail, "UnitPrice", item.unit_price)
        _add(detail, "Length", item.length)
        _add(detail, "Width", item.width)
        # LAG escribe "Hight" (sic) en su especificacion; no corregir el nombre del tag.
        _add(detail, "Hight", item.height)
        _add(detail, "GrossWeight", item.gross_weight)
        _add(detail, "UnitOfMeasurement", item.unit_of_measurement)
        _add(detail, "Comments", item.comments)

    return ET.tostring(root, encoding="unicode")


def parse_po_status(xml_text: str) -> tuple[bool, list[dict[str, str]]]:
    root = ET.fromstring(xml_text)
    success_node = root.find(".//IsSuccess")
    is_success = success_node is not None and (success_node.text or "").strip().lower() == "true"

    errors = []
    for node in root.iter("PoErrorDetails"):
        po_number = node.findtext("POnumber") or ""
        message = node.findtext("Message") or ""
        errors.append({"poNumber": po_number.strip(), "message": message.strip()})

    return is_success, errors
```

### services/lag_inventario_completo.py — reconstruye el reporte ResumenCodigosDeBarra

`backend/app/services/lag_inventario_completo.py`
```python
"""Reconstruye el reporte ResumenCodigosDeBarra combinando varias APIs de LAG.

Ninguna API entrega ese reporte completo:

  - Shipment Information V2  -> que guias (AWB) hubo en una fecha
  - Barcode Information V2   -> el detalle de cada pieza de una guia
  - Pieces in Inventory      -> la ubicacion (rack), que el detalle no trae

Once columnas del reporte original (Days, PO, Warehouse, Ship To, Legal Name,
Dispatch Date, Received O/D, Pallet Label, Manifest Nr y User) no las expone
ninguna API documentada, por lo que no se reconstruyen aqui.

Clonado de InventarioApiLag/backend/app/inventario_completo.py sin cambios
de logica.
"""

import re
from typing import Optional

from app.schemas.inventario_lag import PiezaDetalle

CM_POR_INCH = 2.54


def solo_digitos(guia) -> str:
    return re.sub(r"\D", "", str(guia or ""))


def formatear_guia(guia) -> str:
    """Presenta el AWB como en el reporte del WMS: 02303269313 -> '023-0326 9313'."""
    d = solo_digitos(guia)
    if len(d) != 11:
        return str(guia or "").strip()
    return f"{d[:3]}-{d[3:7]} {d[7:]}"


def _numero(valor) -> Optional[float]:
    if valor is None or valor == "":
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _texto(item: dict, *claves: str) -> str:
    """Lee la primera clave presente, tolerando variaciones de mayusculas de LAG."""
    normalizado = {str(k).lower(): v for k, v in item.items()}
    for clave in claves:
        valor = normalizado.get(clave.lower())
        if valor not in (None, ""):
            return str(valor).strip()
    return ""


def _dimensiones(valor: Optional[float], unidad: str) -> tuple[Optional[float], Optional[float]]:
    """Devuelve (cm, inch). El reporte del WMS muestra ambas, redondeando la convertida."""
    if valor is None:
        return None, None
    if unidad.upper().startswith("INCH"):
        return round(valor * CM_POR_INCH), valor
    return valor, round(valor / CM_POR_INCH)


def construir_pieza(detalle: dict, guia: str, racks: dict[str, str]) -> PiezaDetalle:
    unidad = _texto(detalle, "unitOfMeasurement") or "CM"
    largo_cm, largo_inch = _dimensiones(_numero(detalle.get("length")), unidad)
    ancho_cm, ancho_inch = _dimensiones(_numero(detalle.get("width")), unidad)
    alto_cm, alto_inch = _dimensiones(_numero(detalle.get("height")), unidad)

    barcode = _texto(detalle, "barcode")
    unidades = _numero(detalle.get("packing"))
    precio = _numero(detalle.get("piecePrice"))

    return PiezaDetalle(
        status=_texto(detalle, "status"),
        barcode=barcode,
        shipment_nr=formatear_guia(guia),
        house=_texto(detalle, "hawb"),
        exporter=_texto(detalle, "exporterName", "exporterCode"),
        consignee=_texto(detalle, "consigneeName", "consigneeCode"),
        carrier=_texto(detalle, "carrierName", "carrierCode"),
        location=racks.get(barcode),
        product=_texto(detalle, "productCode"),
        description=_texto(detalle, "productDescription"),
        tipo=_texto(detalle, "boxSize"),
        largo_cm=largo_cm,
        ancho_cm=ancho_cm,
        alto_cm=alto_cm,
        largo_inch=largo_inch,
        ancho_inch=ancho_inch,
        alto_inch=alto_inch,
        unidades=int(unidades) if unidades is not None else None,
        precio=precio,
        peso=_numero(detalle.get("grossWeight")),
        # El reporte del WMS trata Price como precio unitario: el valor de la
        # caja es unidades x precio (270 tallos x 0.323 = 87.21).
        valor_caja=round(unidades * precio, 2) if unidades and precio else None,
    )


def mapa_de_racks(piezas_inventario) -> dict[str, str]:
    mapa = {}
    for item in piezas_inventario or []:
        if not isinstance(item, dict):
            continue
        barcode = _texto(item, "barcode")
        rack = _texto(item, "rack")
        if barcode and rack:
            mapa[barcode] = rack
    return mapa


def esta_recibida(status: str) -> bool:
    return "RECEIV" in (status or "").upper()
```

### api/inventario_lag.py

`backend/app/api/inventario_lag.py`
```python
"""
API del modulo Inventario LAG: proxy sobre las APIs del WMS de Logiztik
Alliance Group (bodega de Bellaflor en Miami).

Clonado de InventarioApiLag (proyecto standalone). LAG es el sistema de
registro real; este modulo no persiste nada en la base de BLIS, siempre
consulta en vivo. A diferencia del proyecto original, no valida un
X-API-Key propio: el frontend de InventarioApiLag era una pagina publica
en GitHub Pages llamando a un backend externo, mientras que aqui el
frontend lo sirve el mismo backend de BLIS (igual que el resto de modulos).
"""

import asyncio
from collections import Counter
from datetime import date as date_type
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status as http_status

from app.schemas.inventario_lag import (
    InventarioCompleto,
    InventoryResponse,
    PieceInInventory,
    PiezaDetalle,
    PlaceOrderIn,
    PlaceOrderResult,
    PurchaseOrderIn,
    PurchaseOrderResult,
    RackSummary,
    SalesOrderCancelIn,
    SalesOrderIn,
)
from app.services import lag_client
from app.services import lag_inventario_completo as ic
from app.services.lag_xml_utils import build_purchase_order_xml, parse_po_status

router = APIRouter(prefix="/inventario-lag", tags=["Inventario LAG"])

SIN_UBICACION = "SIN UBICACION"

# Llamadas simultaneas maximas a Barcode Information V2, para no saturar a LAG.
MAX_CONCURRENTES = 4


@router.get("/health")
async def health():
    return {"status": "ok", "lag_env": lag_client.LAG_ENV}


@router.get("/pieces", response_model=InventoryResponse)
async def piezas_en_inventario() -> InventoryResponse:
    """Lista las piezas disponibles en bodega, con el resumen por ubicacion."""
    crudo = await lag_client.get_pieces_in_inventory()

    piezas = [
        PieceInInventory(
            barcode=str(item.get("barcode") or "").strip(),
            rack=str(item.get("rack") or "").strip() or SIN_UBICACION,
        )
        for item in crudo
        if isinstance(item, dict)
    ]
    piezas.sort(key=lambda p: (p.rack, p.barcode))

    conteo = Counter(pieza.rack for pieza in piezas)
    resumen = [RackSummary(rack=rack, piezas=n) for rack, n in sorted(conteo.items())]

    return InventoryResponse(
        total_piezas=len(piezas),
        total_racks=len(resumen),
        piezas=piezas,
        resumen_racks=resumen,
    )


@router.get("/barcode/{shipment_nr}")
async def info_codigos_barra(shipment_nr: str):
    return await lag_client.get_barcode_info(shipment_nr)


@router.get("/full", response_model=InventarioCompleto)
async def inventario_detallado(
    fecha: Optional[date_type] = Query(
        default=None, description="Fecha de embarque (YYYY-MM-DD) para descubrir las guias"
    ),
    guias: Optional[str] = Query(
        default=None, description="Guias separadas por coma, en lugar de descubrirlas por fecha"
    ),
) -> InventarioCompleto:
    """Reconstruye el reporte ResumenCodigosDeBarra combinando tres APIs de LAG.

    Indique una fecha (para descubrir las guias del dia) o una lista de guias.
    """
    avisos: list[str] = []

    # 1. Determinar que guias consultar.
    if guias:
        lista_guias = [g.strip() for g in guias.split(",") if g.strip()]
    elif fecha:
        envios = await lag_client.get_shipment_info(fecha.isoformat())
        if isinstance(envios, dict):
            raise HTTPException(
                status_code=http_status.HTTP_502_BAD_GATEWAY,
                detail=f"LAG reporto un error al listar los envios: {envios.get('mensaje', envios)}",
            )
        lista_guias = [str(e.get("awb")).strip() for e in envios or [] if e.get("awb")]
        if not lista_guias:
            avisos.append(f"LAG no reporta guias para el {fecha.isoformat()}.")
    else:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Indique 'fecha' o 'guias'.",
        )

    # 2. Detalle de cada guia, en paralelo pero con tope de concurrencia.
    semaforo = asyncio.Semaphore(MAX_CONCURRENTES)

    async def detalle(guia: str):
        async with semaforo:
            try:
                return guia, await lag_client.get_barcode_info(guia)
            except HTTPException as exc:
                return guia, exc

    resultados = await asyncio.gather(*(detalle(g) for g in lista_guias))

    # 3. Ubicaciones. Si falla, seguimos sin racks en vez de perder todo el reporte.
    racks: dict[str, str] = {}
    try:
        racks = ic.mapa_de_racks(await lag_client.get_pieces_in_inventory())
    except HTTPException as exc:
        avisos.append(f"No se pudieron obtener las ubicaciones: {exc.detail}")

    # 4. Armar las piezas.
    piezas: list[PiezaDetalle] = []
    for guia, respuesta in resultados:
        if isinstance(respuesta, HTTPException):
            avisos.append(f"Guia {ic.formatear_guia(guia)}: {respuesta.detail}")
            continue
        if isinstance(respuesta, dict):
            avisos.append(f"Guia {ic.formatear_guia(guia)}: {respuesta.get('mensaje', respuesta)}")
            continue
        for item in respuesta or []:
            if isinstance(item, dict):
                piezas.append(ic.construir_pieza(item, guia, racks))

    piezas.sort(key=lambda p: (p.consignee, p.barcode))

    recibidas = sum(1 for p in piezas if ic.esta_recibida(p.status))
    return InventarioCompleto(
        total_piezas=len(piezas),
        total_recibidas=recibidas,
        total_pendientes=len(piezas) - recibidas,
        total_unidades=sum(p.unidades or 0 for p in piezas),
        valor_total=round(sum(p.valor_caja or 0 for p in piezas), 2),
        guias_consultadas=[ic.formatear_guia(g) for g in lista_guias],
        avisos=avisos,
        piezas=piezas,
    )


@router.get("/shipments")
async def info_envios(fecha: date_type = Query(description="Fecha del envio (YYYY-MM-DD)")):
    return await lag_client.get_shipment_info(fecha.isoformat())


@router.get("/dispatched")
async def piezas_despachadas(fecha: date_type = Query(description="Fecha de despacho (YYYY-MM-DD)")):
    return await lag_client.get_pieces_dispatched(fecha.isoformat())


@router.post("/purchase-orders", response_model=PurchaseOrderResult)
async def crear_orden_compra(order: PurchaseOrderIn) -> PurchaseOrderResult:
    if order.post_type == "LOCAL" and not order.warehouse_code:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="warehouse_code es obligatorio cuando post_type es LOCAL.",
        )

    xml_body = build_purchase_order_xml(order)
    raw = await lag_client.create_purchase_order(xml_body)

    try:
        is_success, errors = parse_po_status(raw)
    except Exception:
        raise HTTPException(
            status_code=http_status.HTTP_502_BAD_GATEWAY,
            detail=f"Respuesta XML no valida de LAG: {raw[:500]}",
        )

    return PurchaseOrderResult(is_success=is_success, errors=errors, raw_response=raw)


@router.post("/sales-orders")
async def crear_orden_venta(order: SalesOrderIn):
    return await lag_client.create_sales_order(order.model_dump(exclude_none=True))


@router.post("/sales-orders/cancel")
async def cancelar_orden_venta(payload: SalesOrderCancelIn):
    return await lag_client.cancel_sales_order(payload.idOrder)


@router.post("/posteo-inventario", response_model=PlaceOrderResult)
async def posteo_inventario(payload: PlaceOrderIn) -> PlaceOrderResult:
    """Endpoint legacy PlaceOrder/ordernew de LAG. Sin ambiente de pruebas:
    cada llamada crea una orden real en el WMS de produccion."""
    boxes = [{"box_id": b.boxId, "stem_price": b.stemPrice} for b in payload.boxIds]
    raw = await lag_client.place_order(
        customer_id=payload.customerId,
        carrier_id=payload.carrierId,
        miami_ship_date=payload.miamiShipDate,
        boxes=boxes,
        print_wms_labels=payload.printWmsLabels,
    )
    return PlaceOrderResult(raw_response=raw)
```

### schemas/truck_company.py — catálogo de carriers de Miami (Posteo de Inventario)

`backend/app/schemas/truck_company.py`
```python
from typing import Optional

from pydantic import BaseModel


class TruckCompanyCreate(BaseModel):
    carrier_name: str
    sub_carrier_name: Optional[str] = None
    country: Optional[str] = None
    id_logistic_carrier: str


class TruckCompanyUpdate(BaseModel):
    carrier_name: Optional[str] = None
    sub_carrier_name: Optional[str] = None
    country: Optional[str] = None
    id_logistic_carrier: Optional[str] = None
    active: Optional[bool] = None
```

### api/truck_company.py — CRUD estándar, seed de 139 carriers reales desde 'ID clientes.xlsx' hoja Listado de Carriers-Miami

`backend/app/api/truck_company.py`
```python
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.database.connection import engine
from app.database.helpers import build_set_clause, jsonable_params
from app.schemas.truck_company import TruckCompanyCreate, TruckCompanyUpdate

router = APIRouter()


@router.get("/truck-companies")
def list_truck_companies():
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT * FROM truck_company WHERE active = true ORDER BY carrier_name, sub_carrier_name")
        ).mappings().all()


@router.post("/truck-companies", status_code=201)
def create_truck_company(payload: TruckCompanyCreate):
    with engine.begin() as conn:
        return conn.execute(
            text(
                """
                INSERT INTO truck_company (carrier_name, sub_carrier_name, country, id_logistic_carrier)
                VALUES (:carrier_name, :sub_carrier_name, :country, :id_logistic_carrier)
                RETURNING *
                """
            ),
            payload.model_dump(),
        ).mappings().first()


@router.put("/truck-companies/{truck_company_id}")
def update_truck_company(truck_company_id: str, payload: TruckCompanyUpdate):
    data = jsonable_params(payload.model_dump(exclude_unset=True))
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = build_set_clause(data)
    data["id"] = truck_company_id

    with engine.begin() as conn:
        row = conn.execute(
            text(f"UPDATE truck_company SET {set_clause}, updated_at = now() WHERE id = :id RETURNING *"),
            data,
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Truck company not found")
    return row


@router.delete("/truck-companies/{truck_company_id}")
def delete_truck_company(truck_company_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            text("UPDATE truck_company SET active = false, updated_at = now() WHERE id = :id RETURNING *"),
            {"id": truck_company_id},
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Truck company not found")
    return row
```

---

## 11. Backend — módulo Torre de Control

Clon de **REPORTEUPSFEDEX**. Concilia, por factura, las cajas declaradas en Dartis contra el manifiesto/tracking en vivo de UPS, FedEx o una agencia de carga local.

**Hallazgo clave de esta fase**: el proyecto original pedía subir un Excel Dartis propio (`empresa, factura, cliente, destinatario, courier, total, fecha, vendedor`) además de los manifiestos de UPS/FedEx. Verificado contra la Supabase real: `dartis_ventas` agrupada por `id_pedido` produce exactamente esa misma forma (`SUM(total_piezas)` = `total`), sin ninguna inconsistencia en las 10,774 facturas de la tabla — así que el `DartisExcelConnector` del original se elimina por completo. Solo hacen falta las subidas de manifiesto UPS (.csv) y FedEx (.pdf), que sí son datos que no existen en ningún otro lado de BLIS.

También desaparece el hack de "persistir subiendo archivos vía `git commit`" (crear/pushear commits desde el servidor con un PAT embebido en la URL remota) — los manifiestos se parsean directo a Postgres al subirlos. Y se corrigió un bug del original: `shipper_name` en la sincronización con Duoplane quedaba hardcodeado a `"UPS"` incluso para trackings de FedEx.

### services/courier_ups_client.py — OAuth2 + Track API de UPS

`backend/app/services/courier_ups_client.py`
```python
"""Cliente OAuth2 + Track API de UPS.

Clonado de REPORTEUPSFEDEX (clase UPSConnector). El token se cachea en
memoria a nivel de modulo (expira en ~1h, se re-obtiene solo) — no hace
falta persistirlo en Postgres.
"""

import os
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

UTC = timezone.utc
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"

_token: Optional[str] = None
_token_exp: datetime = datetime.min.replace(tzinfo=UTC)


def _base_url() -> str:
    return os.getenv("UPS_BASE_URL", "https://onlinetools.ups.com")


async def _get_token(client: httpx.AsyncClient) -> str:
    global _token, _token_exp
    if _token and datetime.now(UTC) < _token_exp:
        return _token
    r = await client.post(
        f"{_base_url()}/security/v1/oauth/token",
        data={"grant_type": "client_credentials"},
        auth=(os.getenv("UPS_CLIENT_ID", ""), os.getenv("UPS_CLIENT_SECRET", "")),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    r.raise_for_status()
    j = r.json()
    _token = j["access_token"]
    _token_exp = datetime.now(UTC) + timedelta(seconds=int(j.get("expires_in", 3600)) - 60)
    return _token


def _demo(trackings: list[str]) -> dict[str, dict]:
    estados = ["EN TRANSITO", "ENTREGADO", "EN ADUANA", "RECIBIDO EN ORIGEN", "EN REPARTO"]
    out = {}
    for t in trackings:
        rnd = random.Random(t)
        out[t] = {
            "estado": rnd.choice(estados),
            "cajas_manifiesto": None,
            "ultimo_evento": rnd.choice(["Louisville, KY", "Miami, FL", "Quito, EC", "Bogota, CO"]),
            "ts": datetime.now(UTC).isoformat(),
        }
    return out


async def track(trackings: list[str]) -> dict[str, dict]:
    if DEMO_MODE:
        return _demo(trackings)
    out: dict[str, dict] = {}
    async with httpx.AsyncClient(timeout=30) as client:
        token = await _get_token(client)
        for t in trackings:
            try:
                r = await client.get(
                    f"{_base_url()}/api/track/v1/details/{t}",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "transId": f"sys-{int(datetime.now(UTC).timestamp())}",
                        "transactionSrc": "blis-torre-control",
                    },
                )
                r.raise_for_status()
                shp = r.json()["trackResponse"]["shipment"][0]
                pkg = shp.get("package", [])
                act = (pkg[0].get("activity") or [{}])[0] if pkg else {}
                out[t] = {
                    "estado": (act.get("status") or {}).get("description", "SIN DATOS"),
                    "cajas_manifiesto": len(pkg) or None,
                    "ultimo_evento": (act.get("location") or {}).get("address", {}).get("city", ""),
                    "ts": datetime.now(UTC).isoformat(),
                }
            except Exception as e:
                out[t] = {
                    "estado": f"ERROR: {e.__class__.__name__}",
                    "cajas_manifiesto": None, "ultimo_evento": "",
                    "ts": datetime.now(UTC).isoformat(),
                }
    return out
```

### services/courier_fedex_client.py — OAuth2 + Track API de FedEx

`backend/app/services/courier_fedex_client.py`
```python
"""Cliente OAuth2 + Track API de FedEx.

Clonado de REPORTEUPSFEDEX (clase FedExConnector + _consultar_estado_real_fedex).
Token cacheado en memoria a nivel de modulo, igual que el UPS client.
"""

import os
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

UTC = timezone.utc
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"

_token: Optional[str] = None
_token_exp: datetime = datetime.min.replace(tzinfo=UTC)


def _base_url() -> str:
    return os.getenv("FEDEX_BASE_URL", "https://apis.fedex.com")


async def _get_token(client: httpx.AsyncClient) -> str:
    global _token, _token_exp
    if _token and datetime.now(UTC) < _token_exp:
        return _token
    r = await client.post(
        f"{_base_url()}/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": os.getenv("FEDEX_CLIENT_ID", ""),
            "client_secret": os.getenv("FEDEX_CLIENT_SECRET", ""),
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    r.raise_for_status()
    j = r.json()
    _token = j["access_token"]
    _token_exp = datetime.now(UTC) + timedelta(seconds=int(j.get("expires_in", 3600)) - 60)
    return _token


def _demo(trackings: list[str]) -> dict[str, dict]:
    estados = ["IN TRANSIT", "DELIVERED", "AT CUSTOMS", "PICKED UP", "OUT FOR DELIVERY"]
    out = {}
    for t in trackings:
        rnd = random.Random(t + "fx")
        out[t] = {
            "estado": rnd.choice(estados),
            "cajas_manifiesto": None,
            "ultimo_evento": rnd.choice(["Memphis, TN", "Miami, FL", "Quito, EC"]),
            "ts": datetime.now(UTC).isoformat(),
        }
    return out


async def track(trackings: list[str]) -> dict[str, dict]:
    if DEMO_MODE:
        return _demo(trackings)
    out: dict[str, dict] = {}
    async with httpx.AsyncClient(timeout=30) as client:
        token = await _get_token(client)
        for i in range(0, len(trackings), 30):  # FedEx: max 30 guias por llamada
            lote = trackings[i:i + 30]
            try:
                r = await client.post(
                    f"{_base_url()}/track/v1/trackingnumbers",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json={"includeDetailedScans": True,
                          "trackingInfo": [{"trackingNumberInfo": {"trackingNumber": t}} for t in lote]},
                )
                r.raise_for_status()
                for res in r.json()["output"]["completeTrackResults"]:
                    t = res["trackingNumber"]
                    tr = (res.get("trackResults") or [{}])[0]
                    latest = tr.get("latestStatusDetail", {}) or {}
                    pkg = tr.get("packageDetails", {}) or {}
                    cnt = pkg.get("count") or (pkg.get("packagingDescription") or {}).get("count")
                    ends_raw = (tr.get("standardTransitTimeWindow") or {}).get("window", {}).get("ends", "")
                    entrega_est = ends_raw[:10] if ends_raw else ""
                    out[t] = {
                        "estado": latest.get("description", "SIN DATOS"),
                        "entrega_estimada": entrega_est,
                        "cajas_manifiesto": int(cnt) if cnt else None,
                        "ultimo_evento": (latest.get("scanLocation") or {}).get("city", ""),
                        "ts": datetime.now(UTC).isoformat(),
                    }
            except Exception as e:
                for t in lote:
                    out.setdefault(t, {
                        "estado": f"ERROR: {e.__class__.__name__}",
                        "cajas_manifiesto": None, "ultimo_evento": "",
                        "ts": datetime.now(UTC).isoformat(),
                    })
    return out


async def consultar_estado_real(trackings: list[str]) -> dict[str, dict]:
    """Consulta SIEMPRE la API real de FedEx (sin importar DEMO_MODE) —
    usada tras subir un manifiesto PDF para refrescar estado/fecha de
    entrega de los envios acumulados en courier_fedex_envios."""
    if not trackings:
        return {}
    client_id = os.getenv("FEDEX_CLIENT_ID", "")
    client_secret = os.getenv("FEDEX_CLIENT_SECRET", "")
    if not (client_id and client_secret):
        return {}
    base = _base_url()
    out: dict[str, dict] = {}
    async with httpx.AsyncClient(timeout=30) as client:
        token_r = await client.post(
            f"{base}/oauth/token",
            data={"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token_r.raise_for_status()
        token = token_r.json()["access_token"]

        for i in range(0, len(trackings), 30):
            lote = trackings[i:i + 30]
            try:
                r = await client.post(
                    f"{base}/track/v1/trackingnumbers",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json={"includeDetailedScans": False,
                          "trackingInfo": [{"trackingNumberInfo": {"trackingNumber": t}} for t in lote]},
                )
                r.raise_for_status()
                for res in r.json().get("output", {}).get("completeTrackResults", []):
                    t = res.get("trackingNumber", "")
                    tr = (res.get("trackResults") or [{}])[0]
                    latest = tr.get("latestStatusDetail", {}) or {}
                    fecha_entrega = next(
                        (dt.get("dateTime", "")[:10] for dt in tr.get("dateAndTimes", [])
                         if dt.get("type") == "ACTUAL_DELIVERY"), "")
                    if not fecha_entrega:
                        fecha_entrega = (
                            (tr.get("estimatedDeliveryTimeWindow") or {}).get("window", {}).get("ends", "")[:10]
                            or (tr.get("standardTransitTimeWindow") or {}).get("window", {}).get("ends", "")[:10]
                        )
                    out[t] = {
                        "estado_fedex": latest.get("description", ""),
                        "fecha_entrega_fedex": fecha_entrega,
                    }
            except Exception:
                continue
    return out
```

### services/courier_parsers.py — parseo de manifiesto UPS (.csv) y FedEx (.pdf)

`backend/app/services/courier_parsers.py`
```python
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
```

### services/courier_entregas_locales.py — entregas de agencias locales (Google Sheet + fuzzy match)

`backend/app/services/courier_entregas_locales.py`
```python
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
```

### services/courier_duoplane.py — sincronización de shipments con Duoplane

`backend/app/services/courier_duoplane.py`
```python
"""Sincronizacion con Duoplane: completa shipments de Purchase Orders
abiertas usando los trackings ya capturados en courier_ups_manifest /
courier_fedex_envios.

Clonado de REPORTEUPSFEDEX (_trackings_por_po_duoplane +
_sincronizar_duoplane), leyendo de Postgres en vez de CSVs. A diferencia
del original, "shipper_name" ahora refleja el courier real de cada
tracking (UPS o FedEx) en vez de quedar hardcodeado a "UPS".
"""

import os
import re

import httpx
from sqlalchemy import text

from app.database.connection import engine

DUOPLANE_API_KEY = os.getenv("DUOPLANE_API_KEY", "")
DUOPLANE_API_PASSWORD = os.getenv("DUOPLANE_API_PASSWORD", "")
DUOPLANE_BASE_URL = os.getenv("DUOPLANE_BASE_URL", "https://app.duoplane.com")

# Token <numero>-<numero> embebido en la referencia de UPS/FedEx que
# coincide con el "purchase_order_public_reference" de Duoplane.
DUOPLANE_PO_RE = re.compile(r"\b(\d{3,6}-\d{1,2})\b")


def _trackings_por_po_duoplane() -> dict[str, list[tuple[str, str]]]:
    """Devuelve {PO_duoplane: [(tracking, courier), ...]} buscando el token
    tanto en courier_ups_manifest.referencia como en
    courier_fedex_envios.referencia."""
    out: dict[str, list[tuple[str, str]]] = {}
    with engine.connect() as conn:
        for tracking, referencia in conn.execute(text(
            "SELECT tracking, referencia FROM courier_ups_manifest WHERE referencia IS NOT NULL"
        )):
            m = DUOPLANE_PO_RE.search(referencia or "")
            if m and tracking:
                out.setdefault(m.group(1), []).append((tracking, "UPS"))

        for tracking, referencia in conn.execute(text(
            "SELECT tracking, referencia FROM courier_fedex_envios WHERE referencia IS NOT NULL"
        )):
            m = DUOPLANE_PO_RE.search(referencia or "")
            if m and tracking:
                out.setdefault(m.group(1), []).append((tracking, "FEDEX"))
    return out


async def sincronizar() -> dict:
    if not (DUOPLANE_API_KEY and DUOPLANE_API_PASSWORD):
        return {"ok": False, "error": "DUOPLANE_API_KEY / DUOPLANE_API_PASSWORD no configurados."}

    trackings_por_po = _trackings_por_po_duoplane()
    creados, pendientes, errores = [], [], []

    async with httpx.AsyncClient(auth=(DUOPLANE_API_KEY, DUOPLANE_API_PASSWORD), timeout=30) as client:
        try:
            r = await client.get(
                f"{DUOPLANE_BASE_URL}/purchase_orders.json",
                params={"search[fulfilled]": "false", "per_page": 250},
            )
            r.raise_for_status()
        except Exception as e:
            return {"ok": False, "error": f"No se pudo consultar Duoplane: {e}"}
        pos_abiertas = r.json()

        for po in pos_abiertas:
            ref = po.get("public_reference", "")
            pares = trackings_por_po.get(ref)
            items = po.get("order_items") or []
            if not pares or not items:
                pendientes.append(ref)
                continue
            # shipper_name: courier real del primer tracking del grupo (en
            # vez de hardcodear "UPS" como el original).
            shipper = pares[0][1]
            trackings = [t for t, _ in pares]
            payload = {
                "shipment": {
                    "shipper_name": shipper,
                    "shipment_items_attributes": [
                        {"order_item_id": it["id"], "quantity": it.get("quantity_open") or it["quantity"]}
                        for it in items
                    ],
                    "shipment_trackings_attributes": [{"tracking": t} for t in trackings],
                }
            }
            try:
                resp = await client.post(
                    f"{DUOPLANE_BASE_URL}/purchase_orders/{po['id']}/shipments.json", json=payload,
                )
                if resp.status_code == 200:
                    creados.append({"po": ref, "trackings": trackings, "shipper": shipper})
                else:
                    errores.append({"po": ref, "error": resp.text[:200]})
            except Exception as e:
                errores.append({"po": ref, "error": str(e)})

    return {
        "ok": True,
        "revisadas": len(pos_abiertas),
        "creados": creados,
        "pendientes": pendientes,
        "errores": errores,
    }
```

### services/courier_reconciliation.py — motor de conciliación (equivalente a `Conciliador` del original)

**Nota de rendimiento**: la primera versión de `_persistir()` insertaba fila por fila (~200ms/round-trip a Supabase medido en pruebas), lo que tardaba ~38 minutos con los ~10,700 facturas reales — parecía que el servidor se colgaba al arrancar. Corregido con `execute_values` (bulk insert, mismo patrón que `dartis_import.py`); un refresco completo tarda ~12-16s ahora.

`backend/app/services/courier_reconciliation.py`
```python
"""Motor de conciliacion: cruza dartis_ventas (agrupado por id_pedido) vs
manifiesto UPS/FedEx vs estado en vivo vs entregas de agencias locales.

Clonado de REPORTEUPSFEDEX (clase Conciliador). Diferencia principal: no
hay un Excel Dartis propio que subir — dartis_ventas ya provee esa
informacion (ver hallazgo en el plan de la Fase 3), y el resultado se
persiste en la tabla courier_reconciliation (en vez de vivir solo en
memoria) para sobrevivir reinicios/redeploys.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text

from app.database.connection import engine
from app.services import courier_entregas_locales as entregas_locales
from app.services import courier_fedex_client as fedex_client
from app.services import courier_ups_client as ups_client

UTC = timezone.utc

_lock = asyncio.Lock()
_ultimo_error: Optional[str] = None
_ultimo_refresh: Optional[str] = None


def _normalizar_courier(courier_raw: str) -> str:
    c = (courier_raw or "").strip().upper()
    if "UPS" in c:
        return "UPS"
    if "FEDEX" in c or "FDX" in c or "FED EX" in c:
        return "FEDEX"
    return c or "OTRO"


def _obtener_base_dartis() -> list[dict]:
    """dartis_ventas agrupado por id_pedido — reemplaza al Excel Dartis
    del proyecto original (ver hallazgo del plan de la Fase 3)."""
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id_pedido AS factura, agencia_carga AS courier_raw, empresa, cliente,
                   destinatario, vendedor AS vendedor_cliente, fecha AS fecha_dartis,
                   SUM(total_piezas) AS cajas_dartis
            FROM dartis_ventas
            WHERE agencia_carga IS NOT NULL
            GROUP BY id_pedido, agencia_carga, empresa, cliente, destinatario, vendedor, fecha
        """)).mappings().all()

    base = []
    for r in rows:
        base.append({
            "factura": r["factura"],
            "courier": _normalizar_courier(r["courier_raw"]),
            "courier_raw": (r["courier_raw"] or "").strip(),
            "empresa": r["empresa"],
            "cliente": r["cliente"],
            "destinatario": r["destinatario"],
            "vendedor_cliente": r["vendedor_cliente"],
            "fecha_dartis": r["fecha_dartis"].isoformat() if r["fecha_dartis"] else None,
            "cajas_dartis": round(float(r["cajas_dartis"] or 0)),
        })
    return base


def _obtener_manifiesto_ups() -> dict[int, dict]:
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT factura, tracking, estado, fecha_manifiesto, ship_to, servicio, entrega_programada
            FROM courier_ups_manifest ORDER BY factura, id
        """)).mappings().all()
    return _agrupar_por_factura(rows)


def _obtener_manifiesto_fedex() -> dict[int, dict]:
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT factura, tracking, estado_fedex AS estado, fecha_envio AS fecha_manifiesto,
                   destinatario AS ship_to, fecha_entrega_fedex AS entrega_programada
            FROM courier_fedex_envios WHERE factura IS NOT NULL ORDER BY factura, id
        """)).mappings().all()
    return _agrupar_por_factura(rows)


def _agrupar_por_factura(rows) -> dict[int, dict]:
    out: dict[int, dict] = {}
    for r in rows:
        f = r["factura"]
        bulto = {"tracking": r["tracking"], "estado": r["estado"], "entrega_programada": r["entrega_programada"]}
        if f in out:
            out[f]["bultos"] += 1
            out[f]["trackings_extra"] += 1
            out[f]["trackings"].append(r["tracking"])
            out[f]["detalle"].append(bulto)
        else:
            out[f] = {
                "bultos": 1, "trackings_extra": 0,
                "tracking": r["tracking"], "trackings": [r["tracking"]], "detalle": [bulto],
                "estado": r["estado"], "fecha_manifiesto": r["fecha_manifiesto"],
                "ship_to": r["ship_to"], "servicio": r.get("servicio"),
                "entrega_programada": r["entrega_programada"],
            }
    return out


def _evaluar(courier: str, dartis_total, bultos_csv, manif_api) -> str:
    if courier == "UPS":
        if bultos_csv is None:
            return "SIN MANIFIESTO"
        if dartis_total != bultos_csv:
            return "DISCREPANCIA"
        if manif_api is not None and manif_api != dartis_total:
            return "DISCREPANCIA"
        return "OK"
    if manif_api is None:
        return "PENDIENTE"
    return "OK" if dartis_total == manif_api else "DISCREPANCIA"


def _armar_fila(r: dict, csv_m: Optional[dict], live: dict, con_vivo: bool) -> dict:
    bultos_csv = csv_m["bultos"] if csv_m else None
    manif_api = live.get("cajas_manifiesto")
    return {
        **r,
        "tracking": csv_m["tracking"] if csv_m else "",
        "trackings": csv_m["trackings"] if csv_m else [],
        "detalle_bultos": csv_m["detalle"] if csv_m else [],
        "trackings_extra": csv_m["trackings_extra"] if csv_m else 0,
        "bultos_csv": bultos_csv,
        "estado_csv": csv_m["estado"] if csv_m else None,
        "fecha_manifiesto": csv_m["fecha_manifiesto"] if csv_m else None,
        "servicio": csv_m["servicio"] if csv_m else None,
        "entrega_programada": csv_m["entrega_programada"] if csv_m else None,
        "cajas_manifiesto": manif_api,
        "estado_vivo": live.get("estado", "PENDIENTE") if con_vivo else "SIN COBERTURA",
        "entrega_estimada": live.get("entrega_estimada", ""),
        "ubicacion": live.get("ultimo_evento", ""),
        "conciliacion": _evaluar(r["courier"], r["cajas_dartis"], bultos_csv, manif_api),
        "diferencia": (r["cajas_dartis"] - bultos_csv) if bultos_csv is not None
                      else ((r["cajas_dartis"] - manif_api) if manif_api is not None else None),
        "fecha_entrega_real": None, "foto_url": None, "cliente_confirmado_ocr": False,
    }


def _armar_fila_otro(r: dict, match: Optional[dict]) -> dict:
    base = {
        **r,
        "tracking": "", "trackings": [], "detalle_bultos": [], "trackings_extra": 0,
        "bultos_csv": None, "fecha_manifiesto": None, "servicio": None,
        "cajas_manifiesto": None, "ubicacion": "", "fecha_entrega_real": None,
        "foto_url": None, "cliente_confirmado_ocr": False,
    }
    if not match:
        return {**base, "estado_csv": None, "entrega_programada": None,
                "estado_vivo": "PENDIENTE", "entrega_estimada": "",
                "conciliacion": "PENDIENTE", "diferencia": None}
    fecha_entrega = match["fecha_documento"].isoformat() if match["fecha_documento"] else None
    return {
        **base,
        "estado_csv": "Entregado", "entrega_programada": fecha_entrega,
        "cajas_manifiesto": r["cajas_dartis"],
        "estado_vivo": "Entregado", "entrega_estimada": fecha_entrega,
        "fecha_entrega_real": fecha_entrega,
        "foto_url": match.get("foto_url"),
        "cliente_confirmado_ocr": bool(match.get("cliente_confirmado_ocr")),
        "conciliacion": "OK", "diferencia": 0,
    }


def _resumen(cajas: list[dict]) -> dict:
    def agg(filtro=None):
        rows = [c for c in cajas if filtro is None or filtro(c)]
        return {
            "guias": len(rows),
            "vendidas": sum(c["cajas_dartis"] for c in rows),
            "manifiesto": sum(c["cajas_manifiesto"] or 0 for c in rows),
            "ok": sum(1 for c in rows if c["conciliacion"] == "OK"),
            "discrepancias": sum(1 for c in rows if c["conciliacion"] == "DISCREPANCIA"),
            "pendientes": sum(1 for c in rows if c["conciliacion"] == "PENDIENTE"),
            "sin_manifiesto": sum(1 for c in rows if c["conciliacion"] == "SIN MANIFIESTO"),
            "no_en_dartis": sum(1 for c in rows if c["conciliacion"] == "NO EN DARTIS"),
        }
    return {
        "total": agg(),
        "UPS": agg(lambda c: c["courier"] == "UPS"),
        "FEDEX": agg(lambda c: c["courier"] == "FEDEX"),
        "OTRO": agg(lambda c: c["courier"] not in ("UPS", "FEDEX")),
    }


def obtener_snapshot() -> dict:
    """Lee el snapshot persistido (courier_reconciliation) — no dispara
    ninguna llamada en vivo, solo lo que dejo el ultimo refrescar()."""
    with engine.connect() as conn:
        cajas = [dict(r) for r in conn.execute(text(
            "SELECT * FROM courier_reconciliation ORDER BY (conciliacion != 'DISCREPANCIA'), factura"
        )).mappings().all()]
    return {
        "cajas": cajas,
        "resumen": _resumen(cajas) if cajas else {},
        "actualizado": _ultimo_refresh,
        "error": _ultimo_error,
    }


def obtener_discrepancias() -> list[dict]:
    with engine.connect() as conn:
        return [dict(r) for r in conn.execute(text("""
            SELECT * FROM courier_reconciliation
            WHERE conciliacion IN ('DISCREPANCIA', 'SIN MANIFIESTO', 'NO EN DARTIS')
            ORDER BY factura
        """)).mappings().all()]


async def refrescar() -> dict:
    global _ultimo_error, _ultimo_refresh
    async with _lock:
        error = None
        try:
            base = _obtener_base_dartis()
        except Exception as e:
            base, error = [], str(e)

        try:
            manif_ups = _obtener_manifiesto_ups()
        except Exception as e:
            manif_ups, error = {}, (error + " | " if error else "") + f"Manifiesto UPS: {e}"

        try:
            manif_fdx = _obtener_manifiesto_fedex()
        except Exception as e:
            manif_fdx, error = {}, (error + " | " if error else "") + f"Manifiesto FedEx: {e}"

        facturas_dartis = {r["factura"] for r in base}
        extras_ups = [f for f in manif_ups if f not in facturas_dartis]
        extras_fdx = [f for f in manif_fdx if f not in facturas_dartis and f not in manif_ups]

        guias_ups = [manif_ups[r["factura"]]["tracking"] for r in base
                     if r["courier"] == "UPS" and r["factura"] in manif_ups]
        guias_ups += [manif_ups[f]["tracking"] for f in extras_ups]
        guias_fdx = [manif_fdx[r["factura"]]["tracking"] for r in base
                     if r["courier"] == "FEDEX" and r["factura"] in manif_fdx]
        guias_fdx += [manif_fdx[f]["tracking"] for f in extras_fdx]

        try:
            vivo_ups, vivo_fdx, entregas = await asyncio.gather(
                ups_client.track(guias_ups), fedex_client.track(guias_fdx), entregas_locales.fetch()
            )
        except Exception as e:
            vivo_ups, vivo_fdx, entregas = {}, {}, []
            error = (error + " | " if error else "") + f"Track API: {e}"
        vivo = {**vivo_ups, **vivo_fdx}
        entregas_por_agencia = entregas_locales.indexar_entregas_por_agencia(entregas)

        cajas = []
        for r in base:
            if r["courier"] not in ("UPS", "FEDEX"):
                match = entregas_locales.emparejar_entrega_local(r, entregas_por_agencia)
                cajas.append(_armar_fila_otro(r, match))
                continue
            m = manif_fdx.get(r["factura"]) if r["courier"] == "FEDEX" else manif_ups.get(r["factura"])
            t = m["tracking"] if m else ""
            cajas.append(_armar_fila(r, m, vivo.get(t, {}), t in vivo))

        for f in extras_ups:
            m = manif_ups[f]
            t = m["tracking"]
            r = {"factura": f, "courier": "UPS", "courier_raw": "UPS", "empresa": "",
                 "cliente": m.get("ship_to", ""), "destinatario": m.get("ship_to", ""),
                 "vendedor_cliente": None, "cajas_dartis": 0, "fecha_dartis": None}
            fila = _armar_fila(r, m, vivo.get(t, {}), t in vivo)
            fila["conciliacion"] = "NO EN DARTIS"
            cajas.append(fila)

        for f in extras_fdx:
            m = manif_fdx[f]
            t = m["tracking"]
            r = {"factura": f, "courier": "FEDEX", "courier_raw": "FEDEX", "empresa": "",
                 "cliente": m.get("ship_to", ""), "destinatario": m.get("ship_to", ""),
                 "vendedor_cliente": None, "cajas_dartis": 0, "fecha_dartis": None}
            fila = _armar_fila(r, m, vivo.get(t, {}), t in vivo)
            fila["conciliacion"] = "NO EN DARTIS"
            cajas.append(fila)

        _persistir(cajas)
        _ultimo_error = error
        _ultimo_refresh = datetime.now(UTC).isoformat()

        return {
            "resumen": _resumen(cajas),
            "actualizado": _ultimo_refresh,
            "error": _ultimo_error,
            "total_facturas": len(cajas),
        }


_PERSISTIR_COLUMNAS = [
    "factura", "courier", "courier_raw", "empresa", "cliente", "destinatario", "vendedor_cliente",
    "cajas_dartis", "fecha_dartis", "tracking", "trackings", "detalle_bultos", "trackings_extra",
    "bultos_csv", "estado_csv", "fecha_manifiesto", "servicio", "entrega_programada",
    "cajas_manifiesto", "estado_vivo", "entrega_estimada", "ubicacion", "conciliacion", "diferencia",
    "fecha_entrega_real", "foto_url", "cliente_confirmado_ocr",
]


def _persistir(cajas: list[dict]) -> None:
    """Reemplaza el snapshot completo (igual semantica que el original:
    siempre refleja el ultimo refresco, no un merge incremental).

    Insercion masiva via execute_values (mismo patron que dartis_import.py):
    con miles de facturas, insertar fila por fila tarda minutos por la
    latencia de red hacia Supabase (~200ms/round-trip medido); en batch es
    una sola ida y vuelta por lote."""
    from psycopg2.extras import execute_values

    tuples = [
        (
            c["factura"], c["courier"], c["courier_raw"], c["empresa"], c["cliente"], c["destinatario"],
            c["vendedor_cliente"], c["cajas_dartis"], c["fecha_dartis"], c["tracking"],
            json.dumps(c["trackings"]), json.dumps(c["detalle_bultos"]), c["trackings_extra"],
            c["bultos_csv"], c["estado_csv"], c["fecha_manifiesto"], c["servicio"], c["entrega_programada"],
            c["cajas_manifiesto"], c["estado_vivo"], c["entrega_estimada"], c["ubicacion"],
            c["conciliacion"], c["diferencia"], c["fecha_entrega_real"], c["foto_url"],
            c["cliente_confirmado_ocr"],
        )
        for c in cajas
    ]

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE courier_reconciliation"))
        if not tuples:
            return
        raw = conn.connection.cursor()
        execute_values(raw, f"""
            INSERT INTO courier_reconciliation ({", ".join(_PERSISTIR_COLUMNAS)}) VALUES %s
        """, tuples, page_size=1000)
```

### api/torre_control.py

`backend/app/api/torre_control.py`
```python
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
```

---

## 12. Backend — módulo Auditoría de Etiquetas

Clon de **Auditoria_LEsp**. Los despachos de clientes especiales se generan directo desde `dartis_ventas` + `customers.es_cliente_especial` (agrupado por `guia_madre`+`guia_hija`+`tipo_caja`) — verificado fila por fila contra los Excel `Ventas Auditoria Etiquetas...xlsx` que se subían a mano en el original, así que ya no hace falta subirlos.

El bot de Telegram del auditor de poscosecha se reutiliza tal cual (mismo token — el auditor no nota el cambio), con su state machine portado completo (`/lista`, `/resumen`, `/cancelar`, formulario paso a paso) a `telegram_bot.py`. El estado de conversación vive en Postgres (`telegram_conversation_state`) en vez del `CacheService` de Apps Script (TTL de 6h en el original), para sobrevivir un redeploy de Render a media auditoría.

Las fotos de respaldo siguen en Google Drive (decisión del usuario), vía una cuenta de servicio y la Drive API v3 — si la subida falla, la auditoría se guarda igual sin `foto_url` en vez de perderse.

El relay de Supabase que necesitaba Apps Script (porque `script.google.com` siempre responde con un 302 y Telegram no sigue redirects) desaparece por completo: FastAPI puede recibir el webhook de Telegram directo.

> ⚠️ El webhook real de Telegram **no se ha registrado todavía** — Apps Script del proyecto original sigue operando sin cambios. El corte a producción (`setWebhook` apuntando a BLIS) requiere confirmación explícita del usuario, ver plan de Fase 4.

### services/special_dispatches.py — genera los despachos desde dartis_ventas

`backend/app/services/special_dispatches.py`
```python
"""Genera los "despachos" a auditar (clientes especiales) directo desde
dartis_ventas — reemplaza el paso manual de "descargar Excel de ventas y
subirlo a la pagina" del proyecto original Auditoria_LEsp.

Verificado en la sesion de planificacion: los archivos "Ventas Auditoria
Etiquetas...xlsx" que se subian a mano tienen exactamente las columnas
empresa/cliente/destinatario/fecha/guia_madre/guia_hija/postcosecha/
tipo_caja/total, y coinciden fila por fila con dartis_ventas agrupada por
guia_madre+guia_hija+tipo_caja (total = SUM(total_piezas)).
"""

from datetime import date as date_type
from typing import Optional

from sqlalchemy import text

from app.database.connection import engine


def generar_despachos_del_dia(fecha: Optional[date_type] = None) -> dict:
    """Idempotente: se puede llamar en cada /lista del bot sin duplicar
    filas (UNIQUE en fecha+guia_madre+guia_hija+tipo_caja) ni pisar
    despachos que ya estan en curso o auditados."""
    with engine.begin() as conn:
        filtro_fecha = "dv.fecha = :fecha" if fecha else "dv.fecha = CURRENT_DATE"
        params = {"fecha": fecha} if fecha else {}

        filas = conn.execute(text(f"""
            SELECT dv.fecha, dv.postcosecha, c.id AS customer_id, dv.cliente, dv.destinatario,
                   dv.guia_madre, dv.guia_hija, dv.tipo_caja, c.customer_name AS etiqueta,
                   SUM(dv.total_piezas) AS cajas
            FROM dartis_ventas dv
            JOIN customers c ON LOWER(TRIM(c.dartis_name)) = LOWER(TRIM(dv.cliente))
            WHERE c.es_cliente_especial = true AND {filtro_fecha}
            GROUP BY dv.fecha, dv.postcosecha, c.id, dv.cliente, dv.destinatario,
                     dv.guia_madre, dv.guia_hija, dv.tipo_caja, c.customer_name
        """), params).mappings().all()

        insertados = 0
        for f in filas:
            r = conn.execute(text("""
                INSERT INTO special_dispatches
                    (fecha, postcosecha, customer_id, cliente, destinatario, guia_madre, guia_hija,
                     cajas, tipo_caja, etiqueta)
                VALUES (:fecha, :postcosecha, :customer_id, :cliente, :destinatario, :guia_madre, :guia_hija,
                        :cajas, :tipo_caja, :etiqueta)
                ON CONFLICT (fecha, guia_madre, guia_hija, tipo_caja) DO NOTHING
            """), dict(f))
            insertados += r.rowcount

    return {"encontrados": len(filas), "insertados": insertados}


def despachos_pendientes(poscosecha: Optional[str] = None) -> list[dict]:
    with engine.connect() as conn:
        filtro = "AND postcosecha = :pos" if poscosecha else ""
        params = {"pos": poscosecha} if poscosecha else {}
        rows = conn.execute(text(f"""
            SELECT * FROM special_dispatches
            WHERE estado = 'PENDIENTE' AND fecha >= CURRENT_DATE {filtro}
            ORDER BY postcosecha, cliente
        """), params).mappings().all()
    return [dict(r) for r in rows]


def poscosechas_pendientes() -> list[str]:
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT DISTINCT postcosecha FROM special_dispatches
            WHERE estado = 'PENDIENTE' AND fecha >= CURRENT_DATE
            ORDER BY postcosecha
        """)).all()
    return [r[0] for r in rows if r[0]]
```

### services/google_drive.py — sube fotos a Drive vía cuenta de servicio

`backend/app/services/google_drive.py`
```python
"""Sube las fotos de respaldo de las auditorias a Google Drive, via una
cuenta de servicio (Drive API v3) — reemplaza DriveApp de Apps Script.

Requiere GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON (el JSON de la cuenta de
servicio, como string) y GOOGLE_DRIVE_FOLDER_ID (carpeta raiz
"Auditoria Etiquetas - Fotos" u otra, compartida con el email de la
cuenta de servicio como Editor). Si no estan configuradas, sube_foto()
devuelve None en vez de lanzar excepcion — la auditoria se guarda igual,
solo sin foto_url (mismo espiritu de resiliencia que los demas conectores).
"""

import json
import os
from datetime import datetime, timezone
from typing import Optional

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]
UTC = timezone.utc

_credentials = None


def _get_credentials():
    global _credentials
    if _credentials is not None:
        return _credentials
    raw = os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON", "")
    if not raw:
        return None
    from google.oauth2 import service_account

    info = json.loads(raw)
    _credentials = service_account.Credentials.from_service_account_info(info, scopes=DRIVE_SCOPES)
    return _credentials


def _access_token() -> Optional[str]:
    creds = _get_credentials()
    if creds is None:
        return None
    from google.auth.transport.requests import Request

    if not creds.valid:
        creds.refresh(Request())
    return creds.token


def _buscar_o_crear_carpeta(token: str, nombre: str, parent_id: str) -> Optional[str]:
    import requests

    q = f"'{parent_id}' in parents and name='{nombre}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    r = requests.get(
        "https://www.googleapis.com/drive/v3/files",
        params={"q": q, "fields": "files(id)"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    r.raise_for_status()
    encontrados = r.json().get("files", [])
    if encontrados:
        return encontrados[0]["id"]

    r = requests.post(
        "https://www.googleapis.com/drive/v3/files",
        json={"name": nombre, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]},
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["id"]


def subir_foto(contenido: bytes, nombre_archivo: str, subcarpeta: Optional[str] = None) -> Optional[str]:
    """Sube una foto a Drive y devuelve su URL publica (o None si Drive
    no esta configurado o falla la subida)."""
    import requests

    token = _access_token()
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
    if not token or not folder_id:
        return None

    try:
        subcarpeta = subcarpeta or datetime.now(UTC).strftime("%Y-%m-%d")
        carpeta_id = _buscar_o_crear_carpeta(token, subcarpeta, folder_id)

        metadata = {"name": nombre_archivo, "parents": [carpeta_id]}
        r = requests.post(
            "https://www.googleapis.com/upload/drive/v3/files",
            params={"uploadType": "multipart", "fields": "id"},
            headers={"Authorization": f"Bearer {token}"},
            files={
                "metadata": (None, json.dumps(metadata), "application/json"),
                "file": (nombre_archivo, contenido, "image/jpeg"),
            },
            timeout=30,
        )
        r.raise_for_status()
        file_id = r.json()["id"]

        requests.post(
            f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions",
            json={"role": "reader", "type": "anyone"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        return f"https://drive.google.com/file/d/{file_id}/view"
    except Exception:
        return None
```

### services/telegram_bot.py — state machine del bot (port de Code.gs)

`backend/app/services/telegram_bot.py`
```python
"""Bot de Telegram para el auditor de poscosecha — port del state machine
de Code.gs (Auditoria_LEsp). Mismo flujo: /lista -> elegir poscosecha (si
hay mas de una) -> elegir despacho -> auditor -> cajas -> piezas -> tipo
de caja OK? -> especie OK? -> etiqueta OK? -> observaciones -> foto ->
se guarda en special_dispatch_audits y se marca el despacho AUDITADO.

El estado de la conversacion vive en telegram_conversation_state
(Postgres) en vez de CacheService de Apps Script, para sobrevivir un
redeploy de Render a media auditoria.
"""

import json
import os
from datetime import datetime, timezone

import httpx
from sqlalchemy import text

from app.database.connection import engine
from app.services import google_drive, special_dispatches

UTC = timezone.utc


def _token() -> str:
    return os.getenv("TELEGRAM_BOT_TOKEN", "")


def _api_url(metodo: str) -> str:
    return f"https://api.telegram.org/bot{_token()}/{metodo}"


async def _enviar(chat_id: str, texto: str) -> None:
    async with httpx.AsyncClient(timeout=15) as client:
        await client.post(_api_url("sendMessage"), json={
            "chat_id": chat_id, "text": texto, "parse_mode": "HTML",
            "reply_markup": {"remove_keyboard": True},
        })


async def _enviar_botones(chat_id: str, texto: str, filas: list) -> None:
    """filas: lista de filas, cada fila lista de {"texto":..., "datos":...}"""
    teclado = [[{"text": b["texto"], "callback_data": b["datos"]} for b in fila] for fila in filas]
    async with httpx.AsyncClient(timeout=15) as client:
        await client.post(_api_url("sendMessage"), json={
            "chat_id": chat_id, "text": texto, "parse_mode": "HTML",
            "reply_markup": {"inline_keyboard": teclado},
        })


async def _responder_callback(callback_id: str) -> None:
    async with httpx.AsyncClient(timeout=15) as client:
        await client.post(_api_url("answerCallbackQuery"), json={"callback_query_id": callback_id})


# ---------- Estado de conversacion (Postgres) ----------

def _obtener_estado(chat_id: str) -> dict:
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT paso, estado FROM telegram_conversation_state WHERE chat_id = :c"
        ), {"c": chat_id}).mappings().first()
    if not row:
        return {"paso": None}
    data = dict(row["estado"] or {})
    data["paso"] = row["paso"]
    return data


def _guardar_estado(chat_id: str, estado: dict) -> None:
    paso = estado.get("paso")
    resto = {k: v for k, v in estado.items() if k != "paso"}
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO telegram_conversation_state (chat_id, paso, estado, updated_at)
            VALUES (:chat_id, :paso, :estado, now())
            ON CONFLICT (chat_id) DO UPDATE SET paso = :paso, estado = :estado, updated_at = now()
        """), {"chat_id": chat_id, "paso": paso, "estado": json.dumps(resto, default=str)})


def _borrar_estado(chat_id: str) -> None:
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM telegram_conversation_state WHERE chat_id = :c"), {"c": chat_id})


# ---------- Flujo principal ----------

async def procesar_update(update: dict) -> None:
    if "callback_query" in update:
        await _manejar_callback(update["callback_query"])
        return
    msg = update.get("message")
    if not msg:
        return
    chat_id = str(msg["chat"]["id"])
    texto = (msg.get("text") or "").strip()
    estado = _obtener_estado(chat_id)

    if texto in ("/start", "/lista"):
        await _enviar_lista_pendientes(chat_id)
        return
    if texto == "/cancelar":
        _borrar_estado(chat_id)
        await _enviar(chat_id, "❌ Auditoria cancelada. Escribe /lista para empezar de nuevo.")
        return
    if texto == "/resumen":
        await _enviar_resumen(chat_id)
        return

    paso = estado.get("paso")

    if paso == "eligiendo_poscosecha":
        poscosechas = estado.get("poscosechas", [])
        elegida = next((p for p in poscosechas if p.upper() == texto.upper()), None)
        if not elegida:
            await _enviar(chat_id, "⚠️ Elige una de las poscosechas del teclado, o /cancelar.")
            return
        await _mostrar_lista_por_poscosecha(chat_id, elegida)
        return

    if paso == "eligiendo":
        pendientes = estado.get("pendientes", [])
        try:
            n = int(texto)
        except ValueError:
            n = None
        if not n or n < 1 or n > len(pendientes):
            await _enviar(chat_id, f"⚠️ Responde con el numero del despacho (1-{len(pendientes)}) o /cancelar.")
            return
        despacho = pendientes[n - 1]
        estado = {"paso": "auditor", "despacho": despacho}
        _guardar_estado(chat_id, estado)
        d = despacho
        texto_msg = (
            f"\U0001F4E6 <b>{d['cliente']}</b>\n\U0001F3ED Poscosecha: {d['postcosecha']}\n"
            f"\U0001F4C4 Guia hija: {d['guia_hija']}\n\U0001F4E6 Cajas segun venta: {d['cajas']}"
        )
        if d.get("tipo_caja"):
            texto_msg += f"\n\U0001F4E6 Tipo de caja segun venta: <b>{d['tipo_caja']}</b>"
        texto_msg += f"\n\U0001F3F7️ Etiqueta: {d.get('etiqueta') or ''}"
        if d.get("instrucciones"):
            texto_msg += f"\n\U0001F4CB Instrucciones: {d['instrucciones']}"
        texto_msg += "\n\n\U0001F464 <b>Nombre del auditor?</b>"
        await _enviar(chat_id, texto_msg)
        return

    if paso == "auditor":
        estado["auditor"] = texto
        estado["paso"] = "cajas"
        _guardar_estado(chat_id, estado)
        await _enviar(chat_id, f"\U0001F4E6 Cuantas <b>cajas</b> se estan despachando? (segun venta: {estado['despacho']['cajas']})")
        return

    if paso == "cajas":
        try:
            cajas = float(texto.replace(",", "."))
        except ValueError:
            await _enviar(chat_id, "⚠️ Escribe solo el numero de cajas.")
            return
        estado["cajas"] = cajas
        estado["paso"] = "piezas"
        _guardar_estado(chat_id, estado)
        await _enviar(chat_id, "\U0001F339 Cuantas <b>piezas</b> (tallos) se estan despachando?")
        return

    if paso == "piezas":
        try:
            piezas = float(texto.replace(",", "."))
        except ValueError:
            await _enviar(chat_id, "⚠️ Escribe solo el numero de piezas.")
            return
        estado["piezas"] = piezas
        estado["paso"] = "tipoCaja"
        _guardar_estado(chat_id, estado)
        tipo_esperado = estado["despacho"].get("tipo_caja")
        pregunta = "\U0001F4E6 El <b>tipo de caja</b> revisado esta correcto"
        pregunta += f" (segun venta: <b>{tipo_esperado}</b>)?" if tipo_esperado else " (HB, QB, EB)?"
        await _enviar_botones(chat_id, pregunta, [[{"texto": "✅ Si", "datos": "SI"}, {"texto": "❌ No", "datos": "NO"}]])
        return

    if paso == "observaciones":
        estado["observaciones"] = "" if texto == "-" else texto
        estado["paso"] = "foto"
        _guardar_estado(chat_id, estado)
        await _enviar(chat_id, "\U0001F4F8 Envia ahora la <b>foto de respaldo</b> del despacho de las cajas.")
        return

    if paso == "foto":
        fotos = msg.get("photo")
        if not fotos:
            await _enviar(chat_id, "⚠️ Necesito una foto. Envia la imagen del despacho.")
            return
        url_foto = await _guardar_foto(fotos, estado)
        await _registrar_auditoria(chat_id, estado, url_foto)
        _borrar_estado(chat_id)
        await _enviar(
            chat_id,
            f"✅ <b>Auditoria registrada</b>\n\U0001F4E6 {estado['despacho']['cliente']}\n"
            f"\U0001F4E6 Cajas: {estado['cajas']}\n\U0001F339 Piezas: {estado['piezas']}\n"
            f"\U0001F4F7 Foto {'guardada' if url_foto else 'NO se pudo guardar (revisar configuracion de Drive)'}.\n\n"
            "Escribe /lista para auditar otro despacho.",
        )
        return

    await _enviar(
        chat_id,
        "\U0001F44B Hola, soy el bot de auditoria de etiquetas Bellaflor.\n\n"
        "/lista - ver despachos pendientes de hoy\n/resumen - avance del dia\n/cancelar - cancelar auditoria en curso",
    )


async def _manejar_callback(cb: dict) -> None:
    chat_id = str(cb["message"]["chat"]["id"])
    texto = cb.get("data", "")
    await _responder_callback(cb["id"])
    estado = _obtener_estado(chat_id)
    paso = estado.get("paso")

    if paso == "eligiendo_poscosecha":
        poscosechas = estado.get("poscosechas", [])
        if texto not in poscosechas:
            await _enviar(chat_id, "⚠️ Esa opcion ya no es valida. Escribe /lista de nuevo.")
            return
        await _mostrar_lista_por_poscosecha(chat_id, texto)
        return

    if paso == "tipoCaja" and texto in ("SI", "NO"):
        estado["tipoCajaOK"] = texto == "SI"
        estado["paso"] = "especie"
        _guardar_estado(chat_id, estado)
        await _enviar_botones(chat_id, "\U0001F9EC La <b>especie</b> esta igual en la etiqueta especial y en la etiqueta de caja?",
                               [[{"texto": "✅ Si", "datos": "SI"}, {"texto": "❌ No", "datos": "NO"}]])
        return

    if paso == "especie" and texto in ("SI", "NO"):
        estado["especieOK"] = texto == "SI"
        estado["paso"] = "etiqueta"
        _guardar_estado(chat_id, estado)
        await _enviar_botones(chat_id, "\U0001F3F7️ La <b>etiqueta especial</b> esta correctamente aplicada?",
                               [[{"texto": "✅ Si", "datos": "SI"}, {"texto": "❌ No", "datos": "NO"}]])
        return

    if paso == "etiqueta" and texto in ("SI", "NO"):
        estado["etiquetaOK"] = texto == "SI"
        estado["paso"] = "observaciones"
        _guardar_estado(chat_id, estado)
        await _enviar(chat_id, "\U0001F4DD Escribe las <b>observaciones</b> (o envia \"-\" si no hay).")
        return


# ---------- Listas / resumen ----------

async def _enviar_lista_pendientes(chat_id: str) -> None:
    special_dispatches.generar_despachos_del_dia()
    pendientes = special_dispatches.despachos_pendientes()
    if not pendientes:
        await _enviar(chat_id, "\U0001F389 No hay despachos pendientes de auditoria hoy.")
        return

    poscosechas = []
    for d in pendientes:
        if d["postcosecha"] not in poscosechas:
            poscosechas.append(d["postcosecha"])

    if len(poscosechas) == 1:
        await _mostrar_lista_por_poscosecha(chat_id, poscosechas[0], pendientes)
        return

    _guardar_estado(chat_id, {"paso": "eligiendo_poscosecha", "poscosechas": poscosechas})
    botones = [[{"texto": p, "datos": p}] for p in poscosechas]
    await _enviar_botones(chat_id, "\U0001F3ED <b>A que poscosecha perteneces?</b>", botones)


async def _mostrar_lista_por_poscosecha(chat_id: str, poscosecha: str, pendientes: list = None) -> None:
    if pendientes is None:
        pendientes = special_dispatches.despachos_pendientes()
    filtrados = [d for d in pendientes if d["postcosecha"] == poscosecha]
    if not filtrados:
        await _enviar(chat_id, f"\U0001F389 No hay despachos pendientes para {poscosecha}.")
        return

    texto = f"\U0001F4CB <b>Despachos pendientes - {poscosecha}</b>\n\n"
    for i, d in enumerate(filtrados, start=1):
        texto += f"{i}. <b>{d['cliente']}</b> - {d['cajas']} cajas"
        if d.get("tipo_caja"):
            texto += f" ({d['tipo_caja']})"
        texto += f" - Guia {d['guia_hija']}\n"
    texto += "\n➡️ Responde con el <b>numero</b> del despacho que vas a auditar."
    _guardar_estado(chat_id, {"paso": "eligiendo", "pendientes": filtrados})
    await _enviar(chat_id, texto)


async def _enviar_resumen(chat_id: str) -> None:
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT postcosecha, estado FROM special_dispatches WHERE fecha = CURRENT_DATE
        """)).all()
    if not rows:
        await _enviar(chat_id, "Aun no hay datos de hoy.")
        return
    total = len(rows)
    auditados = sum(1 for _, e in rows if e == "AUDITADO")
    por_pos: dict[str, dict[str, int]] = {}
    for pos, e in rows:
        por_pos.setdefault(pos, {"t": 0, "a": 0})
        por_pos[pos]["t"] += 1
        if e == "AUDITADO":
            por_pos[pos]["a"] += 1
    texto = f"\U0001F4CA <b>Resumen de hoy</b>\n\nAuditados: {auditados} / {total}\n\n"
    for pos in sorted(por_pos):
        texto += f"\U0001F3ED {pos}: {por_pos[pos]['a']}/{por_pos[pos]['t']}\n"
    await _enviar(chat_id, texto)


# ---------- Foto + registro final ----------

async def _guardar_foto(fotos: list, estado: dict) -> str:
    file_id = fotos[-1]["file_id"]  # mayor resolucion
    async with httpx.AsyncClient(timeout=20) as client:
        info = (await client.get(_api_url("getFile"), params={"file_id": file_id})).json()
        file_path = info["result"]["file_path"]
        contenido = (await client.get(f"https://api.telegram.org/file/bot{_token()}/{file_path}")).content

    d = estado["despacho"]
    hoy = datetime.now(UTC).strftime("%Y-%m-%d")
    cliente_slug = "".join(c if c.isalnum() else "_" for c in d["cliente"])
    nombre = f"{hoy}_{d['postcosecha']}_{cliente_slug}_{d['guia_hija']}.jpg"
    return google_drive.subir_foto(contenido, nombre, subcarpeta=hoy)


async def _registrar_auditoria(chat_id: str, estado: dict, url_foto: str) -> None:
    d = estado["despacho"]
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO special_dispatch_audits
                (dispatch_id, auditor, cajas_despachadas, piezas_despachadas,
                 tipo_caja_ok, especie_ok, etiqueta_ok, observaciones, foto_url, chat_id)
            VALUES (:dispatch_id, :auditor, :cajas, :piezas, :tipo_caja_ok, :especie_ok, :etiqueta_ok,
                    :observaciones, :foto_url, :chat_id)
        """), {
            "dispatch_id": d["id"], "auditor": estado.get("auditor"),
            "cajas": estado.get("cajas"), "piezas": estado.get("piezas"),
            "tipo_caja_ok": estado.get("tipoCajaOK"), "especie_ok": estado.get("especieOK"),
            "etiqueta_ok": estado.get("etiquetaOK"), "observaciones": estado.get("observaciones"),
            "foto_url": url_foto, "chat_id": chat_id,
        })
        conn.execute(text("""
            UPDATE special_dispatches
            SET estado = 'AUDITADO', auditado_por = :auditor, fecha_auditoria = now()
            WHERE id = :id
        """), {"auditor": estado.get("auditor"), "id": d["id"]})
```

### api/auditoria_etiquetas.py

`backend/app/api/auditoria_etiquetas.py`
```python
"""API del modulo Auditoria de Etiquetas Especiales: clon de
Auditoria_LEsp. La carga de datos ocurre via el bot de Telegram (igual
que el original); este router expone el webhook y un dashboard de
solo lectura para supervision.
"""

import os
from datetime import date as date_type
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy import text

from app.database.connection import engine
from app.services import special_dispatches
from app.services import telegram_bot

router = APIRouter(prefix="/auditoria-etiquetas", tags=["Auditoria de Etiquetas"])


@router.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(default=None),
):
    secreto = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    if secreto and x_telegram_bot_api_secret_token != secreto:
        raise HTTPException(status_code=401, detail="secret_token invalido")

    update = await request.json()
    try:
        await telegram_bot.procesar_update(update)
    except Exception:
        pass  # Telegram reintenta si no responde 200; nunca dejar que un error rompa el webhook
    return {"ok": True}


@router.post("/despachos/generar")
def generar_despachos(fecha: Optional[date_type] = None):
    return special_dispatches.generar_despachos_del_dia(fecha)


@router.get("/despachos")
def listar_despachos(fecha: Optional[date_type] = None):
    with engine.connect() as conn:
        if fecha:
            rows = conn.execute(text(
                "SELECT * FROM special_dispatches WHERE fecha = :f ORDER BY postcosecha, cliente"
            ), {"f": fecha}).mappings().all()
        else:
            rows = conn.execute(text(
                "SELECT * FROM special_dispatches WHERE fecha = CURRENT_DATE ORDER BY postcosecha, cliente"
            )).mappings().all()
    return rows


@router.get("/auditorias")
def listar_auditorias(fecha: Optional[date_type] = None):
    with engine.connect() as conn:
        if fecha:
            rows = conn.execute(text("""
                SELECT a.*, d.cliente, d.postcosecha, d.guia_madre, d.guia_hija, d.tipo_caja
                FROM special_dispatch_audits a
                JOIN special_dispatches d ON d.id = a.dispatch_id
                WHERE d.fecha = :f ORDER BY a.fecha_hora DESC
            """), {"f": fecha}).mappings().all()
        else:
            rows = conn.execute(text("""
                SELECT a.*, d.cliente, d.postcosecha, d.guia_madre, d.guia_hija, d.tipo_caja
                FROM special_dispatch_audits a
                JOIN special_dispatches d ON d.id = a.dispatch_id
                WHERE d.fecha = CURRENT_DATE ORDER BY a.fecha_hora DESC
            """)).mappings().all()
    return rows
```

---

## 13. Schemas Pydantic

Un archivo por módulo en `backend/app/schemas/`: `species.py`, `varieties.py`, `product_sizes.py`, `box_types.py`, `airports.py`, `customers.py`, `airlines.py`, `airline_tariffs.py`, `cargo_agencies.py`, `farms.py`, `agrocalidad.py` (Fase 1), `inventario_lag.py` (Fase 2). Torre de Control y Auditoría de Etiquetas (Fases 3-4) no usan Pydantic — siguen el mismo patrón de SQL crudo vía `text()` que `cotizacion.py`/`dartis_import.py`, devolviendo `RowMapping` directo.

Ya mostrados completos en las secciones 9 y 10 (`agrocalidad.py`, `inventario_lag.py`). Ejemplo adicional del patrón CRUD estándar:

`backend/app/schemas/species.py`
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

---

## 14. Frontend — núcleo

### js/layout.js — carga el sidebar y resalta la página activa

`frontend/js/layout.js`
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
        // if inside a nav-group (<details>), open it
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

### js/api.js — wrapper fetch (apiGet/apiPost/apiPut/apiDelete)

`frontend/js/api.js`
```javascript
const API_BASE = "/api";

async function handleResponse(response) {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const data = await response.json();
      if (data && data.detail) {
        detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      }
    } catch (err) {
      // response body was not JSON, keep statusText
    }
    throw new Error(detail);
  }
  if (response.status === 204) return null;
  return response.json();
}

export async function apiGet(path) {
  const response = await fetch(`${API_BASE}${path}`);
  return handleResponse(response);
}

export async function apiPost(path, body) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return handleResponse(response);
}

export async function apiPut(path, body) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return handleResponse(response);
}

export async function apiDelete(path) {
  const response = await fetch(`${API_BASE}${path}`, { method: "DELETE" });
  return handleResponse(response);
}
```

### components/sidebar.html

Un `<a>` por módulo, con `data-page` para que `layout.js` marque el activo. Los 4 módulos nuevos están como ítems de primer nivel (no dentro de "Configuración"), porque son operativos diarios.

`frontend/components/sidebar.html`
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
  <a href="/pages/agrocalidad.html" data-page="agrocalidad"><i class="ph ph-leaf"></i>Agrocalidad</a>
  <a href="/pages/inventario-lag.html" data-page="inventario-lag"><i class="ph ph-warehouse"></i>Inventario LAG</a>
  <a href="/pages/torre-control.html" data-page="torre-control"><i class="ph ph-radar"></i>Torre de Control</a>
  <a href="/pages/auditoria-etiquetas.html" data-page="auditoria-etiquetas"><i class="ph ph-clipboard-text"></i>Auditoría de Etiquetas</a>

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

## 15. Frontend — páginas de catálogo y operación

### pages/dashboard.html

`frontend/pages/dashboard.html`
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

### pages/ingresos-locales.html + .js

`frontend/pages/ingresos-locales.html`
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

`frontend/pages/ingresos-locales.js`
```javascript
/* ═══════════════════════════════════════════════════════════════════
   INGRESOS LOCALES — Dashboard de entregas (datos desde GAS)
   ═══════════════════════════════════════════════════════════════════ */

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

/* ─── Render principal ─────────────────────────────────────────── */
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

    <!-- Tarjetas resumen -->
    <div class="il-resumen" id="il-resumen"></div>

    <!-- Filtros -->
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

    <!-- Tabla -->
    <div class="card" style="padding:0; overflow:hidden">
      <div class="il-tabla-header">
        <h2>Registros de entregas</h2>
        <span class="badge badge-gray" id="il-contador">—</span>
      </div>
      <div style="overflow-x:auto">
        <div id="il-tabla-body"></div>
      </div>
    </div>

    <!-- Modal compartir -->
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

  // Actualizar hora
  document.getElementById("il-updated").textContent =
    new Date().toLocaleTimeString("es-EC", { hour: "2-digit", minute: "2-digit" });

  poblarResumen();
  poblarFiltroEmpresas();
  aplicarFiltros();

  // Listeners
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

  // Abrir registro compartido si viene en URL
  const fila = new URLSearchParams(window.location.search).get("fila");
  if (fila) {
    const reg = todosLosDatos.find(r => String(r._fila) === fila);
    if (reg) abrirModal(reg);
  }
}

/* ─── Resumen ──────────────────────────────────────────────────── */
function poblarResumen() {
  const hoyStr = new Date().toLocaleDateString("es-EC", {
    day: "2-digit", month: "2-digit", year: "numeric"
  }).replace(/\//g, "/");

  const mesNum = new Date().getMonth();
  const hoy    = todosLosDatos.filter(r => String(r["Fecha Documento"]).trim() === hoyStr);
  const mes    = todosLosDatos.filter(r => {
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

/* ─── Filtros ──────────────────────────────────────────────────── */
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
    const campos = [
      r["N° Guía / Ingreso"], r["Finca / Exportador"], r["Nombre del Cliente"],
      r["Nombre del Chofer"], r["Placa Vehículo"]
    ].join(" ").toLowerCase();
    const passTexto   = !texto   || campos.includes(texto);
    const passEmpresa = !empresa || r["Empresa Logística"] === empresa;
    const passFecha   = !fecha   || coincideFecha(r["Fecha Documento"], fecha);
    return passTexto && passEmpresa && passFecha;
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

/* ─── Tabla ────────────────────────────────────────────────────── */
function renderTabla() {
  const tbody = document.getElementById("il-tabla-body");
  document.getElementById("il-contador").textContent =
    datosFiltrados.length + " registro" + (datosFiltrados.length !== 1 ? "s" : "");

  if (datosFiltrados.length === 0) {
    tbody.innerHTML = `<div class="il-empty">
      <i class="ph ph-leaf" style="font-size:40px; color:var(--color-primary)"></i>
      <p>Sin resultados con esos filtros.</p>
    </div>`;
    return;
  }

  let html = `<table class="il-tabla">
    <thead><tr>
      <th>Fecha</th><th>Empresa</th><th>Guía / Ingreso</th>
      <th>Finca</th><th>Cliente</th><th>Fulls</th><th>Temp.</th><th></th>
    </tr></thead><tbody>`;

  datosFiltrados.forEach((r, i) => {
    const empresa = r["Empresa Logística"] || "—";
    const fecha   = r["Fecha Documento"] || "—";
    const guia    = r["N° Guía / Ingreso"] || "—";
    const finca   = r["Finca / Exportador"] || "—";
    const cliente = r["Nombre del Cliente"] || "—";
    const fulls   = r["Total Fulls / PCS"] || "—";
    const temp    = r["Temperatura (°C)"] || "—";
    const fila    = r["_fila"];

    const tempNum = parseFloat(String(temp).replace(/[^0-9.\-]/g, ""));
    const tempCls = isNaN(tempNum) ? "" : tempNum > 5 ? "il-temp-alt" : "il-temp-ok";
    const badgeCls = badgeEmpresa(empresa);
    const fincaCorta  = finca.length > 22  ? finca.slice(0, 22) + "…" : finca;
    const clienteCorto = cliente.length > 20 ? cliente.slice(0, 20) + "…" : cliente;

    html += `<tr class="il-row" data-idx="${i}">
      <td>${fecha}</td>
      <td><span class="il-badge ${badgeCls}">${empresa}</span></td>
      <td><strong>${guia}</strong></td>
      <td title="${finca}">${fincaCorta}</td>
      <td title="${cliente}">${clienteCorto}</td>
      <td>${fulls}</td>
      <td class="${tempCls}">${temp}</td>
      <td><button class="btn btn-sm btn-outline il-btn-compartir" data-idx="${i}">
        <i class="ph ph-share-network"></i>
      </button></td>
    </tr>`;
  });

  html += "</tbody></table>";
  tbody.innerHTML = html;

  tbody.querySelectorAll(".il-row").forEach(row => {
    row.addEventListener("click", (e) => {
      if (!e.target.closest("button")) {
        abrirModal(datosFiltrados[row.dataset.idx]);
      }
    });
  });
  tbody.querySelectorAll(".il-btn-compartir").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      abrirModal(datosFiltrados[btn.dataset.idx]);
    });
  });
}

function badgeEmpresa(empresa) {
  const e = (empresa || "").toLowerCase();
  if (e.includes("one") || e.includes("teamcargo"))  return "il-badge-one";
  if (e.includes("pacific"))                          return "il-badge-pac";
  if (e.includes("value"))                            return "il-badge-val";
  if (e.includes("logiztik") || e.includes("alliance")) return "il-badge-log";
  if (e.includes("ldsexport") || e.includes("lds"))   return "il-badge-lds";
  if (e.includes("fresh"))                            return "il-badge-fresh";
  return "il-badge-otra";
}

/* ─── Modal ────────────────────────────────────────────────────── */
function abrirModal(reg) {
  if (!reg) return;
  document.getElementById("il-modal-guia").textContent =
    "Guía / Ingreso: " + (reg["N° Guía / Ingreso"] || "—");
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
setInterval(init, 180000);
```

### pages/dartis-import.html + .js

`frontend/pages/dartis-import.html`
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

`frontend/pages/dartis-import.js`
```javascript
const API = "/api/dartis/upload";

// ── Drag & drop + selección ───────────────────────────────────────────────────
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
    if (input.files[0]) {
      updateLabel(label, zone, input.files[0].name);
      checkReady();
    }
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

// ── Submit ────────────────────────────────────────────────────────────────────
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

// ── UI helpers ────────────────────────────────────────────────────────────────
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
      <i class="ph ph-warning"></i> <strong>Postcosechas sin finca asignada (revisar en farm_postcosecha):</strong>
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

## 16. Frontend — páginas de los módulos clonados

### pages/agrocalidad.html + .js (Fase 1)

`frontend/pages/agrocalidad.html`
```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>BLIS · Agrocalidad</title>
  <link rel="stylesheet" href="/css/styles.css" />
</head>
<body data-page="agrocalidad">
  <div id="sidebar" class="sidebar"></div>

  <main class="content" id="content">
    <div class="page-header">
      <h1><i class="ph ph-leaf"></i> Consulta Agrocalidad</h1>
      <p class="page-subtitle">Requisitos fitosanitarios de exportación por especie y país de destino.</p>
    </div>

    <div class="import-card">
      <form id="consultaForm">
        <div class="form-grid">
          <div class="form-group">
            <label for="species_id">Especie</label>
            <select id="species_id" required></select>
          </div>
          <div class="form-group">
            <label for="country_id">País de destino</label>
            <select id="country_id" required></select>
          </div>
          <div class="form-group">
            <label for="trade_type">Tipo de trámite</label>
            <select id="trade_type" required></select>
          </div>
          <div class="form-group">
            <label for="area_code">Área</label>
            <select id="area_code" required></select>
          </div>
        </div>

        <div class="import-actions">
          <button type="submit" id="btnConsultar" class="btn btn-primary">
            <i class="ph ph-magnifying-glass"></i> Consultar
          </button>
        </div>
      </form>

      <div id="progressSection" class="hidden">
        <div class="progress-bar"><div id="progressFill" class="progress-fill"></div></div>
        <p id="progressMsg" class="progress-msg">Consultando en Agrocalidad (puede tardar hasta 90 segundos)...</p>
      </div>

      <div id="resultSection" class="hidden"></div>
    </div>

    <div class="page-header" style="margin-top: 2rem;">
      <h2><i class="ph ph-clock-counter-clockwise"></i> Historial de consultas</h2>
    </div>

    <div class="import-card">
      <div class="form-grid">
        <div class="form-group">
          <label for="filter_species">Filtrar por especie</label>
          <select id="filter_species"><option value="">Todas</option></select>
        </div>
        <div class="form-group">
          <label for="filter_country">Filtrar por país</label>
          <select id="filter_country"><option value="">Todos</option></select>
        </div>
      </div>
      <table class="data-table">
        <thead>
          <tr>
            <th>Especie</th>
            <th>País</th>
            <th>Tipo</th>
            <th>Área</th>
            <th>Estado</th>
            <th>Código Agrocalidad</th>
            <th>Partida</th>
            <th>Consultado</th>
          </tr>
        </thead>
        <tbody id="historyBody">
          <tr><td colspan="8" class="loading">Cargando...</td></tr>
        </tbody>
      </table>
    </div>
  </main>

  <script type="module" src="/js/layout.js"></script>
  <script type="module" src="/pages/agrocalidad.js"></script>
</body>
</html>
```

`frontend/pages/agrocalidad.js`
```javascript
import { apiGet, apiPost } from "/js/api.js";

const ESTADO_BADGE = {
  CON_REQUISITOS: "badge-green",
  SIN_REQUISITOS_REGISTRADOS: "badge-gray",
  NO_ENCONTRADO: "badge-red",
  ERROR: "badge-red",
  pending: "badge-blue",
  processing: "badge-blue",
  done: "badge-green",
  error: "badge-red",
};

let catalogo = { especies: [], paises: [] };
let pollTimer = null;

function fillSelect(select, items, { value, label, placeholder }) {
  select.innerHTML = "";
  if (placeholder) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = placeholder;
    select.appendChild(opt);
  }
  for (const item of items) {
    const opt = document.createElement("option");
    opt.value = item[value];
    opt.textContent = item[label];
    select.appendChild(opt);
  }
}

async function initCatalogo() {
  catalogo = await apiGet("/agrocalidad/catalogo");

  fillSelect(document.getElementById("species_id"), catalogo.especies, { value: "id", label: "name" });
  fillSelect(document.getElementById("country_id"), catalogo.paises, {
    value: "id",
    label: "name_es",
  });
  fillSelect(document.getElementById("trade_type"), catalogo.tipos.map(t => ({ v: t })), { value: "v", label: "v" });
  fillSelect(document.getElementById("area_code"), catalogo.areas.map(a => ({ v: a })), { value: "v", label: "v" });
  document.getElementById("trade_type").value = "Exportación";
  document.getElementById("area_code").value = "SV";

  fillSelect(document.getElementById("filter_species"), catalogo.especies, {
    value: "id", label: "name", placeholder: "Todas",
  });
  fillSelect(document.getElementById("filter_country"), catalogo.paises, {
    value: "id", label: "name_es", placeholder: "Todos",
  });
}

document.getElementById("consultaForm").addEventListener("submit", async e => {
  e.preventDefault();
  const btn = document.getElementById("btnConsultar");
  btn.disabled = true;
  clearInterval(pollTimer);

  const payload = {
    species_id: document.getElementById("species_id").value,
    country_id: document.getElementById("country_id").value,
    trade_type: document.getElementById("trade_type").value,
    area_code: document.getElementById("area_code").value,
  };

  showProgress();

  try {
    const solicitud = await apiPost("/agrocalidad/consultar", payload);
    pollSolicitud(solicitud.id);
  } catch (err) {
    hideProgress();
    showError(err.message);
    btn.disabled = false;
  }
});

function pollSolicitud(id) {
  pollTimer = setInterval(async () => {
    try {
      const solicitud = await apiGet(`/agrocalidad/solicitud/${id}`);
      if (solicitud.status === "done") {
        clearInterval(pollTimer);
        hideProgress();
        showResult(solicitud.requirement);
        document.getElementById("btnConsultar").disabled = false;
        cargarHistorial();
      } else if (solicitud.status === "error") {
        clearInterval(pollTimer);
        hideProgress();
        showError(solicitud.error_message || "La consulta terminó en error");
        document.getElementById("btnConsultar").disabled = false;
      }
      // pending / processing -> sigue esperando
    } catch (err) {
      clearInterval(pollTimer);
      hideProgress();
      showError(err.message);
      document.getElementById("btnConsultar").disabled = false;
    }
  }, 4000);
}

function showProgress() {
  document.getElementById("progressSection").classList.remove("hidden");
  document.getElementById("resultSection").classList.add("hidden");
  let w = 0;
  window._prog = setInterval(() => {
    w = Math.min(w + 1, 90);
    document.getElementById("progressFill").style.width = w + "%";
  }, 1000);
}

function hideProgress() {
  clearInterval(window._prog);
  const fill = document.getElementById("progressFill");
  fill.style.width = "100%";
  setTimeout(() => {
    document.getElementById("progressSection").classList.add("hidden");
    fill.style.width = "0%";
  }, 400);
}

function showResult(req) {
  const section = document.getElementById("resultSection");
  if (!req) {
    section.innerHTML = `<div class="result-box error"><h3><i class="ph ph-x-circle"></i> Sin resultado</h3></div>`;
    section.classList.remove("hidden");
    return;
  }
  const badge = ESTADO_BADGE[req.status] || "badge-gray";
  section.innerHTML = `
    <div class="result-box success">
      <h3><i class="ph ph-check-circle"></i> ${req.matched_product_name || "Consulta completada"}
        <span class="badge ${badge}">${req.status}</span>
      </h3>
      <p><strong>Nombre científico:</strong> ${req.scientific_name || "-"}</p>
      <p><strong>Partida arancelaria:</strong> ${req.tariff_heading || "-"}</p>
      <p><strong>Código Agrocalidad:</strong> ${req.agrocalidad_code || "-"}</p>
      <p><strong>Requisitos:</strong><br>${(req.requirements || "Sin requisitos registrados").replace(/\/\/\//g, "<br>")}</p>
    </div>`;
  section.classList.remove("hidden");
}

function showError(msg) {
  const section = document.getElementById("resultSection");
  section.innerHTML = `<div class="result-box error"><h3><i class="ph ph-x-circle"></i> Error</h3><p>${msg}</p></div>`;
  section.classList.remove("hidden");
}

async function cargarHistorial() {
  const speciesId = document.getElementById("filter_species").value;
  const countryId = document.getElementById("filter_country").value;
  const params = new URLSearchParams();
  if (speciesId) params.set("species_id", speciesId);
  if (countryId) params.set("country_id", countryId);

  const tbody = document.getElementById("historyBody");
  tbody.innerHTML = `<tr><td colspan="8" class="loading">Cargando...</td></tr>`;

  try {
    const rows = await apiGet(`/agrocalidad/requisitos?${params.toString()}`);
    if (!rows.length) {
      tbody.innerHTML = `<tr><td colspan="8" class="empty">Sin consultas registradas</td></tr>`;
      return;
    }
    tbody.innerHTML = rows.map(r => `
      <tr>
        <td>${r.species_name}</td>
        <td>${r.country_name}</td>
        <td>${r.trade_type}</td>
        <td>${r.area_code}</td>
        <td><span class="badge ${ESTADO_BADGE[r.status] || "badge-gray"}">${r.status}</span></td>
        <td>${r.agrocalidad_code || "-"}</td>
        <td>${r.tariff_heading || "-"}</td>
        <td>${new Date(r.queried_at).toLocaleDateString("es-EC")}</td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" class="error">${err.message}</td></tr>`;
  }
}

document.getElementById("filter_species").addEventListener("change", cargarHistorial);
document.getElementById("filter_country").addEventListener("change", cargarHistorial);

initCatalogo().then(cargarHistorial);
```

### pages/inventario-lag.html + .js (Fase 2) — 5 sub-pestañas del proyecto original en una sola página

`frontend/pages/inventario-lag.html`
```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>BLIS · Inventario LAG</title>
  <link rel="stylesheet" href="/css/styles.css" />
</head>
<body data-page="inventario-lag">
  <div id="sidebar" class="sidebar"></div>

  <main class="content" id="content">
    <div class="page-header">
      <h1><i class="ph ph-warehouse"></i> Inventario LAG</h1>
      <p class="page-subtitle">Bodega de Bellaflor en Miami (Logiztik Alliance Group) — consulta en vivo, sin datos propios.</p>
    </div>

    <nav class="subtabs">
      <button class="subtab active" data-tab="inventario">Inventario</button>
      <button class="subtab" data-tab="reporte">Reporte detallado</button>
      <button class="subtab" data-tab="envios">Envíos</button>
      <button class="subtab" data-tab="compras">Órdenes de compra</button>
      <button class="subtab" data-tab="ventas">Órdenes de venta</button>
      <button class="subtab" data-tab="posteo">Posteo de Inventario</button>
    </nav>

    <!-- INVENTARIO -->
    <section id="panel-inventario" class="subpanel active">
      <div class="import-card">
        <h3>Piezas disponibles en bodega (Miami)</h3>
        <div class="import-actions" style="justify-content: flex-start; gap: .75rem;">
          <button id="btn-piezas" class="btn btn-primary"><i class="ph ph-magnifying-glass"></i> Consultar inventario</button>
          <button id="btn-exportar" class="btn btn-secondary" disabled><i class="ph ph-download-simple"></i> Exportar CSV</button>
          <span id="actualizado" class="page-subtitle"></span>
        </div>

        <div id="tarjetas" class="card-grid hidden" style="margin-top: 1.25rem;">
          <div class="summary-card">
            <span class="summary-card-value" id="kpi-piezas">0</span>
            <span class="summary-card-label">Piezas en inventario</span>
          </div>
          <div class="summary-card">
            <span class="summary-card-value" id="kpi-racks">0</span>
            <span class="summary-card-label">Ubicaciones ocupadas</span>
          </div>
          <div class="summary-card">
            <span class="summary-card-value" id="kpi-visibles">0</span>
            <span class="summary-card-label">Piezas mostradas</span>
          </div>
        </div>

        <div id="filtros" class="form-grid hidden" style="margin-top: 1.25rem;">
          <div class="form-group">
            <label>Buscar barcode</label>
            <input id="buscar-barcode" type="search" placeholder="Ej. 12202605462" autocomplete="off" />
          </div>
          <div class="form-group">
            <label>Ubicación (rack)</label>
            <select id="filtro-rack"><option value="">Todas</option></select>
          </div>
          <div class="form-group" style="align-self: end;">
            <button type="button" id="btn-limpiar" class="btn btn-secondary">Limpiar filtros</button>
          </div>
        </div>

        <div id="res-piezas" class="resultado"></div>

        <details id="resumen-racks" class="hidden" style="margin-top: 1rem;">
          <summary>Resumen de piezas por ubicación</summary>
          <div id="res-racks"></div>
        </details>
      </div>

      <div class="import-card" style="margin-top: 1.5rem;">
        <h3>Códigos de barra por envío</h3>
        <form id="form-barcode" class="form-grid">
          <div class="form-group">
            <label>Número de envío (AWB/HAWB)</label>
            <input name="shipmentNr" required placeholder="17202083572" />
          </div>
          <div class="form-group" style="align-self: end;">
            <button type="submit" class="btn btn-primary">Consultar</button>
          </div>
        </form>
        <div id="res-barcode" class="resultado"></div>
      </div>
    </section>

    <!-- REPORTE DETALLADO -->
    <section id="panel-reporte" class="subpanel">
      <div class="import-card">
        <h3>Reporte detallado de piezas</h3>
        <p class="page-subtitle">
          Equivale al reporte ResumenCodigosDeBarra del WMS. Combina tres consultas de LAG:
          las guías de la fecha, el detalle de cada pieza y su ubicación en bodega.
        </p>

        <form id="form-reporte" class="form-grid">
          <div class="form-group">
            <label>Fecha de embarque</label>
            <input type="date" name="fecha" />
          </div>
          <div class="form-group">
            <label>Guías (separadas por coma)</label>
            <input name="guias" placeholder="023-0326 9313, 023-0326 9571" />
          </div>
          <div class="form-group" style="align-self: end; display: flex; gap: .5rem;">
            <button type="submit" class="btn btn-primary">Generar reporte</button>
            <button type="button" id="btn-exportar-rep" class="btn btn-secondary" disabled>Exportar CSV</button>
          </div>
        </form>

        <div id="avisos-rep"></div>

        <div id="tarjetas-rep" class="card-grid hidden">
          <div class="summary-card"><span class="summary-card-value" id="rep-piezas">0</span><span class="summary-card-label">Piezas</span></div>
          <div class="summary-card"><span class="summary-card-value" id="rep-recibidas">0</span><span class="summary-card-label">En bodega</span></div>
          <div class="summary-card"><span class="summary-card-value" id="rep-pendientes">0</span><span class="summary-card-label">Pendientes</span></div>
          <div class="summary-card"><span class="summary-card-value" id="rep-unidades">0</span><span class="summary-card-label">Unidades / tallos</span></div>
          <div class="summary-card"><span class="summary-card-value" id="rep-valor">0</span><span class="summary-card-label">Valor total</span></div>
        </div>

        <div id="filtros-rep" class="form-grid hidden">
          <div class="form-group">
            <label>Estado</label>
            <select id="rep-estado">
              <option value="">Todos</option>
              <option value="recibidas">Solo en bodega</option>
              <option value="pendientes">Solo pendientes</option>
            </select>
          </div>
          <div class="form-group">
            <label>Buscar</label>
            <input id="rep-buscar" type="search" placeholder="barcode, consignee, producto" autocomplete="off" />
          </div>
          <div class="form-group">
            <label>Consignee</label>
            <select id="rep-consignee"><option value="">Todos</option></select>
          </div>
          <div class="form-group" style="align-self: end;">
            <button type="button" id="rep-limpiar" class="btn btn-secondary">Limpiar</button>
          </div>
        </div>

        <div id="res-reporte" class="resultado"></div>
      </div>
    </section>

    <!-- ENVIOS -->
    <section id="panel-envios" class="subpanel">
      <div class="import-card">
        <h3>Información de envíos por fecha</h3>
        <form id="form-envios" class="form-grid">
          <div class="form-group"><label>Fecha</label><input type="date" name="fecha" required /></div>
          <div class="form-group" style="align-self: end;"><button type="submit" class="btn btn-primary">Consultar</button></div>
        </form>
        <div id="res-envios" class="resultado"></div>
      </div>

      <div class="import-card" style="margin-top: 1.5rem;">
        <h3>Piezas despachadas a carrier</h3>
        <form id="form-despachadas" class="form-grid">
          <div class="form-group"><label>Fecha</label><input type="date" name="fecha" required /></div>
          <div class="form-group" style="align-self: end;"><button type="submit" class="btn btn-primary">Consultar</button></div>
        </form>
        <div id="res-despachadas" class="resultado"></div>
      </div>
    </section>

    <!-- ORDENES DE COMPRA -->
    <section id="panel-compras" class="subpanel">
      <div class="import-card">
        <h3>Crear orden de compra (PO)</h3>
        <form id="form-po">
          <fieldset style="border: none; padding: 0; margin: 0 0 1rem;">
            <legend style="font-weight: 600; margin-bottom: .5rem;">Cabecera</legend>
            <div class="form-grid">
              <div class="form-group"><label>Consignee Code *</label><input name="consignee_code" required maxlength="32" /></div>
              <div class="form-group"><label>Destino (IATA) *</label><input name="destination_port_code" required maxlength="3" placeholder="MIA" /></div>
              <div class="form-group">
                <label>Tipo de PO *</label>
                <select name="post_type" required>
                  <option value="FINAL">FINAL</option>
                  <option value="LOCAL">LOCAL</option>
                </select>
              </div>
              <div class="form-group"><label>Warehouse Code</label><input name="warehouse_code" maxlength="8" placeholder="Requerido si LOCAL" /></div>
              <div class="form-group"><label>Número de PO</label><input name="po_number" maxlength="32" /></div>
              <div class="form-group"><label>Origen (IATA)</label><input name="origin_port_code" maxlength="3" placeholder="UIO" /></div>
              <div class="form-group"><label>Fecha estimada</label><input type="date" name="estimated_date" /></div>
              <div class="form-group">
                <label>Acción</label>
                <select name="accion"><option value="INSERT">INSERT</option><option value="DELETE">DELETE</option></select>
              </div>
              <div class="form-group"><label>Comentarios</label><input name="comments" maxlength="256" /></div>
            </div>
          </fieldset>

          <fieldset style="border: none; padding: 0; margin: 0 0 1rem;">
            <legend style="font-weight: 600; margin-bottom: .5rem;">Detalle de cajas</legend>
            <div id="items-po"></div>
            <button type="button" id="btn-add-item" class="btn btn-secondary">+ Agregar caja</button>
          </fieldset>

          <button type="submit" class="btn btn-primary">Enviar orden de compra</button>
        </form>
        <div id="res-po" class="resultado"></div>
      </div>
    </section>

    <!-- ORDENES DE VENTA -->
    <section id="panel-ventas" class="subpanel">
      <div class="import-card">
        <h3>Crear orden de venta</h3>
        <form id="form-venta">
          <div class="form-grid">
            <div class="form-group"><label>Customer ID *</label><input name="customerId" required maxlength="16" /></div>
            <div class="form-group"><label>Carrier ID *</label><input name="carrierId" required maxlength="16" placeholder="PIK" /></div>
            <div class="form-group"><label>Fecha de embarque *</label><input type="date" name="shipDate" required /></div>
            <div class="form-group"><label>Número de orden *</label><input name="orderNumber" required maxlength="16" /></div>
            <div class="form-group"><label>ID de orden (numérico) *</label><input type="number" name="idOrder" required /></div>
            <div class="form-group"><label>Número de PO</label><input name="poNumber" maxlength="16" /></div>
            <div class="form-group">
              <label>Generar BOL</label>
              <select name="generateBOL">
                <option value="">(no enviar)</option>
                <option value="true">Sí</option>
                <option value="false">No</option>
              </select>
            </div>
          </div>
          <fieldset style="border: none; padding: 0; margin: 0 0 1rem;">
            <legend style="font-weight: 600; margin-bottom: .5rem;">Cajas</legend>
            <div id="items-venta"></div>
            <button type="button" id="btn-add-box" class="btn btn-secondary">+ Agregar caja</button>
          </fieldset>
          <button type="submit" class="btn btn-primary">Crear orden de venta</button>
        </form>
        <div id="res-venta" class="resultado"></div>
      </div>

      <div class="import-card" style="margin-top: 1.5rem;">
        <h3>Cancelar orden de venta</h3>
        <form id="form-cancelar" class="form-grid">
          <div class="form-group"><label>ID de orden</label><input type="number" name="idOrder" required /></div>
          <div class="form-group" style="align-self: end;"><button type="submit" class="btn btn-danger">Cancelar orden</button></div>
        </form>
        <div id="res-cancelar" class="resultado"></div>
      </div>
    </section>

    <section id="panel-posteo" class="subpanel">
      <div class="import-card">
        <h3>Posteo de Inventario</h3>
        <div class="import-rule" style="background: #fef2f2; border-color: #fca5a5; color: #b91c1c;">
          <i class="ph ph-warning"></i>
          <span><strong>Sin ambiente de pruebas.</strong> Este endpoint (`PlaceOrder/ordernew`) solo existe en producción de LAG — cada envío crea una orden real en el WMS. Verifica los datos antes de enviar.</span>
        </div>
        <form id="form-posteo">
          <div class="form-grid">
            <div class="form-group">
              <label>Cliente *</label>
              <div class="combo-buscable" id="posteo-customer-combo">
                <input type="text" id="posteo-customer-search" placeholder="Cargando clientes..." autocomplete="off" disabled />
                <input type="hidden" name="customerId" id="posteo-customer-value" />
                <div class="combo-opciones" id="posteo-customer-opciones"></div>
              </div>
            </div>
            <div class="form-group">
              <label>Carrier *</label>
              <div class="combo-buscable" id="posteo-carrier-combo">
                <input type="text" id="posteo-carrier-search" placeholder="Cargando carriers..." autocomplete="off" disabled />
                <input type="hidden" name="carrierId" id="posteo-carrier-value" />
                <div class="combo-opciones" id="posteo-carrier-opciones"></div>
              </div>
            </div>
            <div class="form-group"><label>Miami Ship Date *</label><input type="date" name="miamiShipDate" required /></div>
            <div class="form-group">
              <label>Imprimir etiquetas WMS</label>
              <select name="printWmsLabels">
                <option value="true" selected>Sí</option>
                <option value="false">No</option>
              </select>
            </div>
          </div>
          <fieldset style="border: none; padding: 0; margin: 0 0 1rem;">
            <legend style="font-weight: 600; margin-bottom: .5rem;">Cajas</legend>
            <div id="items-posteo"></div>
            <button type="button" id="btn-add-box-posteo" class="btn btn-secondary">+ Agregar caja</button>
          </fieldset>
          <button type="submit" class="btn btn-danger">Postear inventario en LAG</button>
        </form>
        <div id="res-posteo" class="resultado"></div>
      </div>
    </section>
  </main>

  <script type="module" src="/js/layout.js"></script>
  <script type="module" src="/pages/inventario-lag.js"></script>
</body>
</html>
```

`frontend/pages/inventario-lag.js`
```javascript
import { apiGet, apiPost } from "/js/api.js";

// ---------- API del modulo (proxy sobre LAG) ----------
const api = {
  crearOrdenCompra: (payload) => apiPost("/inventario-lag/purchase-orders", payload),
  piezasInventario: () => apiGet("/inventario-lag/pieces"),
  reporteDetallado: (params) => apiGet(`/inventario-lag/full?${new URLSearchParams(params)}`),
  infoCodigosBarra: (shipmentNr) => apiGet(`/inventario-lag/barcode/${encodeURIComponent(shipmentNr)}`),
  infoEnvios: (fecha) => apiGet(`/inventario-lag/shipments?fecha=${fecha}`),
  piezasDespachadas: (fecha) => apiGet(`/inventario-lag/dispatched?fecha=${fecha}`),
  crearOrdenVenta: (payload) => apiPost("/inventario-lag/sales-orders", payload),
  cancelarOrdenVenta: (idOrder) =>
    apiPost("/inventario-lag/sales-orders/cancel", { idOrder: Number(idOrder) }),
  postearInventario: (payload) => apiPost("/inventario-lag/posteo-inventario", payload),
};

// ---------- Utilidades ----------
const $ = (sel) => document.querySelector(sel);

function mostrarError(destino, mensaje) {
  const div = $(destino);
  div.innerHTML = "";
  const p = document.createElement("p");
  p.className = "msg-error";
  p.textContent = mensaje;
  div.appendChild(p);
}

function mostrarMensaje(destino, mensaje, clase = "msg-ok") {
  const div = $(destino);
  div.innerHTML = "";
  const p = document.createElement("p");
  p.className = clase;
  p.textContent = mensaje;
  div.appendChild(p);
}

function mostrarTabla(destino, filas) {
  const div = $(destino);
  div.innerHTML = "";

  if (!Array.isArray(filas) || filas.length === 0) {
    mostrarMensaje(destino, "Sin resultados para esta consulta.", "msg-info");
    return;
  }

  const columnas = [...new Set(filas.flatMap((f) => Object.keys(f)))];

  const conteo = document.createElement("p");
  conteo.className = "conteo";
  conteo.textContent = `${filas.length} registro(s)`;
  div.appendChild(conteo);

  const tabla = document.createElement("table");
  tabla.className = "data-table";
  const thead = tabla.createTHead().insertRow();
  columnas.forEach((c) => {
    const th = document.createElement("th");
    th.textContent = c;
    thead.appendChild(th);
  });

  const tbody = tabla.createTBody();
  filas.forEach((fila) => {
    const tr = tbody.insertRow();
    columnas.forEach((c) => {
      const valor = fila[c];
      tr.insertCell().textContent =
        valor === null || valor === undefined
          ? ""
          : typeof valor === "object"
            ? JSON.stringify(valor)
            : String(valor);
    });
  });

  const wrap = document.createElement("div");
  wrap.className = "tabla-wrap";
  wrap.appendChild(tabla);
  div.appendChild(wrap);
}

async function ejecutar(boton, destino, accion) {
  boton.disabled = true;
  mostrarMensaje(destino, "Consultando...", "msg-info");
  try {
    await accion();
  } catch (err) {
    mostrarError(destino, err.message);
  } finally {
    boton.disabled = false;
  }
}

function datosFormulario(form) {
  const datos = {};
  new FormData(form).forEach((valor, clave) => {
    const texto = String(valor).trim();
    if (texto !== "") datos[clave] = texto;
  });
  return datos;
}

// ---------- Navegacion por sub-pestanas ----------
document.querySelectorAll(".subtab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".subtab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".subpanel").forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    $(`#panel-${tab.dataset.tab}`).classList.add("active");
  });
});

// ---------- Inventario ----------
const inventario = {
  piezas: [],
  orden: { columna: "rack", asc: true },
};

function aplicarFiltros() {
  const texto = $("#buscar-barcode").value.trim().toLowerCase();
  const rack = $("#filtro-rack").value;

  let filas = inventario.piezas.filter(
    (p) => (!texto || p.barcode.toLowerCase().includes(texto)) && (!rack || p.rack === rack)
  );

  const { columna, asc } = inventario.orden;
  filas = [...filas].sort((a, b) => a[columna].localeCompare(b[columna]) * (asc ? 1 : -1));

  $("#kpi-visibles").textContent = filas.length;
  renderTablaInventario(filas);
}

function renderTablaInventario(filas) {
  const div = $("#res-piezas");
  div.innerHTML = "";

  if (filas.length === 0) {
    mostrarMensaje(
      "#res-piezas",
      inventario.piezas.length === 0
        ? "LAG no reporta piezas en inventario para este cliente."
        : "Ninguna pieza coincide con los filtros aplicados.",
      "msg-info"
    );
    return;
  }

  const tabla = document.createElement("table");
  tabla.className = "data-table";
  const encabezado = tabla.createTHead().insertRow();

  [
    { clave: "barcode", titulo: "Barcode" },
    { clave: "rack", titulo: "Ubicacion (rack)" },
  ].forEach(({ clave, titulo }) => {
    const th = document.createElement("th");
    const activa = inventario.orden.columna === clave;
    th.textContent = titulo + (activa ? (inventario.orden.asc ? " ▲" : " ▼") : "");
    th.style.cursor = "pointer";
    th.addEventListener("click", () => {
      inventario.orden = {
        columna: clave,
        asc: activa ? !inventario.orden.asc : true,
      };
      aplicarFiltros();
    });
    encabezado.appendChild(th);
  });

  const tbody = tabla.createTBody();
  filas.forEach((pieza) => {
    const tr = tbody.insertRow();
    tr.insertCell().textContent = pieza.barcode;
    tr.insertCell().textContent = pieza.rack;
  });

  const wrap = document.createElement("div");
  wrap.className = "tabla-wrap";
  wrap.appendChild(tabla);
  div.appendChild(wrap);
}

function renderResumenRacks(resumen) {
  const div = $("#res-racks");
  div.innerHTML = "";

  const tabla = document.createElement("table");
  tabla.className = "data-table";
  const encabezado = tabla.createTHead().insertRow();
  ["Ubicacion (rack)", "Piezas"].forEach((t) => {
    const th = document.createElement("th");
    th.textContent = t;
    encabezado.appendChild(th);
  });

  const tbody = tabla.createTBody();
  resumen.forEach((fila) => {
    const tr = tbody.insertRow();
    const celdaRack = tr.insertCell();
    const enlace = document.createElement("button");
    enlace.type = "button";
    enlace.className = "enlace";
    enlace.textContent = fila.rack;
    enlace.addEventListener("click", () => {
      $("#filtro-rack").value = fila.rack;
      $("#resumen-racks").open = false;
      aplicarFiltros();
    });
    celdaRack.appendChild(enlace);
    tr.insertCell().textContent = fila.piezas;
  });

  const wrap = document.createElement("div");
  wrap.className = "tabla-wrap";
  wrap.appendChild(tabla);
  div.appendChild(wrap);
}

$("#btn-piezas").addEventListener("click", (e) =>
  ejecutar(e.target, "#res-piezas", async () => {
    const data = await api.piezasInventario();

    inventario.piezas = data.piezas;
    $("#kpi-piezas").textContent = data.total_piezas;
    $("#kpi-racks").textContent = data.total_racks;

    const select = $("#filtro-rack");
    const rackPrevio = select.value;
    select.innerHTML = '<option value="">Todas</option>';
    data.resumen_racks.forEach((r) => {
      const opcion = document.createElement("option");
      opcion.value = r.rack;
      opcion.textContent = `${r.rack} (${r.piezas})`;
      select.appendChild(opcion);
    });
    select.value = data.resumen_racks.some((r) => r.rack === rackPrevio) ? rackPrevio : "";

    renderResumenRacks(data.resumen_racks);

    ["#tarjetas", "#filtros", "#resumen-racks"].forEach((sel) => $(sel).classList.remove("hidden"));
    $("#btn-exportar").disabled = data.total_piezas === 0;
    $("#actualizado").textContent = `Actualizado ${new Date().toLocaleString("es-EC")}`;

    aplicarFiltros();
  })
);

$("#buscar-barcode").addEventListener("input", aplicarFiltros);
$("#filtro-rack").addEventListener("change", aplicarFiltros);

$("#btn-limpiar").addEventListener("click", () => {
  $("#buscar-barcode").value = "";
  $("#filtro-rack").value = "";
  aplicarFiltros();
});

$("#btn-exportar").addEventListener("click", () => {
  const texto = $("#buscar-barcode").value.trim().toLowerCase();
  const rack = $("#filtro-rack").value;
  const filas = inventario.piezas.filter(
    (p) => (!texto || p.barcode.toLowerCase().includes(texto)) && (!rack || p.rack === rack)
  );

  // BOM inicial para que Excel respete los acentos al abrir el CSV.
  const csv = ["barcode;rack", ...filas.map((p) => `${p.barcode};${p.rack}`)].join("\r\n");
  const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);

  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = `inventario_${new Date().toISOString().slice(0, 10)}.csv`;
  enlace.click();
  URL.revokeObjectURL(url);
});

$("#form-barcode").addEventListener("submit", (e) => {
  e.preventDefault();
  const shipmentNr = datosFormulario(e.target).shipmentNr;
  ejecutar(e.target.querySelector("button"), "#res-barcode", async () => {
    mostrarTabla("#res-barcode", await api.infoCodigosBarra(shipmentNr));
  });
});

// ---------- Reporte detallado ----------
const COLUMNAS_REPORTE = [
  { clave: "status", titulo: "Status" },
  { clave: "barcode", titulo: "Barcode" },
  { clave: "shipment_nr", titulo: "Shipment Nr" },
  { clave: "house", titulo: "House" },
  { clave: "exporter", titulo: "Exporter" },
  { clave: "consignee", titulo: "Consignee" },
  { clave: "carrier", titulo: "Carrier" },
  { clave: "location", titulo: "Location" },
  { clave: "product", titulo: "Product" },
  { clave: "description", titulo: "Description" },
  { clave: "tipo", titulo: "Type" },
  { clave: "largo_cm", titulo: "Largo Cm" },
  { clave: "ancho_cm", titulo: "Ancho Cm" },
  { clave: "alto_cm", titulo: "Alto Cm" },
  { clave: "largo_inch", titulo: "Largo Inch" },
  { clave: "ancho_inch", titulo: "Ancho Inch" },
  { clave: "alto_inch", titulo: "Alto Inch" },
  { clave: "unidades", titulo: "Uni/Pcs" },
  { clave: "precio", titulo: "Price" },
  { clave: "peso", titulo: "Weight" },
  { clave: "valor_caja", titulo: "Valor caja" },
];

const reporte = { piezas: [] };

function esRecibida(p) {
  return (p.status || "").toUpperCase().includes("RECEIV");
}

function filtrarReporte() {
  const estado = $("#rep-estado").value;
  const texto = $("#rep-buscar").value.trim().toLowerCase();
  const consignee = $("#rep-consignee").value;

  return reporte.piezas.filter((p) => {
    if (estado === "recibidas" && !esRecibida(p)) return false;
    if (estado === "pendientes" && esRecibida(p)) return false;
    if (consignee && p.consignee !== consignee) return false;
    if (texto) {
      const heno = `${p.barcode} ${p.consignee} ${p.product} ${p.description} ${p.house}`;
      if (!heno.toLowerCase().includes(texto)) return false;
    }
    return true;
  });
}

function renderReporte() {
  const filas = filtrarReporte();
  const div = $("#res-reporte");
  div.innerHTML = "";

  if (filas.length === 0) {
    mostrarMensaje(
      "#res-reporte",
      reporte.piezas.length === 0
        ? "La consulta no devolvio piezas."
        : "Ninguna pieza coincide con los filtros.",
      "msg-info"
    );
    return;
  }

  const conteo = document.createElement("p");
  conteo.className = "conteo";
  conteo.textContent = `${filas.length} de ${reporte.piezas.length} piezas`;
  div.appendChild(conteo);

  const tabla = document.createElement("table");
  tabla.className = "data-table";
  const encabezado = tabla.createTHead().insertRow();
  COLUMNAS_REPORTE.forEach((c) => {
    const th = document.createElement("th");
    th.textContent = c.titulo;
    encabezado.appendChild(th);
  });

  const tbody = tabla.createTBody();
  filas.forEach((pieza) => {
    const tr = tbody.insertRow();
    if (!esRecibida(pieza)) tr.className = "pendiente";
    COLUMNAS_REPORTE.forEach((c) => {
      const valor = pieza[c.clave];
      tr.insertCell().textContent = valor === null || valor === undefined ? "" : String(valor);
    });
  });

  const wrap = document.createElement("div");
  wrap.className = "tabla-wrap";
  wrap.appendChild(tabla);
  div.appendChild(wrap);
}

$("#form-reporte").addEventListener("submit", (e) => {
  e.preventDefault();
  const datos = datosFormulario(e.target);

  if (!datos.fecha && !datos.guias) {
    mostrarError("#res-reporte", "Indique una fecha de embarque o al menos una guia.");
    return;
  }

  ejecutar(e.target.querySelector('button[type="submit"]'), "#res-reporte", async () => {
    const data = await api.reporteDetallado(datos);
    reporte.piezas = data.piezas;

    $("#rep-piezas").textContent = data.total_piezas;
    $("#rep-recibidas").textContent = data.total_recibidas;
    $("#rep-pendientes").textContent = data.total_pendientes;
    $("#rep-unidades").textContent = data.total_unidades.toLocaleString("es-EC");
    $("#rep-valor").textContent = `$${data.valor_total.toLocaleString("es-EC")}`;

    const select = $("#rep-consignee");
    select.innerHTML = '<option value="">Todos</option>';
    [...new Set(data.piezas.map((p) => p.consignee).filter(Boolean))].sort().forEach((c) => {
      const opcion = document.createElement("option");
      opcion.value = c;
      opcion.textContent = c;
      select.appendChild(opcion);
    });

    const avisos = $("#avisos-rep");
    avisos.innerHTML = "";
    data.avisos.forEach((texto) => {
      const p = document.createElement("p");
      p.className = "msg-aviso";
      p.textContent = texto;
      avisos.appendChild(p);
    });

    ["#tarjetas-rep", "#filtros-rep"].forEach((s) => $(s).classList.remove("hidden"));
    $("#btn-exportar-rep").disabled = data.total_piezas === 0;
    renderReporte();
  });
});

["#rep-estado", "#rep-consignee"].forEach((s) => $(s).addEventListener("change", renderReporte));
$("#rep-buscar").addEventListener("input", renderReporte);
$("#rep-limpiar").addEventListener("click", () => {
  $("#rep-estado").value = "";
  $("#rep-buscar").value = "";
  $("#rep-consignee").value = "";
  renderReporte();
});

$("#btn-exportar-rep").addEventListener("click", () => {
  const filas = filtrarReporte();
  const escapar = (v) => {
    const t = v === null || v === undefined ? "" : String(v);
    return t.includes(";") || t.includes('"') ? `"${t.replace(/"/g, '""')}"` : t;
  };

  const csv = [
    COLUMNAS_REPORTE.map((c) => c.titulo).join(";"),
    ...filas.map((p) => COLUMNAS_REPORTE.map((c) => escapar(p[c.clave])).join(";")),
  ].join("\r\n");

  const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = `ResumenCodigosDeBarra_${new Date().toISOString().slice(0, 10)}.csv`;
  enlace.click();
  URL.revokeObjectURL(url);
});

// ---------- Envios ----------
$("#form-envios").addEventListener("submit", (e) => {
  e.preventDefault();
  const fecha = datosFormulario(e.target).fecha;
  ejecutar(e.target.querySelector("button"), "#res-envios", async () => {
    mostrarTabla("#res-envios", await api.infoEnvios(fecha));
  });
});

$("#form-despachadas").addEventListener("submit", (e) => {
  e.preventDefault();
  const fecha = datosFormulario(e.target).fecha;
  ejecutar(e.target.querySelector("button"), "#res-despachadas", async () => {
    mostrarTabla("#res-despachadas", await api.piezasDespachadas(fecha));
  });
});

// ---------- Ordenes de compra ----------
function plantillaItemPO() {
  const div = document.createElement("div");
  div.className = "item-row";
  div.innerHTML = `
    <div class="form-grid">
      <div class="form-group"><label>Farm Code *</label><input name="farm_code" required maxlength="32" /></div>
      <div class="form-group"><label>Barcode</label><input name="barcode" maxlength="11" /></div>
      <div class="form-group"><label>Box Size</label><input name="box_size" maxlength="16" placeholder="QB" /></div>
      <div class="form-group"><label>Codigo producto</label><input name="product_code" maxlength="32" /></div>
      <div class="form-group"><label>Descripcion</label><input name="product_description" maxlength="128" /></div>
      <div class="form-group"><label>Packing</label><input type="number" name="packing" min="0" /></div>
      <div class="form-group"><label>Precio unitario</label><input type="number" step="0.01" name="unit_price" min="0" /></div>
      <div class="form-group"><label>Largo *</label><input type="number" step="0.01" name="length" required min="0" /></div>
      <div class="form-group"><label>Ancho *</label><input type="number" step="0.01" name="width" required min="0" /></div>
      <div class="form-group"><label>Alto *</label><input type="number" step="0.01" name="height" required min="0" /></div>
      <div class="form-group"><label>Peso bruto *</label><input type="number" step="0.01" name="gross_weight" required min="0" /></div>
      <div class="form-group">
        <label>Unidad de medida *</label>
        <select name="unit_of_measurement"><option value="CM">CM</option><option value="INCH">INCH</option></select>
      </div>
      <div class="form-group"><label>Carrier Code</label><input name="carrier_code" maxlength="8" /></div>
      <div class="form-group"><label>Ship To Code</label><input name="ship_to_code" maxlength="32" /></div>
      <div class="form-group"><label>Fecha de despacho</label><input type="date" name="dispatch_date" /></div>
    </div>
    <button type="button" class="btn btn-secondary btn-quitar">Quitar</button>`;
  div.querySelector(".btn-quitar").addEventListener("click", () => div.remove());
  return div;
}

$("#btn-add-item").addEventListener("click", () => $("#items-po").appendChild(plantillaItemPO()));
$("#items-po").appendChild(plantillaItemPO());

const NUMERICOS_PO = ["packing", "unit_price", "length", "width", "height", "gross_weight"];

$("#form-po").addEventListener("submit", (e) => {
  e.preventDefault();
  const form = e.target;

  const cajas = [...form.querySelectorAll("#items-po .item-row")];
  if (cajas.length === 0) {
    mostrarError("#res-po", "Agregue al menos una caja al detalle.");
    return;
  }

  const cabecera = {};
  ["consignee_code", "destination_port_code", "post_type", "warehouse_code", "po_number",
   "origin_port_code", "estimated_date", "comments", "accion"].forEach((campo) => {
    const valor = form.elements[campo]?.value.trim();
    if (valor) cabecera[campo] = valor;
  });

  const items = cajas.map((caja) => {
    const item = {};
    caja.querySelectorAll("input, select").forEach((campo) => {
      const valor = campo.value.trim();
      if (valor === "") return;
      item[campo.name] = NUMERICOS_PO.includes(campo.name) ? Number(valor) : valor;
    });
    return item;
  });

  ejecutar(form.querySelector('button[type="submit"]'), "#res-po", async () => {
    const res = await api.crearOrdenCompra({ ...cabecera, items });
    if (res.is_success) {
      mostrarMensaje("#res-po", "Orden de compra registrada correctamente en LAG.");
    } else {
      const detalle = res.errors.length
        ? res.errors.map((x) => `${x.poNumber}: ${x.message}`).join(" | ")
        : res.raw_response;
      mostrarError("#res-po", `LAG rechazo la orden. ${detalle}`);
    }
  });
});

// ---------- Ordenes de venta ----------
function plantillaCaja() {
  const div = document.createElement("div");
  div.className = "item-row";
  div.innerHTML = `
    <div class="form-grid">
      <div class="form-group"><label>Box ID (barcode) *</label><input name="boxId" required maxlength="16" /></div>
      <div class="form-group"><label>Precio unitario</label><input type="number" step="0.001" name="unitPrice" min="0" /></div>
      <div class="form-group"><label>Unidades</label><input type="number" name="units" min="0" /></div>
      <div class="form-group"><label>Mark Code</label><input name="markCode" maxlength="16" /></div>
    </div>
    <button type="button" class="btn btn-secondary btn-quitar">Quitar</button>`;
  div.querySelector(".btn-quitar").addEventListener("click", () => div.remove());
  return div;
}

$("#btn-add-box").addEventListener("click", () => $("#items-venta").appendChild(plantillaCaja()));
$("#items-venta").appendChild(plantillaCaja());

// LAG espera la fecha en formato MM/dd/yyyy; el input type=date entrega yyyy-MM-dd.
function aFormatoLag(fechaIso) {
  const [anio, mes, dia] = fechaIso.split("-");
  return `${mes}/${dia}/${anio}`;
}

$("#form-venta").addEventListener("submit", (e) => {
  e.preventDefault();
  const form = e.target;

  const cajas = [...form.querySelectorAll("#items-venta .item-row")];
  if (cajas.length === 0) {
    mostrarError("#res-venta", "Agregue al menos una caja.");
    return;
  }

  const payload = {
    customerId: form.elements.customerId.value.trim(),
    carrierId: form.elements.carrierId.value.trim(),
    shipDate: aFormatoLag(form.elements.shipDate.value),
    orderNumber: form.elements.orderNumber.value.trim(),
    idOrder: Number(form.elements.idOrder.value),
    boxIds: cajas.map((caja) => {
      const box = {};
      caja.querySelectorAll("input").forEach((campo) => {
        const valor = campo.value.trim();
        if (valor === "") return;
        box[campo.name] = ["unitPrice", "units"].includes(campo.name) ? Number(valor) : valor;
      });
      return box;
    }),
  };

  const poNumber = form.elements.poNumber.value.trim();
  if (poNumber) payload.poNumber = poNumber;

  const generateBOL = form.elements.generateBOL.value;
  if (generateBOL) payload.generateBOL = generateBOL === "true";

  ejecutar(form.querySelector('button[type="submit"]'), "#res-venta", async () => {
    const res = await api.crearOrdenVenta(payload);
    const detalle = res.error || JSON.stringify(res);
    if (String(res.status) === "1") {
      mostrarMensaje("#res-venta", detalle);
    } else {
      mostrarError("#res-venta", detalle);
    }
    if (Array.isArray(res.boxesNotAvailable) && res.boxesNotAvailable.length) {
      const p = document.createElement("p");
      p.className = "msg-info";
      p.textContent = `Cajas no disponibles: ${res.boxesNotAvailable.join(", ")}`;
      $("#res-venta").appendChild(p);
    }
  });
});

$("#form-cancelar").addEventListener("submit", (e) => {
  e.preventDefault();
  const idOrder = e.target.elements.idOrder.value;
  ejecutar(e.target.querySelector("button"), "#res-cancelar", async () => {
    const res = await api.cancelarOrdenVenta(idOrder);
    const detalle = res.error || JSON.stringify(res);
    if (String(res.status) === "1") {
      mostrarMensaje("#res-cancelar", detalle);
    } else {
      mostrarError("#res-cancelar", detalle);
    }
  });
});

// ---------- Posteo de Inventario (PlaceOrder/ordernew, sin ambiente de pruebas) ----------

const normalizarBusqueda = (s) =>
  (s || "").toString().normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

const escapeHtml = (s) =>
  (s || "").toString().replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// Combo buscable generico (input de texto + lista filtrada en vivo,
// navegable con flechas/Enter) para catalogos largos donde un <select>
// plano no se puede filtrar. Devuelve el estado (con .seleccionado) para
// poder leerlo despues, p.ej. al armar el mensaje de confirmacion.
function crearComboBuscable({ prefix, cargar, filtro, textoOpcion, valorOpcion, textoSeleccionado, etiquetaCarga }) {
  const estado = { items: [], seleccionado: null, resaltado: -1 };
  const input = document.getElementById(`${prefix}-search`);
  const hidden = document.getElementById(`${prefix}-value`);
  const cont = document.getElementById(`${prefix}-opciones`);
  const combo = document.getElementById(`${prefix}-combo`);

  async function cargarDatos() {
    try {
      const items = await cargar();
      estado.items = filtro(items);
      input.disabled = false;
      input.placeholder = `Escribe para buscar (${estado.items.length} ${etiquetaCarga})...`;
    } catch (err) {
      input.placeholder = `Error cargando ${etiquetaCarga}: ${err.message}`;
    }
  }

  function render(texto) {
    const norm = normalizarBusqueda(texto);
    const coincidencias = estado.items
      .filter((it) => !norm || normalizarBusqueda(textoOpcion(it)).includes(norm))
      .slice(0, 50);
    estado.resaltado = -1;
    cont.innerHTML = coincidencias.length
      ? coincidencias.map((it, i) => `<div class="combo-opcion" data-index="${i}">${escapeHtml(textoOpcion(it))}</div>`).join("")
      : `<div class="combo-vacio">Sin coincidencias</div>`;
    cont._coincidencias = coincidencias;
    cont.classList.add("abierto");
  }

  function seleccionar(item) {
    estado.seleccionado = item;
    input.value = textoSeleccionado(item);
    hidden.value = valorOpcion(item);
    cont.classList.remove("abierto");
  }

  input.addEventListener("input", () => {
    estado.seleccionado = null;
    hidden.value = "";
    render(input.value);
  });
  input.addEventListener("focus", () => render(input.value));
  cont.addEventListener("click", (e) => {
    const fila = e.target.closest(".combo-opcion");
    if (!fila) return;
    const item = cont._coincidencias[Number(fila.dataset.index)];
    if (item) seleccionar(item);
  });
  input.addEventListener("keydown", (e) => {
    const filas = cont.querySelectorAll(".combo-opcion");
    if (!filas.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      estado.resaltado = Math.min(estado.resaltado + 1, filas.length - 1);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      estado.resaltado = Math.max(estado.resaltado - 1, 0);
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (estado.resaltado >= 0) {
        const item = cont._coincidencias[estado.resaltado];
        if (item) seleccionar(item);
      }
      return;
    } else {
      return;
    }
    filas.forEach((f, i) => f.classList.toggle("resaltada", i === estado.resaltado));
  });
  document.addEventListener("click", (e) => {
    if (!combo.contains(e.target)) cont.classList.remove("abierto");
  });

  cargarDatos();
  return estado;
}

// El customerId de LAG viene de customers.customer_code_lag (verificado:
// siempre igual a customer_code cuando existe, 1,409 de 1,703 clientes lo
// tienen poblado). Solo se listan esos — postear con un customerId
// inventado fallaria contra LAG.
const comboCliente = crearComboBuscable({
  prefix: "posteo-customer",
  cargar: () => apiGet("/customers"),
  filtro: (clientes) => clientes.filter((c) => c.customer_code_lag).sort((a, b) => a.customer_name.localeCompare(b.customer_name)),
  textoOpcion: (c) => `${c.customer_name} (${c.customer_code_lag})`,
  textoSeleccionado: (c) => `${c.customer_name} (${c.customer_code_lag})`,
  valorOpcion: (c) => c.customer_code_lag,
  etiquetaCarga: "clientes",
});

// El carrierId viene de truck_company.id_logistic_carrier (catalogo de
// carriers de Miami, cargado desde "ID clientes.xlsx" hoja
// "Listado de Carriers-Miami").
const comboCarrier = crearComboBuscable({
  prefix: "posteo-carrier",
  cargar: () => apiGet("/truck-companies"),
  filtro: (carriers) => carriers,
  textoOpcion: (c) => c.sub_carrier_name && c.sub_carrier_name !== c.carrier_name
    ? `${c.carrier_name} - ${c.sub_carrier_name} (${c.id_logistic_carrier})`
    : `${c.carrier_name} (${c.id_logistic_carrier})`,
  textoSeleccionado: (c) => `${c.carrier_name} (${c.id_logistic_carrier})`,
  valorOpcion: (c) => c.id_logistic_carrier,
  etiquetaCarga: "carriers",
});

// Box ID = barcode de una pieza disponible en bodega (misma fuente que la
// pestana "Inventario", GET /inventario-lag/pieces). Se pide una sola vez
// y se comparte entre todas las filas de caja (cada fila tiene su propio
// combo, pero la lista de piezas es la misma).
let piezasDisponiblesPromise = null;
function obtenerPiezasDisponibles() {
  if (!piezasDisponiblesPromise) {
    piezasDisponiblesPromise = apiGet("/inventario-lag/pieces").then((r) => r.piezas || []);
  }
  return piezasDisponiblesPromise;
}

let contadorCajaPosteo = 0;

function plantillaCajaPosteo() {
  const idx = contadorCajaPosteo++;
  const prefix = `posteo-box-${idx}`;
  const div = document.createElement("div");
  div.className = "item-row";
  div.innerHTML = `
    <div class="form-grid">
      <div class="form-group">
        <label>Box ID (pieza en bodega) *</label>
        <div class="combo-buscable" id="${prefix}-combo">
          <input type="text" id="${prefix}-search" placeholder="Cargando piezas..." autocomplete="off" disabled />
          <input type="hidden" name="boxId" id="${prefix}-value" />
          <div class="combo-opciones" id="${prefix}-opciones"></div>
        </div>
      </div>
      <div class="form-group"><label>Stem Price</label><input type="number" step="0.01" name="stemPrice" min="0" /></div>
    </div>
    <button type="button" class="btn btn-secondary btn-quitar">Quitar</button>`;
  div.querySelector(".btn-quitar").addEventListener("click", () => div.remove());

  crearComboBuscable({
    prefix,
    cargar: obtenerPiezasDisponibles,
    filtro: (piezas) => piezas,
    textoOpcion: (p) => `${p.barcode} (Rack: ${p.rack})`,
    textoSeleccionado: (p) => `${p.barcode} (Rack: ${p.rack})`,
    valorOpcion: (p) => p.barcode,
    etiquetaCarga: "piezas",
  });

  return div;
}

$("#btn-add-box-posteo").addEventListener("click", () => $("#items-posteo").appendChild(plantillaCajaPosteo()));
$("#items-posteo").appendChild(plantillaCajaPosteo());

// LAG espera miamiShipDate en MM/dd/yyyy; el input type=date entrega yyyy-MM-dd.
$("#form-posteo").addEventListener("submit", (e) => {
  e.preventDefault();
  const form = e.target;

  if (!form.elements.customerId.value) {
    mostrarError("#res-posteo", "Selecciona un cliente de la lista.");
    return;
  }
  if (!form.elements.carrierId.value) {
    mostrarError("#res-posteo", "Selecciona un carrier de la lista.");
    return;
  }

  const cajas = [...form.querySelectorAll("#items-posteo .item-row")];
  if (cajas.length === 0) {
    mostrarError("#res-posteo", "Agregue al menos una caja.");
    return;
  }

  const boxIdsVacios = cajas.some((caja) => !caja.querySelector('[name="boxId"]').value.trim());
  if (boxIdsVacios) {
    mostrarError("#res-posteo", "Selecciona un Box ID (pieza en bodega) para cada caja.");
    return;
  }

  const boxIds = cajas.map((caja) => {
    const box = { boxId: caja.querySelector('[name="boxId"]').value.trim() };
    const stemPrice = caja.querySelector('[name="stemPrice"]').value.trim();
    if (stemPrice !== "") box.stemPrice = Number(stemPrice);
    return box;
  });

  const payload = {
    customerId: form.elements.customerId.value.trim(),
    carrierId: form.elements.carrierId.value.trim(),
    miamiShipDate: aFormatoLag(form.elements.miamiShipDate.value),
    printWmsLabels: form.elements.printWmsLabels.value === "true",
    boxIds,
  };

  const nombreCliente = comboCliente.seleccionado
    ? `${comboCliente.seleccionado.customer_name} (${payload.customerId})`
    : payload.customerId;
  const nombreCarrier = comboCarrier.seleccionado
    ? `${comboCarrier.seleccionado.carrier_name} (${payload.carrierId})`
    : payload.carrierId;
  const confirmado = window.confirm(
    `Esto crea una orden REAL en el WMS de LAG (sin ambiente de pruebas).\n\n` +
    `Cliente: ${nombreCliente}\nCarrier: ${nombreCarrier}\nFecha: ${payload.miamiShipDate}\n` +
    `Cajas: ${boxIds.map((b) => b.boxId).join(", ")}\n\n¿Confirmas el envío?`
  );
  if (!confirmado) return;

  ejecutar(form.querySelector('button[type="submit"]'), "#res-posteo", async () => {
    const res = await api.postearInventario(payload);
    mostrarMensaje("#res-posteo", `Respuesta de LAG:\n${res.raw_response}`);
  });
});
```

### pages/torre-control.html + .js (Fase 3)

`frontend/pages/torre-control.html`
```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>BLIS · Torre de Control</title>
  <link rel="stylesheet" href="/css/styles.css" />
</head>
<body data-page="torre-control">
  <div id="sidebar" class="sidebar"></div>

  <main class="content" id="content">
    <div class="page-header">
      <h1><i class="ph ph-radar"></i> Torre de Control</h1>
      <p class="page-subtitle">Concilia las cajas de dartis_ventas contra los manifiestos de UPS, FedEx y agencias locales.</p>
    </div>

    <div class="import-card">
      <div class="import-actions" style="justify-content: flex-start; gap: .75rem; flex-wrap: wrap;">
        <button id="btnRefrescar" class="btn btn-primary"><i class="ph ph-arrows-clockwise"></i> Actualizar ahora</button>
        <button id="btnDuoplane" class="btn btn-secondary"><i class="ph ph-package"></i> Sincronizar Duoplane</button>
        <label class="btn btn-secondary" style="cursor:pointer;">
          <i class="ph ph-upload-simple"></i> Subir manifiesto UPS (.csv)
          <input type="file" id="fileUps" accept=".csv" style="display:none;" />
        </label>
        <label class="btn btn-secondary" style="cursor:pointer;">
          <i class="ph ph-upload-simple"></i> Subir manifiesto FedEx (.pdf)
          <input type="file" id="fileFedex" accept=".pdf" style="display:none;" />
        </label>
        <span id="actualizado" class="page-subtitle"></span>
      </div>
      <div id="resultado" class="resultado"></div>
    </div>

    <div class="card-grid" id="kpis" style="margin-top: 1.5rem;">
      <div class="summary-card"><span class="summary-card-value" id="kpi-guias">0</span><span class="summary-card-label">Facturas</span></div>
      <div class="summary-card"><span class="summary-card-value" id="kpi-ok">0</span><span class="summary-card-label">OK</span></div>
      <div class="summary-card"><span class="summary-card-value" id="kpi-discrepancias">0</span><span class="summary-card-label">Discrepancias</span></div>
      <div class="summary-card"><span class="summary-card-value" id="kpi-pendientes">0</span><span class="summary-card-label">Pendientes</span></div>
      <div class="summary-card"><span class="summary-card-value" id="kpi-sin-manifiesto">0</span><span class="summary-card-label">Sin manifiesto</span></div>
      <div class="summary-card"><span class="summary-card-value" id="kpi-no-en-dartis">0</span><span class="summary-card-label">No en Dartis</span></div>
    </div>

    <nav class="subtabs" style="margin-top: 1.5rem;">
      <button class="subtab active" data-tab="principal">Principal (UPS / FedEx)</button>
      <button class="subtab" data-tab="locales">Agencias locales</button>
    </nav>

    <section id="panel-principal" class="subpanel active">
      <div class="import-card">
        <div class="form-grid">
          <div class="form-group">
            <label>Estado</label>
            <select id="filtroEstado">
              <option value="">Todos</option>
              <option value="OK">OK</option>
              <option value="DISCREPANCIA">Discrepancia</option>
              <option value="SIN MANIFIESTO">Sin manifiesto</option>
              <option value="NO EN DARTIS">No en Dartis</option>
            </select>
          </div>
          <div class="form-group">
            <label>Courier</label>
            <select id="filtroCourier">
              <option value="">Ambos</option>
              <option value="UPS">UPS</option>
              <option value="FEDEX">FedEx</option>
            </select>
          </div>
          <div class="form-group">
            <label>Buscar</label>
            <input type="search" id="filtroBuscar" placeholder="factura, cliente, tracking..." />
          </div>
        </div>
        <table class="data-table">
          <thead>
            <tr>
              <th>Factura</th><th>Courier</th><th>Empresa</th><th>Cliente</th>
              <th>Cajas Dartis</th><th>Manifiesto</th><th>Diferencia</th>
              <th>Estado vivo</th><th>Ubicación</th><th>Conciliación</th>
            </tr>
          </thead>
          <tbody id="tablaPrincipal"><tr><td colspan="10" class="loading">Cargando...</td></tr></tbody>
        </table>
      </div>
    </section>

    <section id="panel-locales" class="subpanel">
      <div class="import-card">
        <div class="form-grid">
          <div class="form-group">
            <label>Estado</label>
            <select id="filtroEstadoLocal">
              <option value="">Todos</option>
              <option value="OK">OK</option>
              <option value="PENDIENTE">Pendiente</option>
            </select>
          </div>
          <div class="form-group">
            <label>Buscar</label>
            <input type="search" id="filtroBuscarLocal" placeholder="factura, agencia, cliente..." />
          </div>
        </div>
        <table class="data-table">
          <thead>
            <tr>
              <th>Factura</th><th>Agencia</th><th>Empresa</th><th>Cliente</th>
              <th>Fecha Dartis</th><th>Cajas</th><th>Entrega real</th><th>Conciliación</th>
            </tr>
          </thead>
          <tbody id="tablaLocales"><tr><td colspan="8" class="loading">Cargando...</td></tr></tbody>
        </table>
      </div>
    </section>
  </main>

  <script type="module" src="/js/layout.js"></script>
  <script type="module" src="/pages/torre-control.js"></script>
</body>
</html>
```

`frontend/pages/torre-control.js`
```javascript
import { apiGet, apiPost } from "/js/api.js";

const BADGE = {
  OK: "badge-green",
  DISCREPANCIA: "badge-red",
  PENDIENTE: "badge-gray",
  "SIN MANIFIESTO": "badge-orange",
  "NO EN DARTIS": "badge-red",
};

let snapshot = { cajas: [], resumen: {} };

const $ = (sel) => document.querySelector(sel);

// ---------- Sub-pestanas ----------
document.querySelectorAll(".subtab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".subtab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".subpanel").forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    $(`#panel-${tab.dataset.tab}`).classList.add("active");
  });
});

// ---------- Carga de datos ----------
async function cargarEstado() {
  snapshot = await apiGet("/torre-control/estado");
  renderKpis();
  renderTablaPrincipal();
  renderTablaLocales();
  if (snapshot.actualizado) {
    $("#actualizado").textContent = `Actualizado ${new Date(snapshot.actualizado).toLocaleString("es-EC")}`;
  }
}

function renderKpis() {
  const t = snapshot.resumen?.total || {};
  $("#kpi-guias").textContent = t.guias ?? 0;
  $("#kpi-ok").textContent = t.ok ?? 0;
  $("#kpi-discrepancias").textContent = t.discrepancias ?? 0;
  $("#kpi-pendientes").textContent = t.pendientes ?? 0;
  $("#kpi-sin-manifiesto").textContent = t.sin_manifiesto ?? 0;
  $("#kpi-no-en-dartis").textContent = t.no_en_dartis ?? 0;
}

function renderTablaPrincipal() {
  const estado = $("#filtroEstado").value;
  const courier = $("#filtroCourier").value;
  const texto = $("#filtroBuscar").value.trim().toLowerCase();

  const filas = snapshot.cajas.filter((c) => {
    if (!["UPS", "FEDEX"].includes(c.courier)) return false;
    if (estado && c.conciliacion !== estado) return false;
    if (courier && c.courier !== courier) return false;
    if (texto) {
      const heno = `${c.factura} ${c.cliente || ""} ${c.empresa || ""} ${c.tracking || ""}`.toLowerCase();
      if (!heno.includes(texto)) return false;
    }
    return true;
  });

  const tbody = $("#tablaPrincipal");
  if (!filas.length) {
    tbody.innerHTML = `<tr><td colspan="10" class="empty">Sin resultados</td></tr>`;
    return;
  }
  tbody.innerHTML = filas.slice(0, 500).map((c) => `
    <tr>
      <td>${c.factura}</td>
      <td>${c.courier}</td>
      <td>${c.empresa || ""}</td>
      <td>${c.cliente || ""}</td>
      <td>${c.cajas_dartis ?? ""}</td>
      <td>${c.bultos_csv ?? c.cajas_manifiesto ?? "-"}</td>
      <td>${c.diferencia ?? "-"}</td>
      <td>${c.estado_vivo || ""}</td>
      <td>${c.ubicacion || ""}</td>
      <td><span class="badge ${BADGE[c.conciliacion] || "badge-gray"}">${c.conciliacion}</span></td>
    </tr>
  `).join("");
  if (filas.length > 500) {
    tbody.innerHTML += `<tr><td colspan="10" class="conteo">Mostrando 500 de ${filas.length} — afina el filtro para ver el resto.</td></tr>`;
  }
}

function renderTablaLocales() {
  const estado = $("#filtroEstadoLocal").value;
  const texto = $("#filtroBuscarLocal").value.trim().toLowerCase();

  const filas = snapshot.cajas.filter((c) => {
    if (["UPS", "FEDEX"].includes(c.courier)) return false;
    if (estado && c.conciliacion !== estado) return false;
    if (texto) {
      const heno = `${c.factura} ${c.courier_raw || ""} ${c.cliente || ""} ${c.empresa || ""}`.toLowerCase();
      if (!heno.includes(texto)) return false;
    }
    return true;
  });

  const tbody = $("#tablaLocales");
  if (!filas.length) {
    tbody.innerHTML = `<tr><td colspan="8" class="empty">Sin resultados</td></tr>`;
    return;
  }
  tbody.innerHTML = filas.slice(0, 500).map((c) => `
    <tr>
      <td>${c.factura}</td>
      <td>${c.courier_raw || ""}</td>
      <td>${c.empresa || ""}</td>
      <td>${c.cliente || ""}</td>
      <td>${c.fecha_dartis || ""}</td>
      <td>${c.cajas_dartis ?? ""}</td>
      <td>${c.fecha_entrega_real || "-"}</td>
      <td><span class="badge ${BADGE[c.conciliacion] || "badge-gray"}">${c.conciliacion}</span></td>
    </tr>
  `).join("");
  if (filas.length > 500) {
    tbody.innerHTML += `<tr><td colspan="8" class="conteo">Mostrando 500 de ${filas.length} — afina el filtro para ver el resto.</td></tr>`;
  }
}

["filtroEstado", "filtroCourier", "filtroBuscar"].forEach((id) =>
  $(`#${id}`).addEventListener("input", renderTablaPrincipal)
);
["filtroEstadoLocal", "filtroBuscarLocal"].forEach((id) =>
  $(`#${id}`).addEventListener("input", renderTablaLocales)
);

// ---------- Acciones ----------
function mostrarResultado(msg, clase = "msg-ok") {
  $("#resultado").innerHTML = `<p class="${clase}">${msg}</p>`;
}

$("#btnRefrescar").addEventListener("click", async () => {
  const btn = $("#btnRefrescar");
  btn.disabled = true;
  mostrarResultado("Actualizando (dartis_ventas + manifiestos + tracking en vivo)...", "msg-info");
  try {
    const r = await apiPost("/torre-control/refrescar", {});
    mostrarResultado(`Actualizado: ${r.total_facturas} facturas procesadas.`);
    await cargarEstado();
  } catch (err) {
    mostrarResultado(err.message, "msg-error");
  } finally {
    btn.disabled = false;
  }
});

$("#btnDuoplane").addEventListener("click", async () => {
  const btn = $("#btnDuoplane");
  btn.disabled = true;
  mostrarResultado("Sincronizando con Duoplane...", "msg-info");
  try {
    const r = await apiPost("/torre-control/sincronizar-duoplane", {});
    if (!r.ok) {
      mostrarResultado(r.error, "msg-error");
    } else {
      mostrarResultado(`Duoplane: ${r.revisadas} POs revisadas, ${r.creados.length} shipments creados, ${r.pendientes.length} pendientes, ${r.errores.length} errores.`);
    }
  } catch (err) {
    mostrarResultado(err.message, "msg-error");
  } finally {
    btn.disabled = false;
  }
});

async function subirArchivo(input, path) {
  const file = input.files[0];
  if (!file) return;
  mostrarResultado(`Subiendo ${file.name}...`, "msg-info");
  const form = new FormData();
  form.append("archivo", file);
  try {
    const res = await fetch(`/api${path}`, { method: "POST", body: form });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Error al subir el archivo");
    mostrarResultado(`${file.name}: ${JSON.stringify(data)}`);
    await cargarEstado();
  } catch (err) {
    mostrarResultado(err.message, "msg-error");
  } finally {
    input.value = "";
  }
}

$("#fileUps").addEventListener("change", (e) => subirArchivo(e.target, "/torre-control/subir-ups"));
$("#fileFedex").addEventListener("change", (e) => subirArchivo(e.target, "/torre-control/subir-fedex"));

cargarEstado();
```

### pages/auditoria-etiquetas.html + .js (Fase 4) — dashboard de solo lectura, la carga de datos es vía Telegram

`frontend/pages/auditoria-etiquetas.html`
```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>BLIS · Auditoría de Etiquetas</title>
  <link rel="stylesheet" href="/css/styles.css" />
</head>
<body data-page="auditoria-etiquetas">
  <div id="sidebar" class="sidebar"></div>

  <main class="content" id="content">
    <div class="page-header">
      <h1><i class="ph ph-clipboard-text"></i> Auditoría de Etiquetas Especiales</h1>
      <p class="page-subtitle">Despachos de clientes especiales y su auditoría física, vía el bot de Telegram del auditor de poscosecha.</p>
    </div>

    <div class="import-card">
      <div class="import-actions" style="justify-content: flex-start; gap: .75rem;">
        <button id="btnGenerar" class="btn btn-primary"><i class="ph ph-arrows-clockwise"></i> Generar despachos de hoy</button>
        <span id="actualizado" class="page-subtitle"></span>
      </div>
      <div id="resultado" class="resultado"></div>
    </div>

    <div class="card-grid" id="kpis" style="margin-top: 1.5rem;">
      <div class="summary-card"><span class="summary-card-value" id="kpi-total">0</span><span class="summary-card-label">Despachos hoy</span></div>
      <div class="summary-card"><span class="summary-card-value" id="kpi-auditados">0</span><span class="summary-card-label">Auditados</span></div>
      <div class="summary-card"><span class="summary-card-value" id="kpi-pendientes">0</span><span class="summary-card-label">Pendientes</span></div>
    </div>

    <div class="import-card" style="margin-top: 1.5rem;">
      <h3>Despachos de hoy</h3>
      <table class="data-table">
        <thead>
          <tr><th>Poscosecha</th><th>Cliente</th><th>Guía madre</th><th>Guía hija</th><th>Cajas</th><th>Tipo caja</th><th>Estado</th></tr>
        </thead>
        <tbody id="tablaDespachos"><tr><td colspan="7" class="loading">Cargando...</td></tr></tbody>
      </table>
    </div>

    <div class="import-card" style="margin-top: 1.5rem;">
      <h3>Auditorías registradas hoy</h3>
      <table class="data-table">
        <thead>
          <tr><th>Hora</th><th>Auditor</th><th>Cliente</th><th>Cajas</th><th>Piezas</th><th>Tipo caja OK</th><th>Especie OK</th><th>Etiqueta OK</th><th>Observaciones</th><th>Foto</th></tr>
        </thead>
        <tbody id="tablaAuditorias"><tr><td colspan="10" class="loading">Cargando...</td></tr></tbody>
      </table>
    </div>
  </main>

  <script type="module" src="/js/layout.js"></script>
  <script type="module" src="/pages/auditoria-etiquetas.js"></script>
</body>
</html>
```

`frontend/pages/auditoria-etiquetas.js`
```javascript
import { apiGet, apiPost } from "/js/api.js";

const $ = (sel) => document.querySelector(sel);

function badgeSiNo(v) {
  if (v === true) return `<span class="badge badge-green">Sí</span>`;
  if (v === false) return `<span class="badge badge-red">No</span>`;
  return "-";
}

async function cargar() {
  const [despachos, auditorias] = await Promise.all([
    apiGet("/auditoria-etiquetas/despachos"),
    apiGet("/auditoria-etiquetas/auditorias"),
  ]);
  renderKpis(despachos);
  renderDespachos(despachos);
  renderAuditorias(auditorias);
  $("#actualizado").textContent = `Actualizado ${new Date().toLocaleString("es-EC")}`;
}

function renderKpis(despachos) {
  const total = despachos.length;
  const auditados = despachos.filter((d) => d.estado === "AUDITADO").length;
  $("#kpi-total").textContent = total;
  $("#kpi-auditados").textContent = auditados;
  $("#kpi-pendientes").textContent = total - auditados;
}

function renderDespachos(despachos) {
  const tbody = $("#tablaDespachos");
  if (!despachos.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty">Sin despachos hoy. Usa "Generar despachos de hoy" o espera a que el bot los cree con /lista.</td></tr>`;
    return;
  }
  tbody.innerHTML = despachos.map((d) => `
    <tr>
      <td>${d.postcosecha || ""}</td>
      <td>${d.cliente || ""}</td>
      <td>${d.guia_madre || ""}</td>
      <td>${d.guia_hija || ""}</td>
      <td>${d.cajas ?? ""}</td>
      <td>${d.tipo_caja || ""}</td>
      <td><span class="badge ${d.estado === "AUDITADO" ? "badge-green" : "badge-gray"}">${d.estado}</span></td>
    </tr>
  `).join("");
}

function renderAuditorias(auditorias) {
  const tbody = $("#tablaAuditorias");
  if (!auditorias.length) {
    tbody.innerHTML = `<tr><td colspan="10" class="empty">Sin auditorías registradas hoy.</td></tr>`;
    return;
  }
  tbody.innerHTML = auditorias.map((a) => `
    <tr>
      <td>${new Date(a.fecha_hora).toLocaleTimeString("es-EC")}</td>
      <td>${a.auditor || ""}</td>
      <td>${a.cliente || ""}</td>
      <td>${a.cajas_despachadas ?? ""}</td>
      <td>${a.piezas_despachadas ?? ""}</td>
      <td>${badgeSiNo(a.tipo_caja_ok)}</td>
      <td>${badgeSiNo(a.especie_ok)}</td>
      <td>${badgeSiNo(a.etiqueta_ok)}</td>
      <td>${a.observaciones || ""}</td>
      <td>${a.foto_url ? `<a href="${a.foto_url}" target="_blank" rel="noopener">Ver foto</a>` : "-"}</td>
    </tr>
  `).join("");
}

$("#btnGenerar").addEventListener("click", async () => {
  const btn = $("#btnGenerar");
  btn.disabled = true;
  $("#resultado").innerHTML = `<p class="msg-info">Generando despachos desde dartis_ventas...</p>`;
  try {
    const r = await apiPost("/auditoria-etiquetas/despachos/generar", {});
    $("#resultado").innerHTML = `<p class="msg-ok">${r.encontrados} facturas de clientes especiales encontradas, ${r.insertados} despachos nuevos creados.</p>`;
    await cargar();
  } catch (err) {
    $("#resultado").innerHTML = `<p class="msg-error">${err.message}</p>`;
  } finally {
    btn.disabled = false;
  }
});

cargar();
```

---

## 17. Base de datos — tablas y relaciones

51 tablas en el esquema `public` de Supabase (`kgpzhwocygonppblgmpm`). Conteo de filas verificado en vivo, agosto 2026.

### Tablas del núcleo original

| Tabla | Filas | Campos principales |
|---|---|---|
| `species` | 101 | id (UUID), code, name, active, name_agrocalidad |
| `varieties` | 870 | id, species_id (FK), code, name, active |
| `product_sizes` | 140 | id, species_id (FK), size_code, description, active |
| `box_types` | 12 | id, box_code, box_name, length_cm, width_cm, height_cm |
| `airports` | 37 | id, iata_code, airport_name, city, country_id (FK) |
| `countries` | 255 | id, code, name, name_es, market_id |
| `airlines` | 8 | id, airline_code, airline_name, active |
| `airline_tariffs` | 8 | id, airline_id, origin/destination_airport_id (FK), cost_per_kg |
| `cargo_agencies` | 34 | id, code, name, dartis_name, ocr_variants (TEXT[]), type |
| `customers` | 1,703 | id, customer_code, customer_name, dartis_name, destinatario, **es_cliente_especial** (Fase 4) |
| `farms` / `farm_postcosecha` | 3 / 6 | id, code, name, dartis_postcosecha |
| `dartis_ventas` | 20,888 | fecha, dae, id_pedido, empresa, cliente, customer_id (FK), destinatario, postcosecha, especie, guia_madre, guia_hija, tipo_caja, total_piezas, total_tallos, total_dolares, vendedor, agencia_carga |
| `roles` / `profiles` | 0 / 0 | auth pendiente |
| `markets`, `providers`, `incoterms`, `cost_components`, `currencies`, `exchange_rates` | 2/3/4/16/2/1 | catálogos de costeo |
| `scenario_headers/details/cost_results` | 1/1/5 | Costing Engine |
| `_migrations` | 14 | control de migraciones aplicadas |

**Clave única en `dartis_ventas`** (corregida en esta sesión — ver §22):
```sql
UNIQUE (id_pedido, guia_madre, guia_hija, tipo_caja, especie)
```

### Tablas de los módulos clonados (Fases 1-4)

| Tabla | Filas | Módulo | Descripción |
|---|---|---|---|
| `agrocalidad_requests` | 44 | Agrocalidad | cola de solicitudes de scraping (pending/processing/done/error) |
| `agrocalidad_requirements` | 196 | Agrocalidad | resultados: requisitos fitosanitarios por especie+país+trámite+área |
| `courier_ups_manifest` | 876 | Torre de Control | bultos del manifiesto UPS subido (se trunca/reinserta en cada subida) |
| `courier_fedex_envios` | 0 | Torre de Control | acumulador de envíos FedEx (upsert por tracking) |
| `courier_agency_mapping` | 90 | Torre de Control | mapeo agencia-local-en-Sheet → nombre canónico Dartis (solo confianza "alta") |
| `courier_reconciliation` | 10,775 | Torre de Control | snapshot calculado de la conciliación, persistido en cada refresco |
| `courier_bot_log` | 0 | Torre de Control | bitácora reservada para la Fase 3b (bot RPA, no implementada) |
| `special_dispatches` | 73 | Auditoría de Etiquetas | despachos de clientes especiales generados desde `dartis_ventas` |
| `special_dispatch_audits` | 0 | Auditoría de Etiquetas | auditorías registradas por el bot de Telegram |
| `telegram_conversation_state` | 0 | Auditoría de Etiquetas | estado de conversación del bot (reemplaza CacheService de Apps Script) |
| `truck_company` | 139 | Inventario LAG (Posteo) | catálogo de carriers de Miami, sembrado desde `ID clientes.xlsx` hoja "Listado de Carriers-Miami"; `id_logistic_carrier` es el valor real que se envía a LAG |

Inventario LAG (Fase 2) en sí no tiene tabla propia — es 100% proxy en vivo sobre las APIs de Logiztik Alliance Group. `truck_company` es la única excepción, agregada para la sub-pestaña "Posteo de Inventario".

---

## 18. Migraciones aplicadas

Todas en `database/migrations/`, aplicadas directo en Supabase (no vía Alembic — el proyecto lo tiene en requirements pero no está en uso activo).

| # | Archivo | Qué hace |
|---|---|---|
| 002 | `cargo_agencies.sql` | Tabla maestra de agencias de carga, normaliza nombres OCR del bot de Telegram |
| 003 | `farms.sql` | Tabla maestra de fincas/exportadoras, vincula con código postcosecha de Dartis |
| 004 | `cargo_agencies_dartis.sql` | Agrega `dartis_name` a `cargo_agencies`, sincroniza con `agenciaCarga` real de Dartis |
| 005 | `farm_postcosecha.sql` | Tabla de códigos postcosecha vinculados a fincas (una finca puede tener varias) |
| 006 | `cargo_agencies_reset.sql` | Reconstruye `cargo_agencies` con nombres exactos de Dartis como referencia oficial |
| 007 | `farm_postcosecha_amazing_bfexpoflor.sql` | Agrega postcosechas AMAZING y BF-EXPOFLOR detectadas en Dartis |
| 008 | `dartis_ventas_recetas.sql` | Tabla única `dartis_ventas` basada en formato Ventas Recetas (reemplaza la anterior) |
| 009 | `dartis_ventas_vendedor.sql` | Agrega columna `vendedor` (viene del formato Ventas clásico, no de Recetas) |
| 010 | `dartis_ventas_agencia_carga.sql` | Agrega columna `agencia_carga`, cruzada por `id_pedido` con Ventas clásico |
| 011 | `customers_destinatario.sql` | Agrega `destinatario` a `customers` (quien recibe físicamente vs. quien compra) |
| 012 | `customers_code_lag.sql` | Agrega `customer_code_lag`, código de cliente en el sistema de Alianza Logistika |
| 013 | `customers_seed.sql` | Carga inicial de clientes activos desde `ID clientes.xlsx` |
| 014 | `customers_dartis_name.sql` | Agrega `dartis_name` a `customers` — nombre exacto como aparece en Dartis ERP |
| 015 | `customers_destinatarios.sql` | Puebla `destinatario` y crea registros de destinatarios distintos desde `dartis_ventas` |
| 016 | `dartis_ventas_especie_unique.sql` | **Corrige el bug crítico de pérdida de datos** — agrega `especie` a la clave única (ver §22) |
| 017 | `courier_reconciliation.sql` | Tablas de Torre de Control + semilla de `courier_agency_mapping` (90 filas de confianza alta) |
| 018 | `customers_cliente_especial.sql` | Agrega `es_cliente_especial` a `customers` (reemplaza tabla externa de Auditoria_LEsp) |
| 019 | `auditoria_etiquetas.sql` | Tablas de Auditoría de Etiquetas (`special_dispatches`, `special_dispatch_audits`, `telegram_conversation_state`) |
| 020 | `truck_company.sql` | Tabla `truck_company` (catálogo de carriers de Miami) + seed de 139 filas reales desde `ID clientes.xlsx`, para el campo Carrier de "Posteo de Inventario" |

---

## 19. Despliegue en Render.com

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

Render → BLIS → **Environment** → Add Environment Variable. Ver la lista completa en §4 — todas las variables de las Fases 1-4 deben agregarse ahí manualmente (siguen sin configurar en Render al cierre de esta ronda; los módulos nuevos corren en modo degradado/demo hasta entonces).

### Errores resueltos durante el deploy

| Error | Causa | Solución aplicada |
|---|---|---|
| `ModuleNotFoundError: No module named 'app'` | uvicorn corría desde raíz del repo | Start command: `cd backend && uvicorn ...` |
| `Could not parse SQLAlchemy URL` | `DATABASE_URL` no configurada en Render | Agregar variable en Environment |
| `Form data requires python-multipart` | Paquete faltante en requirements | Agregar `python-multipart` al `backend/requirements.txt` + Clear cache & deploy |
| Deploy usaba cache viejo | Render cachea paquetes pip | Manual Deploy → ▼ → **Clear build cache & deploy** |
| `We are unable to access your GitHub repository` | Repo privado | Cambiar a público temporalmente → conectar → volver a privado |

---

## 20. Desarrollo local — paso a paso

```powershell
# 1. Clonar
git clone https://github.com/freddyerazo/BellaflorLogis.git
cd BellaflorLogis

# 2. Entorno virtual — FUERA de OneDrive (ver Deuda técnica en CLAUDE.md).
#    Crearlo dentro del repo lo rompe: OneDrive deshidrata los archivos.
python -m venv C:\dev\venvs\blis

# 3. Dependencias
C:\dev\venvs\blis\Scripts\python.exe -m pip install -r backend\requirements.txt

# 4. Variables de entorno (crear backend/.env, ver §4 para la lista completa)

# 5. Iniciar (desde la raíz del repo)
.\scripts\dev.ps1
```

La aplicación estará disponible en `http://localhost:8000`. El frontend se sirve como archivos estáticos desde `../frontend/`:
```python
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
```

Verificación:
```
GET /health                          → {"status":"ok","system":"BLIS"}
GET /db-test                         → {"status":"connected","database_time":"..."}
GET /api/agrocalidad/catalogo        → especies/países disponibles
GET /api/inventario-lag/health       → {"status":"ok","lag_env":"test"}
GET /api/torre-control/estado        → snapshot de conciliación (arranca solo, via scheduler de startup)
GET /api/auditoria-etiquetas/despachos → despachos del día
```

---

## 21. GitHub

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
git status
git add <archivo>
git commit -m "descripcion del cambio"
git push origin main   # dispara autodeploy en Render
```

---

## 22. Troubleshooting

### Bug crítico corregido: pérdida silenciosa de datos en dartis_ventas

**Síntoma**: la clave única de `dartis_ventas` era `(id_pedido, guia_madre, guia_hija, tipo_caja)` — sin `especie`. Una misma guía/caja transporta legítimamente varias especies (una "receta" combina flores distintas en una caja), así que al importar solo sobrevivía la última especie del archivo por guía; las demás se descartaban en silencio.

**Magnitud**: de 20,917 líneas válidas del reporte Dartis, 8,676 (41.5%) se perdían. Un pedido real verificado: 3 especies por $13.20+$19.00+$7.60=$39.80, pero en la base solo quedaba 1 línea de $7.60.

**Corrección** (migración 016 + `dartis_import.py`): se agregó `especie` a la clave única; el dedup en Python ahora suma cantidades cuando dos líneas comparten la clave completa (lotes separados del mismo producto) en vez de sobrescribir. Reimportado: 12,269 → 20,888 filas, +$217,339.62 en `total_dolares` recuperados.

Esta corrección fue la base que permitió que las Fases 1-4 (especialmente Torre de Control y Auditoría de Etiquetas) pudieran leer `dartis_ventas` directo como tabla base, sin necesitar sus propios archivos de ventas.

### Bug de rendimiento: insertar fila por fila en bulk imports

**Síntoma**: `courier_reconciliation._persistir()` y el endpoint `/subir-ups` de Torre de Control insertaban una fila a la vez en un loop de Python. Con ~10,700-11,000 filas y ~200ms de latencia por round-trip a Supabase (medido en pruebas), esto tardaba **~38 minutos** — el servidor parecía colgado al arrancar (`Waiting for application startup` indefinido).

**Corrección**: reemplazado por `execute_values` de `psycopg2.extras` (bulk insert en un solo round-trip por lote de 1000), el mismo patrón que ya usaba `dartis_import.py`. Un refresco completo de Torre de Control pasó de ~38 min a ~12-16s.

### Bug menor: columna mal escrita

`special_dispatches.py` tenía `ORDER BY poscosecha` en dos consultas — la columna real es `postcosecha`. Encontrado y corregido en pruebas antes de desplegar.

### Riesgo operativo: Posteo de Inventario no tiene ambiente de pruebas

El endpoint legacy de LAG usado por "Posteo de Inventario" (`PlaceOrder/ordernew`, host `cloudus.logiztikalliance.com:5005`) **no tiene sandbox** — el token configurado en `LAG_PLACE_ORDER_TOKEN` es de producción real, sin excepción. Por eso el formulario en `inventario-lag.js` exige confirmación explícita (`window.confirm`) antes de cada envío, mostrando cliente/carrier/fecha/cajas.

**Pendiente de seguridad**: el token real (`LoMi0-G6pR6sr8aFd`) fue pegado en texto plano durante esta sesión de trabajo — se recomienda **rotarlo** con Logiztik Alliance Group antes de considerar el posteo listo para uso diario, y configurar el nuevo valor únicamente en `backend/.env` / Render → Environment (nunca en el repo).

### Backend

| Problema | Causa probable | Solución |
|---|---|---|
| `ModuleNotFoundError: No module named 'app'` | uvicorn no está en `backend/` | `cd backend` antes de uvicorn |
| `Could not parse SQLAlchemy URL` | `DATABASE_URL` vacía | Verificar `.env` o variable en Render |
| `Form data requires python-multipart` | Paquete no instalado | `pip install python-multipart` |
| Import Dartis cuelga | Código síncrono en endpoint async | Usar `run_in_executor` (ya implementado) |
| `ON CONFLICT command cannot affect row a second time` | Duplicados en el Excel con misma clave | Deduplicar con dict Python antes del bulk insert (ya implementado) |
| Un refresco/import tarda minutos con volúmenes grandes | Insert fila por fila en un loop | Usar `execute_values` (bulk insert) — ver arriba |
| GAS no responde en 120s | Cold start de GAS | Normal en primera carga del día — reintentar |
| Torre de Control muestra todo "SIN MANIFIESTO"/"PENDIENTE" | No se ha subido el manifiesto UPS/FedEx del día | Subir el CSV/PDF desde la pestaña, o esperar credenciales reales (`DEMO_MODE=false`) |
| Auditoría de Etiquetas no muestra despachos | No hay ventas de clientes especiales para la fecha, o `es_cliente_especial` no está marcado en `customers` | Usar el botón "Generar despachos de hoy"; revisar `customers.es_cliente_especial` |

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
| Módulo nuevo responde con datos vacíos/demo | Faltan variables de entorno del módulo (ver §4) — no es un bug, es config pendiente |


---

## 23. Módulo Proveedores (catálogo de exportadores Logiztik)

Pestaña **Proveedores**: catálogo de exportadores ("proveedores" de Bellaflor,
que es importadora) consultado **en vivo** desde el gateway móvil de Logiztik
Alliance — el mismo que usa la app *AllianceApp*. No persiste nada en Supabase.

### Origen
Endpoints y parámetros descubiertos analizando la APK de Logiztik Alliance
(React Native / motor Hermes, `com.logiztikalliance.allianceapp`) y validados
con captura de tráfico. Es un gateway **distinto** del WMS de Inventario LAG
(`cloudWS`): aquí la base es `apigwtmb.logiztikalliance.com`.

### Backend
- `backend/app/services/proveedores_client.py`
  - `_login()` → `POST /apisso/Account/Login` con `{usuario, clave, minutosExpiracion}`
    → JWT en `objetoADeserializar.token`. Token **cacheado en memoria** con expiración.
  - `get_categorias()` → `GET /apimobile/exportadores/CategoriaMercaderias`
    (FLORES FRESCAS `CME011`, FRUTAS, MARISCOS, VEGETALES, …). Header
    `Accept-Language: es-US` para recibir los nombres en español.
  - `get_proveedores(id_categoria, busqueda_exportador, busqueda_producto, id_pais)`
    → `POST /apimobile/exportadores/ObtenerExportadoresConMercanciaPaisAppMovil`
    con `{idEntidad, IdCategoriaMercancia, busquedaNombreExportador,
    busquedaNombreProducto, idPais}`. La respuesta viene agrupada por producto;
    el cliente **aplana y deduplica por exportador**, agregando sus productos.
- `backend/app/api/proveedores.py` — router `/proveedores`:
  - `GET /api/proveedores/health`
  - `GET /api/proveedores/categorias`
  - `GET /api/proveedores/exportadores?categoria=CME011&exportador=&producto=&pais=`
- Registrado en `main.py` (`proveedores_router`, prefix `/api`).

### Campos de cada proveedor
`id` (idExportador), `nombre`, `pais`, `codigoPais`, `contacto` (email),
`telefono`, `paginaWeb`, `productos` (lista separada por comas).

### Frontend — `pages/proveedores.html` + `pages/proveedores.js`
- Filtros de consulta (server-side): **Categoría de mercancía, Producto,
  Nombre del proveedor**.
- Filtro **País** (client-side, se llena con los países del resultado).
- **Búsqueda en vivo** sobre la lista cargada (nombre, país, producto, correo).
- **Paginación** de 50 por página con encabezado fijo y scroll.
- Tabla: **bandera** del país (desde `codigoPais`), **botones de contacto**
  (correo `mailto:` / teléfono `tel:`) y enlace **web**.
- **Productos ocultos**: se despliegan como *chips* al hacer clic en la fila.
- Pestaña agregada al `components/sidebar.html` (entre Inventario LAG y Torre de Control).

### Configuración
Variables `LOGIZTIK_MOBILE_BASE_URL`, `LOGIZTIK_USER`, `LOGIZTIK_PASS`,
`LOGIZTIK_ENTITY_ID` en `backend/.env` (local) y en Render → Environment (producción).
Sin ellas, `/api/proveedores/categorias` responde 503 pidiendo credenciales.

> ⚠️ Seguridad: `LOGIZTIK_PASS` es la contraseña real de la cuenta de Bellaflor
> en Logiztik. Nunca commitear el `.env`; rotar la clave si se expone.
