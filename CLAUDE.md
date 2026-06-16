# CLAUDE.md — BLIS Project Context

## Proyecto
**BLIS - Bellaflor Logistics Intelligence System**
Sistema de apoyo logístico y comercial para Bellaflor Group (exportadora de flores).
**No es un ERP financiero.** Foco exclusivo: logística, comercial, simulación de costos, análisis operativo.

## Stack
- **Frontend:** Vanilla HTML + CSS + JavaScript (sin frameworks, módulos ES6)
- **Backend:** FastAPI (Python) — sirve el frontend como archivos estáticos
- **Base de datos:** Supabase PostgreSQL · `kgpzhwocygonppblgmpm.supabase.co`
- **ORM:** SQLAlchemy + psycopg2 (conexión directa vía `DATABASE_URL` en `.env`)
- **Autenticación:** pendiente (tablas `roles` y `profiles` creadas, sin datos)

## Estructura de carpetas
```
BLIS/
├── backend/
│   ├── app/
│   │   ├── api/          ← un archivo por módulo (especies, variedades, etc.)
│   │   ├── database/     ← connection.py (SQLAlchemy), helpers.py
│   │   ├── schemas/      ← modelos Pydantic de entrada/salida
│   │   ├── models/       ← (pendiente de poblar)
│   │   ├── services/     ← (pendiente de poblar)
│   │   └── main.py       ← FastAPI app + CORS + monta frontend en "/"
│   ├── scripts/          ← carga y normalización de datos (ya ejecutados)
│   ├── tests/
│   └── .env              ← DATABASE_URL (nunca al repo)
├── frontend/
│   ├── assets/
│   ├── components/
│   │   └── sidebar.html
│   ├── css/
│   │   └── styles.css
│   ├── js/
│   │   ├── api.js        ← apiGet/apiPost/apiPut/apiDelete (fetch wrapper)
│   │   ├── crud-page.js  ← lógica CRUD reutilizable
│   │   └── layout.js     ← carga sidebar y header
│   ├── pages/            ← un .html + un .js por módulo
│   └── index.html
├── database/
│   ├── migrations/
│   ├── schema/           ← schema_v1.sql
│   ├── seeds/            ← seeds_v1.sql
│   └── views/            ← views_v1.sql
├── docs/                 ← ERD, especificaciones, PRD
├── requirements.txt
├── .gitignore
├── rules/
│   ├── security.md
│   └── coding-style.md
└── CLAUDE.md             ← este archivo
```

## Rutas API implementadas (prefix /api)
| Módulo | Ruta | Estado |
|--------|------|--------|
| Especies | `/api/especies` | ✅ 54 registros |
| Variedades | `/api/variedades` | ✅ 870 registros |
| Grados | `/api/grados` | ✅ 140 registros |
| Tipos de caja | `/api/tipos-caja` | ✅ 12 registros |
| Aeropuertos | `/api/aeropuertos` | ✅ 6 registros |
| Aerolíneas | `/api/aerolineas` | ✅ 5 registros |
| Países | `/api/paises` | ✅ 5 registros |
| Clientes | `/api/clientes` | ✅ 1 registro |
| Dashboard | `/api/dashboard` | ✅ |
| Roles | `/api/roles` | ⚠️ sin datos |
| Perfiles | `/api/perfiles` | ⚠️ sin datos |

## Tablas Supabase con datos pero SIN API aún
- `markets`, `currencies`, `exchange_rates`
- `incoterms` (4 filas), `cost_components` (16 filas)
- `providers` (3 filas), `service_types` (9 filas)
- `distribution_centers`, `fuel_charges`, `provider_tariffs`
- `scenario_headers`, `scenario_details`, `scenario_cost_results` ← **Costing Engine**

## Tablas vacías (pendiente cargar datos)
- `packaging_configurations` — entrada del Costing Engine
- `logistics_routes`, `airline_tariffs`, `airline_volumetric_factors`
- `airport_charges`, `country_duties`, `product_costs`
- `scenario_route_comparisons`

## Fórmulas clave (Costing Engine)
```
Peso Volumétrico = (Largo × Ancho × Alto) / Factor Volumétrico
Peso Facturable  = MAX(Peso Real, Peso Volumétrico)
```

## Convenciones de código
- Ver `rules/coding-style.md`
- Ver `rules/security.md`
- Commits: `feat:`, `fix:`, `refactor:`, `docs:` (conventional commits)
- Nunca hardcodear credenciales — usar `backend/.env` (excluido del repo)
