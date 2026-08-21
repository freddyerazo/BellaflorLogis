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
- **Base de datos:** Supabase PostgreSQL · `kgpzhwocygonppblgmpm.supabase.co` — 51 tablas en `public`
- **ORM:** SQLAlchemy + psycopg2, mayormente SQL crudo vía `text()` (sin capa ORM de modelos)
- **Autenticación:** pendiente (`roles` y `profiles` existen, 0 filas)
- **Tests:** no hay tests automatizados (`backend/tests/` vacío)

## Estructura de carpetas
```
BLIS/
├── backend/
│   ├── app/
│   │   ├── api/          ← 22 módulos activos, montados en main.py bajo /api
│   │   ├── database/     ← connection.py (SQLAlchemy), helpers.py
│   │   ├── schemas/      ← modelos Pydantic (cubre la mayoría de módulos)
│   │   ├── models/       ← vacío, no se usa (lógica vive en api/*.py con SQL crudo)
│   │   ├── services/     ← 12 archivos (LAG, Torre de Control, Auditoría de Etiquetas) — antes vacío
│   │   └── main.py       ← FastAPI app + CORS + scheduler (apscheduler) + monta frontend en "/"
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
│   ├── pages/            ← 19 páginas, un .html + un .js por módulo
│   └── index.html
├── database/
│   ├── migrations/       ← 002 a 019 (cargo agencies, farms, customers, Dartis ventas, módulos clonados)
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
| Clientes | `/api/clientes` | 1,703 — incluye `es_cliente_especial` (62 marcados) |
| Agencias de carga | `/api/cargo-agencies` (`cargo_agencies`) | 34 |
| Fincas | `/api/farms` (`farms` / `farm_postcosecha`) | 3 / 6 |
| Tarifas aerolínea | `/api/airline-tariffs` | 8 |
| Cotización (Costing Engine) | `/api/cotizacion` — wizard que combina especies, variedades, tarifas | funcional, `scenario_*` con datos de prueba |
| Importación Dartis | `/api/dartis-import` (`dartis_ventas`, `import_species_varieties`) | 20,888 / 1,211 |
| Ingresos locales | `/api/ingresos-locales` | — |
| Dashboard | `/api/dashboard` | — |
| Roles | `/api/roles` | 0 (auth pendiente) |
| Perfiles | `/api/perfiles` | 0 (auth pendiente) |
| Agrocalidad | `/api/agrocalidad` (`agrocalidad_requests`/`agrocalidad_requirements`) | 44 / 196 — clon de la app externa "Agrocalidad Consulta"; el scraping real sigue en GitHub Actions del repo `freddyerazo/AgrocalidadDartis`, disparado desde BLIS vía `GITHUB_TOKEN`/`GITHUB_REPO` (pendiente de configurar en `.env`) |
| Inventario LAG | `/api/inventario-lag` | sin BD propia — proxy en vivo sobre las APIs del WMS de Logiztik Alliance Group (bodega Miami); clon de "InventarioApiLag". Requiere `LAG_ENV`/`LAG_CUSTOMER_CODE`/`LAG_TOKEN`/`LAG_SALES_API_KEY` en `.env` (pendiente de configurar). Incluye "Posteo de Inventario" (`POST /posteo-inventario`, endpoint legacy `PlaceOrder/ordernew`) — **sin ambiente de pruebas**, cada llamada crea una orden real; requiere `LAG_PLACE_ORDER_TOKEN` (distinto de `LAG_TOKEN`) |
| Torre de Control | `/api/torre-control` (`courier_reconciliation`, `courier_ups_manifest`, `courier_fedex_envios`, `courier_agency_mapping`) | conciliación de cajas: `dartis_ventas` agrupada por `id_pedido` vs manifiestos UPS/FedEx vs tracking en vivo vs entregas de agencias locales; clon de "REPORTEUPSFEDEX". Scheduler propio (`apscheduler`, `REFRESH_SECONDS`). Requiere `UPS_CLIENT_ID/SECRET`, `FEDEX_CLIENT_ID/SECRET`, `DUOPLANE_API_KEY/PASSWORD` en `.env` para datos reales (por defecto `DEMO_MODE=true`) |
| Auditoría de Etiquetas | `/api/auditoria-etiquetas` (`special_dispatches`, `special_dispatch_audits`, `telegram_conversation_state`) | despachos de `customers.es_cliente_especial` generados directo desde `dartis_ventas` (sin subir Excel), auditados vía bot de Telegram; clon de "Auditoria_LEsp". Requiere `TELEGRAM_BOT_TOKEN`/`TELEGRAM_WEBHOOK_SECRET`/`GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON`/`GOOGLE_DRIVE_FOLDER_ID` en `.env`. **El webhook real de Telegram todavía no se registró** — Apps Script del proyecto original sigue operando hasta que se confirme el corte |

## Módulos externos clonados a BLIS (una pestaña por proyecto) — ✅ completo
Plan completo (con detalles de cada fase) en `C:\Users\Coordinación\.claude\plans\rustling-beaming-heron.md`.
1. ✅ **Agrocalidad Consulta** → `/api/agrocalidad`
2. ✅ **InventarioApiLag** → `/api/inventario-lag`
3. ✅ **REPORTEUPSFEDEX** → `/api/torre-control` (el bot RPA de tracking en Dartis queda pendiente como Fase 3b, ver plan)
4. ✅ **Auditoria_LEsp** → `/api/auditoria-etiquetas` (corte del webhook de Telegram a producción pendiente de confirmación, ver plan)

## Módulos con datos en Supabase pero SIN API todavía
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
- `models/` vacío — toda la lógica de negocio vive directo en `api/*.py`/`services/*.py` con SQL embebido
- `requirements.txt` duplicado entre raíz y `backend/`
- Dos entornos virtuales locales (`.venv`, `.venv-1`) — ambos ignorados en git, revisar cuál es el vigente
- 4 módulos nuevos (Agrocalidad, Inventario LAG, Torre de Control, Auditoría de Etiquetas) corren sin credenciales reales configuradas en `.env`/Render — ver la tabla de rutas arriba para la lista exacta por módulo
- Fase 3b (bot RPA de tracking en Dartis) y el corte del webhook de Telegram a producción (Fase 4) quedaron deliberadamente pendientes — ver plan
- Documentación repartida entre `CLAUDE.md`, `BLIS_DOCUMENTACION.md`, `PRODUCT.md`, `AGENTS.md`, `README.md` — las 5 se sincronizaron en esta ronda (agosto 2026), pero mantenerlas al día requiere disciplina en cada cambio futuro

## Convenciones de código
- Ver `rules/coding-style.md`
- Ver `rules/security.md`
- Commits: `feat:`, `fix:`, `refactor:`, `docs:` (conventional commits)
- Nunca hardcodear credenciales — usar `backend/.env` (excluido del repo)
