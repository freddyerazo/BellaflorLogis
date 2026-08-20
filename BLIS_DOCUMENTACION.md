# BLIS — Bellaflor Logistics Intelligence System
## Documentación Técnica Completa · v1.0 · Agosto 2026

---

## Índice

1. [Descripción del proyecto](#1-descripción-del-proyecto)
2. [Stack tecnológico](#2-stack-tecnológico)
3. [Estructura del proyecto](#3-estructura-del-proyecto)
4. [Variables de entorno](#4-variables-de-entorno)
5. [Endpoints de la API](#5-endpoints-de-la-api)
6. [Import Dartis — detalle técnico](#6-import-dartis--detalle-técnico)
7. [Ingresos Locales — GAS](#7-ingresos-locales--gas)
8. [Base de datos — tablas](#8-base-de-datos--tablas)
9. [Relaciones clave](#9-relaciones-clave)
10. [Páginas del frontend](#10-páginas-del-frontend)
11. [Despliegue en Render.com](#11-despliegue-en-rendercom)
12. [Desarrollo local](#12-desarrollo-local)
13. [GitHub](#13-github)

---

## 1. Descripción del proyecto

BLIS es una plataforma web interna de Bellaflor Group para análisis, simulación y gestión de costos logísticos de exportación de flores. Centraliza datos de múltiples fuentes — Dartis (sistema de ventas), Google Apps Script (ingresos locales), y una base de datos propia en Supabase — en una interfaz de administración unificada.

**Objetivos principales:**
- Importar y normalizar ventas desde Dartis (archivos Excel)
- Consultar ingresos locales desde Google Sheets vía GAS
- Generar cotizaciones logísticas con cálculo de peso cargable
- Mantener el catálogo de clientes, especies, variedades, aerolíneas, agencias de carga y fincas

**URL de producción:** `https://blis-hxu1.onrender.com`  
**Plan:** Free (spin-down tras 15 min de inactividad) → actualizar a Starter $7/mes para siempre activo

---

## 2. Stack tecnológico

| Capa | Tecnología | Versión | Notas |
|---|---|---|---|
| Backend | FastAPI | 0.141+ | Python 3.11+ |
| Servidor ASGI | Uvicorn | 0.52+ | Con `uvloop` en Linux |
| ORM / DB | SQLAlchemy | 2.x | Modo Core (SQL raw) |
| Driver PostgreSQL | psycopg2-binary | 2.9+ | `execute_values` para bulk insert |
| Base de datos | PostgreSQL (Supabase) | 15 | Cloud, región us-east-1 |
| Excel parsing | openpyxl | 3.1+ | `read_only=True` para streaming |
| HTTP cliente | httpx | 0.28+ | Proxy async hacia GAS |
| Multipart | python-multipart | — | Requerido por FastAPI para File upload |
| Frontend | HTML + JS vanilla | ES2022 | Sin frameworks, módulos nativos |
| Iconos | Phosphor Icons | 2.1.1 | CDN unpkg |
| Deploy | Render.com | — | Plan Free → Starter recomendado |
| Control de versiones | GitHub | — | `freddyerazo/BellaflorLogis` |

---

## 3. Estructura del proyecto

```
BLIS/
├── backend/
│   ├── requirements.txt              # dependencias Python (fuente de verdad para Render)
│   └── app/
│       ├── main.py                   # FastAPI app, monta frontend como static
│       ├── api/
│       │   ├── health.py
│       │   ├── dashboard.py
│       │   ├── cotizacion.py
│       │   ├── dartis_import.py      # import Excel Dartis (bulk insert)
│       │   ├── ingresos_locales.py   # proxy async → GAS
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
│       ├── schemas/                  # Pydantic models por entidad
│       └── database/
│           ├── connection.py         # engine = create_engine(DATABASE_URL)
│           └── helpers.py
├── frontend/
│   ├── index.html                    # redirect → /pages/dashboard.html
│   ├── css/
│   │   └── styles.css
│   ├── js/
│   │   └── layout.js                 # inyecta sidebar en todas las páginas
│   ├── pages/                        # una página HTML por módulo
│   └── components/
│       └── sidebar.html
├── database/
│   ├── schema/
│   │   └── schema_v1.sql
│   ├── views/
│   │   └── views_v1.sql
│   └── seeds/
│       └── seeds_v1.sql
├── docs/                             # documentos Word de arquitectura
├── requirements.txt                  # raíz (usado localmente)
├── render.yaml                       # config de deploy en Render
└── .gitignore                        # excluye .env, .venv, __pycache__
```

---

## 4. Variables de entorno

El archivo `backend/.env` **nunca se commitea**. En producción (Render), se configuran en **Environment → Add Environment Variable**.

| Variable | Requerida | Descripción |
|---|---|---|
| `DATABASE_URL` | Sí | Cadena de conexión PostgreSQL. Formato: `postgresql://user:password@host:5432/postgres`. Obtenida desde Supabase → Project Settings → Database → Connection string. |
| `INGRESOS_LOCALES_URL` | Sí | URL pública del Web App de Google Apps Script. Formato: `https://script.google.com/macros/s/AKfy.../exec`. Se regenera cada vez que se publica el GAS. |

> ⚠️ **Nunca compartir el valor de `DATABASE_URL` en el chat ni en el código.** Contiene usuario, contraseña y host de Supabase.

### Archivo `.env` local

```env
DATABASE_URL=postgresql://postgres.xxxx:password@aws-0-us-east-1.pooler.supabase.com:5432/postgres
INGRESOS_LOCALES_URL=https://script.google.com/macros/s/.../exec
```

---

## 5. Endpoints de la API

Todos los endpoints tienen prefijo `/api` excepto `/health`. El frontend estático está montado en `/`.

### Sistema

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/health` | Healthcheck. Devuelve `{"status":"ok"}` |
| `GET` | `/api/db-test` | Prueba la conexión a Supabase |

### Dashboard

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/dashboard/summary` | Conteos de todas las tablas, top 5 especies, distribución de cajas, último escenario calculado |

### Cotizaciones

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/cotizacion/catalogo` | Todos los catálogos del wizard: países origen/destino, especies, variedades, grados, cajas, aerolíneas, rutas activas, aeropuertos, incoterms, tipos de cambio |

### Ingresos Locales

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/ingresos-locales/datos` | Proxy async hacia el GAS de IngresosLocales. Timeout 120s (cold start GAS puede tardar 1–2 min) |

### Import Dartis

| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/api/dartis/upload` | Recibe dos archivos Excel (`file_recetas`, `file_ventas`) con `multipart/form-data`. Proceso en thread pool via `run_in_executor`. |

### Catálogos (CRUD)

| Recurso | Prefijo | Operaciones |
|---|---|---|
| Especies | `/api/species` | GET list, GET one, POST, PUT, DELETE |
| Variedades | `/api/varieties` | GET list, GET one, POST, PUT, DELETE |
| Grados | `/api/product-sizes` | GET list, GET one, POST, PUT, DELETE |
| Tipos de caja | `/api/box-types` | GET list, GET one, POST, PUT, DELETE |
| Aeropuertos | `/api/airports` | GET list, GET one, POST, PUT, DELETE |
| Países | `/api/countries` | GET list |
| Clientes | `/api/customers` | GET list, GET one, POST, PUT, DELETE |
| Aerolíneas | `/api/airlines` | GET list, GET one, POST, PUT, DELETE |
| Tarifas aerolínea | `/api/airline-tariffs` | GET list, POST, PUT, DELETE |
| Agencias de carga | `/api/cargo-agencies` | GET list, GET one, POST, PUT, DELETE |
| Fincas | `/api/farms` | GET list, GET one, POST, PUT, DELETE |
| Roles | `/api/roles` | GET list |
| Perfiles | `/api/profiles` | GET list, GET one, POST, PUT |

---

## 6. Import Dartis — detalle técnico

El módulo `dartis_import.py` procesa dos archivos Excel exportados desde Dartis. Todo el procesamiento corre en un thread pool (`asyncio.run_in_executor`) para no bloquear el event loop de uvicorn.

### Flujo de procesamiento

**Paso 1 — Ventas Recetas** (archivo principal, filas desde la fila 8):

| Col | Campo |
|---|---|
| 0 | fecha |
| 1 | DAE |
| 2 | id_comercializadora |
| 3 | id_pedido *(clave, requerida)* |
| 4 | empresa |
| 5 | cliente |
| 6 | destinatario |
| 7 | postcosecha |
| 8 | especie |
| 9 | guia_madre |
| 10 | guia_hija |
| 11 | tipo_caja |
| 12 | total_piezas |
| 13 | total_tallos |
| 14 | total_dolares |

**Paso 2 — Ventas Clásico** (archivo secundario): enriquece `vendedor` y `agencia_carga` por `id_pedido` vía tabla temporal.

### Estrategia de inserción

| Paso | Técnica | Por qué |
|---|---|---|
| INSERT principal | `psycopg2.execute_values` | Un solo SQL con todos los valores — 10–20× más rápido que `executemany` |
| Conflictos | `ON CONFLICT DO UPDATE` | Clave única: `(id_pedido, guia_madre, guia_hija, tipo_caja)` |
| Deduplicación previa | Dict Python por clave | El Excel puede tener filas duplicadas; `ON CONFLICT` falla si hay duplicados en el mismo batch |
| Enrich ventas | Temp table + UPDATE JOIN | Un solo UPDATE afecta miles de filas; la temp table se elimina al hacer COMMIT (`ON COMMIT DROP`) |
| Clientes nuevos | Bulk INSERT + UPDATE masivo | Crea clientes faltantes en batch; luego un solo UPDATE vincula `customer_id` en todo `dartis_ventas` |

### Sincronización de clientes (`_sync_customers`)

1. Carga todos los `dartis_name` existentes en memoria (un solo SELECT)
2. Identifica clientes faltantes (case-insensitive)
3. Genera códigos únicos de 6 caracteres para los nuevos
4. INSERT masivo con `execute_values` + `ON CONFLICT DO NOTHING`
5. UPDATE masivo: `UPDATE dartis_ventas SET customer_id = c.id FROM customers c WHERE LOWER(TRIM(c.dartis_name)) = LOWER(TRIM(dv.cliente))`

### Respuesta del endpoint

```json
{
  "recetas": {
    "archivo": "VentasRecetas.xlsx",
    "insertados_o_actualizados": 12241,
    "errores": 0,
    "postcosechas_sin_finca": [],
    "clientes_vinculados": 8934,
    "clientes_nuevos": 12
  },
  "ventas": {
    "archivo": "Ventas.xlsx",
    "filas_procesadas": 11800,
    "actualizadas": 11800,
    "errores": 0,
    "agencias_nuevas": []
  }
}
```

---

## 7. Ingresos Locales — GAS

La página de Ingresos Locales consume datos desde un Google Apps Script (GAS) que lee directamente de Google Sheets. BLIS actúa como proxy para evitar CORS.

| Aspecto | Detalle |
|---|---|
| Fuente de datos | Google Sheets (hoja de ingresos locales de Bellaflor) |
| GAS project ID | `1_qxgkU27OHG0JoLyyDAn1DpZm_jsRHtJ1sLSvRVT9I5-N0xX5IAfcj51` |
| Endpoint backend | `GET /api/ingresos-locales/datos` |
| Timeout | 120 segundos |
| Variable de entorno | `INGRESOS_LOCALES_URL` |
| Cold start | Primera carga del día puede tardar 60–120s. Normal — el spinner de la UI lo indica con mensaje de advertencia. |

> ⚠️ Si `INGRESOS_LOCALES_URL` no está configurada en Render, la página muestra **"URL no configurada"**. Solución: Render → Environment → Add Environment Variable → `INGRESOS_LOCALES_URL`.

---

## 8. Base de datos — tablas

Base de datos PostgreSQL en Supabase. Todas las tablas usan `UUID` como `id` (generado por `gen_random_uuid()`).

| Tabla | Descripción | Campos principales |
|---|---|---|
| `species` | Especies de flores | id, code, name, active |
| `varieties` | Variedades por especie | id, species_id, code, name, active |
| `product_sizes` | Grados/tallos por especie | id, species_id, size_code, description, active |
| `box_types` | Tipos de caja con dimensiones | id, box_code, box_name, length_cm, width_cm, height_cm, reference_weight_kg, active |
| `airports` | Aeropuertos con código IATA | id, iata_code, airport_name, city, country_id, active |
| `countries` | Países | id, code, name, active |
| `airlines` | Aerolíneas | id, airline_code, airline_name, active |
| `airline_tariffs` | Tarifas por ruta y aerolínea | id, airline_id, origin_airport_id, destination_airport_id, valid_from, valid_to, active |
| `cargo_agencies` | Agencias de carga aérea | id, code, name, dartis_name, ocr_variants, type |
| `customers` | Clientes exportadores | id, customer_code, customer_name, dartis_name, active |
| `farms` | Fincas / postcosechas | id, farm_code, farm_name, active |
| `farm_postcosecha` | Nombres de postcosecha por finca | id, farm_id, postcosecha |
| `dartis_ventas` | Ventas importadas desde Dartis | id, fecha, dae, id_comercializadora, id_pedido, empresa, cliente, **customer_id**, destinatario, postcosecha, especie, guia_madre, guia_hija, tipo_caja, total_piezas, total_tallos, total_dolares, vendedor, agencia_carga, importado_at |
| `roles` | Roles de usuario | id, name |
| `profiles` | Perfiles de usuarios del sistema | id, user_id, role_id, full_name |
| `markets` | Mercados destino | id, code, name |
| `providers` | Proveedores logísticos | id, name, active |
| `incoterms` | Términos de comercio internacional | id, code, name |
| `cost_components` | Componentes de costo logístico | id, component_name, category |
| `scenario_headers` | Cabecera de escenarios de cotización | id, scenario_code, scenario_name, created_at |
| `scenario_details` | Líneas de detalle del escenario | id, scenario_id, boxes, chargeable_weight_kg |
| `scenario_cost_results` | Resultados de costo por escenario | id, scenario_id, cost_component_id, amount, currency_code |
| `exchange_rates` | Tipos de cambio | id, currency_code, rate, rate_date |

### Migración aplicada manualmente

```sql
-- customer_id en dartis_ventas (FK hacia customers)
ALTER TABLE dartis_ventas
  ADD COLUMN IF NOT EXISTS customer_id UUID REFERENCES customers(id);
```

---

## 9. Relaciones clave

| Relación | Clave de unión | Propósito |
|---|---|---|
| `dartis_ventas → customers` | `customer_id` / `dartis_name` | Vincula ventas Dartis con el maestro de clientes. Se popula automáticamente al importar. |
| `varieties → species` | `species_id` | Cada variedad pertenece a una especie |
| `product_sizes → species` | `species_id` | Grados de tallo son específicos por especie |
| `airline_tariffs → airlines` | `airline_id` | Tarifa tiene una aerolínea |
| `airline_tariffs → airports` | `origin_airport_id`, `destination_airport_id` | Tarifa define ruta origen-destino |
| `farm_postcosecha → farms` | `farm_id` | Una finca tiene múltiples nombres de postcosecha |
| `scenario_details → scenario_headers` | `scenario_id` | Escenario de cotización multi-línea |
| `scenario_cost_results → scenario_headers` | `scenario_id` | Resultados de costo por escenario |
| `scenario_cost_results → cost_components` | `cost_component_id` | Detalle de componente de costo |

---

## 10. Páginas del frontend

Todas las páginas comparten `layout.js` que inyecta el sidebar. El body usa `display: flex` con `<div id="sidebar" class="sidebar">` y `<main class="content" id="content">` como hijos directos.

| Página | Archivo | Descripción |
|---|---|---|
| Dashboard | `pages/dashboard.html` | Resumen ejecutivo: conteos, top especies, último escenario |
| Ingresos Locales | `pages/ingresos-locales.html` | Tabla de ventas locales desde GAS. Spinner con aviso de cold start. |
| Import Dartis | `pages/dartis-import.html` | Carga de dos Excel con drag-and-drop. Barra de progreso animada. |
| Cotizaciones | `pages/cotizaciones.html` | Wizard de cotización logística |
| Clientes | `pages/clientes.html` | CRUD de clientes |
| Especies | `pages/especies.html` | CRUD de especies |
| Variedades | `pages/variedades.html` | CRUD de variedades (filtradas por especie) |
| Grados | `pages/grados.html` | CRUD de product_sizes |
| Tipos de caja | `pages/tipos-caja.html` | CRUD de box_types con dimensiones |
| Aeropuertos | `pages/aeropuertos.html` | CRUD de aeropuertos con código IATA |
| Aerolíneas | `pages/aerolineas.html` | CRUD de aerolíneas |
| Tarifas aerolínea | `pages/tarifas-aerolinea.html` | CRUD de airline_tariffs con vigencia |
| Agencias de carga | `pages/cargo-agencies.html` | CRUD de cargo_agencies |
| Fincas | `pages/farms.html` | CRUD de fincas y postcosechas |
| Configuración | `pages/configuracion.html` | Roles y perfiles de usuarios |

---

## 11. Despliegue en Render.com

### Configuración actual

| Campo | Valor |
|---|---|
| Service ID | `srv-da39og5g1s2s73d4jmlg` |
| URL | `https://blis-hxu1.onrender.com` |
| Plan | Free (spin-down tras 15 min) → Starter $7/mes para siempre activo |
| Runtime | Python 3 |
| Build command | `pip install -r backend/requirements.txt` |
| Start command | `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Branch | `main` de `freddyerazo/BellaflorLogis` |
| Auto-deploy | Sí — cada `git push` a main dispara un deploy automático |

### render.yaml

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

### Troubleshooting

| Error | Causa | Solución |
|---|---|---|
| `ModuleNotFoundError: No module named 'app'` | uvicorn corre desde raíz, no desde `backend/` | Start command: `cd backend && uvicorn ...` |
| `Could not parse SQLAlchemy URL` | `DATABASE_URL` vacía o no configurada | Agregar variable en Render → Environment |
| `Form data requires python-multipart` | Falta paquete en requirements | Agregar `python-multipart` y hacer Clear cache & deploy |
| Deploy usa paquetes del cache | Render cachea paquetes pip | Manual Deploy → ▼ → **Clear build cache & deploy** |
| `We are unable to access your GitHub repository` | Repo privado sin acceso a Render | Cambiar repo a público temporalmente o conectar con GitHub App en Render Settings |
| Página "URL no configurada" en Ingresos Locales | `INGRESOS_LOCALES_URL` no configurada | Render → Environment → Add Environment Variable |

---

## 12. Desarrollo local

### 1. Clonar e instalar

```bash
git clone https://github.com/freddyerazo/BellaflorLogis.git
cd BellaflorLogis
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r backend/requirements.txt
```

### 2. Configurar variables de entorno

```bash
# Crear archivo: backend/.env
DATABASE_URL=postgresql://postgres.xxxx:password@aws-0-us-east-1.pooler.supabase.com:5432/postgres
INGRESOS_LOCALES_URL=https://script.google.com/macros/s/.../exec
```

### 3. Iniciar el servidor

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

La app estará disponible en `http://localhost:8000`. El frontend se sirve como archivos estáticos desde `../frontend/`.

> `--reload` hace hot-reload automático al guardar archivos Python. No usar en producción.

---

## 13. GitHub

| Campo | Valor |
|---|---|
| Repositorio | `github.com/freddyerazo/BellaflorLogis` |
| Branch principal | `main` |
| Visibilidad | Privado (cambiar a público solo temporalmente para conectar Render) |
| Auto-deploy | Push a `main` → Render redeploya automáticamente |

### Archivos excluidos por `.gitignore`

```
backend/.env
.venv/
.venv-1/
__pycache__/
*.pyc
backups/
docs/*.docx
```

> ⚠️ Los tokens de GitHub deben eliminarse inmediatamente si se comparten accidentalmente. Ir a `github.com/settings/tokens` → Delete.

---

*Documentación generada: Agosto 2026 · Bellaflor Group · freddyerazo@unach.edu.ec*
