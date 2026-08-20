# CLAUDE.md — BLIS Project Context

## Proyecto
**BLIS - Bellaflor Logistics Intelligence System**
Sistema de apoyo logístico y comercial para Bellaflor Group (exportadora de flores).
**No es un ERP financiero.** Foco exclusivo: logística, comercial, simulación de costos, análisis operativo.

## Deploy
- **GitHub:** [freddyerazo/BellaflorLogis](https://github.com/freddyerazo/BellaflorLogis) (privado), rama `main`
- **Producción (Render):** https://blis-hxu1.onrender.com — plan free, autodeploy en push a `main`
- Sin GitHub Actions / CI configurado — el único gate antes de producción es el build de Render

## Stack
- **Frontend:** Vanilla HTML + CSS + JavaScript (sin frameworks, módulos ES6)
- **Backend:** FastAPI (Python) — sirve el frontend como archivos estáticos
- **Base de datos:** Supabase PostgreSQL · `kgpzhwocygonppblgmpm.supabase.co` — 43 tablas en `public`
- **ORM:** SQLAlchemy + psycopg2, mayormente SQL crudo vía `text()` (sin capa ORM de modelos)
- **Autenticación:** pendiente (`roles` y `profiles` existen, 0 filas)
- **Tests:** no hay tests automatizados (`backend/tests/` vacío)

## Estructura de carpetas
```
BLIS/
├── backend/
│   ├── app/
│   │   ├── api/          ← 18 módulos activos, montados en main.py bajo /api
│   │   ├── database/     ← connection.py (SQLAlchemy), helpers.py
│   │   ├── schemas/      ← modelos Pydantic (cubre la mayoría de módulos)
│   │   ├── models/       ← vacío, no se usa (lógica vive en api/*.py con SQL crudo)
│   │   ├── services/     ← vacío, no se usa
│   │   └── main.py       ← FastAPI app + CORS + monta frontend en "/"
│   ├── scripts/          ← carga y normalización de datos (ya ejecutados)
│   ├── tests/            ← vacío
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
│   ├── pages/            ← 15 páginas, un .html + un .js por módulo
│   └── index.html
├── database/
│   ├── migrations/       ← 002 a 015 (cargo agencies, farms, customers, Dartis ventas)
│   ├── schema/           ← schema_v1.sql
│   ├── seeds/            ← seeds_v1.sql
│   └── views/            ← views_v1.sql
├── docs/                 ← ERD, especificaciones, PRD
├── scripts/              ← import_dartis.py, migrate.py (separado de backend/scripts)
├── requirements.txt      ← duplicado idéntico a backend/requirements.txt
├── .gitignore
├── rules/
│   ├── security.md
│   └── coding-style.md
└── CLAUDE.md             ← este archivo
```

## Rutas API implementadas (prefix /api, salvo health/db_test)
| Módulo | Ruta | Filas en Supabase |
|--------|------|--------------------|
| Especies | `/api/especies` | 101 |
| Variedades | `/api/variedades` | 870 |
| Grados (product_sizes) | `/api/grados` | 140 |
| Tipos de caja | `/api/tipos-caja` | 12 |
| Aeropuertos | `/api/aeropuertos` | 37 |
| Aerolíneas | `/api/aerolineas` | 8 |
| Países | `/api/paises` | 255 |
| Clientes | `/api/clientes` | 1,699 |
| Agencias de carga | `/api/cargo-agencies` (`cargo_agencies`) | 34 |
| Fincas | `/api/farms` (`farms` / `farm_postcosecha`) | 3 / 6 |
| Tarifas aerolínea | `/api/airline-tariffs` | 8 |
| Cotización (Costing Engine) | `/api/cotizacion` — wizard que combina especies, variedades, tarifas | funcional, `scenario_*` con datos de prueba |
| Importación Dartis | `/api/dartis-import` (`dartis_ventas`, `import_species_varieties`) | 12,269 / 1,211 |
| Ingresos locales | `/api/ingresos-locales` | — |
| Dashboard | `/api/dashboard` | — |
| Roles | `/api/roles` | 0 (auth pendiente) |
| Perfiles | `/api/perfiles` | 0 (auth pendiente) |

## Módulos con datos en Supabase pero SIN API todavía
- `agrocalidad_requests` (44) / `agrocalidad_requirements` (196) — módulo fitosanitario
- `markets`, `currencies`, `exchange_rates`
- `incoterms` (4), `cost_components` (16)
- `providers` (3), `provider_services` (3), `provider_tariffs` (1), `service_types` (9)
- `distribution_centers` (1), `fuel_charges` (1)

## Tablas vacías (pendiente cargar datos)
- `packaging_configurations` — entrada del Costing Engine
- `logistics_routes`, `airline_volumetric_factors`
- `airport_charges`, `country_duties`, `product_costs`
- `scenario_route_comparisons`
- `audit_logs`, `incoterm_cost_components`

## Fórmulas clave (Costing Engine)
```
Peso Volumétrico = (Largo × Ancho × Alto) / Factor Volumétrico
Peso Facturable  = MAX(Peso Real, Peso Volumétrico)
```

## Deuda técnica conocida
- Sin tests automatizados en `backend/tests/`
- `models/` y `services/` vacíos — toda la lógica de negocio vive directo en `api/*.py` con SQL embebido
- `requirements.txt` duplicado entre raíz y `backend/`
- Dos entornos virtuales locales (`.venv`, `.venv-1`) — ambos ignorados en git, revisar cuál es el vigente
- Documentación repartida entre `CLAUDE.md`, `BLIS_DOCUMENTACION.md`, `PRODUCT.md`, `AGENTS.md`, `README.md` — riesgo de divergencia

## Convenciones de código
- Ver `rules/coding-style.md`
- Ver `rules/security.md`
- Commits: `feat:`, `fix:`, `refactor:`, `docs:` (conventional commits)
- Nunca hardcodear credenciales — usar `backend/.env` (excluido del repo)
