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
│   │   ├── api/          ← 24 módulos activos, montados en main.py bajo /api
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
│   ├── pages/            ← 21 páginas, un .html + un .js por módulo
│   └── index.html
├── database/
│   ├── migrations/       ← 002 a 023 (cargo agencies, farms, customers, Dartis ventas, módulos clonados, Armellini Post)
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
| Clientes | `/api/clientes` | 1,703 — incluye `es_cliente_especial` (65 marcados) |
| Agencias de carga | `/api/cargo-agencies` (`cargo_agencies`) | 34 |
| Fincas | `/api/farms` (`farms` / `farm_postcosecha`) | 3 / 6 |
| Tarifas aerolínea | `/api/airline-tariffs` | 8 |
| Carriers Miami | `/api/truck-companies` (`truck_company`) | 139 — catálogo cargado desde "ID clientes.xlsx" hoja "Listado de Carriers-Miami"; usado como Carrier ID en Posteo de Inventario (Inventario LAG) |
| Cotización (Costing Engine) | `/api/cotizacion` — wizard que combina especies, variedades, tarifas; `/api/cotizaciones` (`cotizaciones`) para guardarlas, listarlas y reabrirlas | funcional, `scenario_*` con datos de prueba |
| Importación Dartis | `/api/dartis-import` (`dartis_ventas`, `import_species_varieties`) | 20,888 / 1,211 |
| Ingresos locales | `/api/ingresos-locales` | — |
| Dashboard | `/api/dashboard` | — |
| Roles | `/api/roles` | 0 (auth pendiente) |
| Perfiles | `/api/perfiles` | 0 (auth pendiente) |
| Agrocalidad | `/api/agrocalidad` (`agrocalidad_requirements`, `agrocalidad_requisitos`, `agrocalidad_requirement_items`) | requisitos fitosanitarios por especie y destino. **Desde el 2026-08-30 consulta directo la API móvil de Agrocalidad** (`services/agrocalidad_api.py`), sin credenciales: ya no usa el scraping con Playwright en GitHub Actions ni `GITHUB_TOKEN`. La consulta es síncrona (~3-5 s contra 30-90 s). 196 consultas guardadas, 37 requisitos en catálogo, 86 especies y 149 países mapeados |
| Inventario LAG | `/api/inventario-lag` | sin BD propia — proxy en vivo sobre las APIs del WMS de Logiztik Alliance Group (bodega Miami); clon de "InventarioApiLag". Requiere `LAG_ENV`/`LAG_CUSTOMER_CODE`/`LAG_TOKEN`/`LAG_SALES_API_KEY` en `.env` (pendiente de configurar). Incluye "Posteo de Inventario" (`POST /posteo-inventario`, endpoint legacy `PlaceOrder/ordernew`) — **sin ambiente de pruebas**, cada llamada crea una orden real; requiere `LAG_PLACE_ORDER_TOKEN` (distinto de `LAG_TOKEN`) |
| Torre de Control | `/api/torre-control` (`courier_reconciliation`, `courier_ups_manifest`, `courier_fedex_envios`, `courier_agency_mapping`) | conciliación de cajas: `dartis_ventas` agrupada por `id_pedido` vs manifiestos UPS/FedEx vs tracking en vivo vs entregas de agencias locales; clon de "REPORTEUPSFEDEX". Scheduler propio (`apscheduler`, `REFRESH_SECONDS`). Requiere `UPS_CLIENT_ID/SECRET`, `FEDEX_CLIENT_ID/SECRET`, `DUOPLANE_API_KEY/PASSWORD` en `.env` para datos reales (por defecto `DEMO_MODE=true`) |
| Auditoría de Etiquetas | `/api/auditoria-etiquetas` (`special_dispatches`, `special_dispatch_audits`, `telegram_conversation_state`) | despachos de `customers.es_cliente_especial` generados directo desde `dartis_ventas` (sin subir Excel), auditados vía bot de Telegram; clon de "Auditoria_LEsp". Requiere `TELEGRAM_BOT_TOKEN`/`TELEGRAM_WEBHOOK_SECRET` en `.env`. Las fotos de respaldo se suben vía un Apps Script propio y aislado (`GOOGLE_DRIVE_UPLOAD_URL`/`GOOGLE_DRIVE_UPLOAD_SECRET`) desplegado como Web App bajo una cuenta real — las cuentas de servicio de Google Cloud no tienen cuota de almacenamiento propia y no pueden subir archivos sin delegación de dominio (requiere admin de Workspace, no disponible); el Apps Script solo expone `doPost()` para guardar la foto, no reintroduce el bot ni las hojas del proyecto original. **El webhook real de Telegram todavía no se registró** — Apps Script del proyecto original (el bot completo) sigue operando hasta que se confirme el corte |
| Armellini Post | `/api/armellini-post` (`expoflor_operaciones_cajas`, `armellini_consignees`, `armellini_product_overrides`, `armellini_exports`) | genera el XML `AelisShipperEDI` de Armellini (carrier de Miami) desde el XML de operaciones de Expoflor (`ReservasExportadores`); clon de "ArmelliniFormat". En el WMS de LAG el carrier figura como "ARMELLINI NO EDI", por eso el archivo se arma aparte. Sin credenciales externas para generar/descargar el XML. El filtro de cajas es por **destino con consignee configurado**, no por código de carrier: las cajas de Heinen's (destinatario de los 5 XML históricos) vienen como `HEB` = "ARMELLINI NO EDI" y no como `ARM`, así que filtrar por carrier las habría omitido — `HEB` faltaba en `truck_company` y se agregó. **`armellini_consignees` se siembra a mano** (el código de consignee no existe en ninguna fuente) y ahí mismo vive `dias_entrega` por destino. `<Invoice>` del XML sale de `dartis_ventas.id_comercializadora` (no del campo `factura` del XML, que lleva el pedido). Incluye la **pre-alerta de despacho por correo** (destinatarios configurables + días de entrega por destino) vía **API de Gmail sobre HTTPS** — no SMTP, que Render bloquea en el plan gratuito: requiere `GMAIL_CLIENT_ID`/`GMAIL_CLIENT_SECRET`/`GMAIL_REFRESH_TOKEN`/`GMAIL_USER`, obtenidos con `backend/scripts/gmail_autorizar.py` |
| Proveedores | `/api/proveedores` (`/categorias`, `/exportadores`) | sin BD propia — proxy en vivo sobre el **gateway móvil** de Logiztik Alliance (`apigwtmb.logiztikalliance.com`, el mismo de la app AllianceApp; distinto del WMS de Inventario LAG). Login SSO `POST /apisso/Account/Login` (usuario/clave → JWT, token cacheado en memoria) y catálogo de exportadores (= "proveedores" de Bellaflor) `POST /apimobile/exportadores/ObtenerExportadoresConMercanciaPaisAppMovil` + categorías `GET /apimobile/exportadores/CategoriaMercaderias`. Requiere `LOGIZTIK_USER`/`LOGIZTIK_PASS`/`LOGIZTIK_ENTITY_ID`/`LOGIZTIK_MOBILE_BASE_URL` en `.env` (y en Render). Endpoints/params obtenidos por análisis de la APK (React Native/Hermes) + captura de tráfico. Frontend `pages/proveedores.*`: filtros categoría/producto/proveedor/país, búsqueda en vivo, paginación, banderas, botones de contacto y productos expandibles por fila |

## Módulos externos clonados a BLIS (una pestaña por proyecto) — ✅ completo
Plan completo (con detalles de cada fase) en `C:\Users\Coordinación\.claude\plans\rustling-beaming-heron.md`.
1. ✅ **Agrocalidad Consulta** → `/api/agrocalidad`
2. ✅ **InventarioApiLag** → `/api/inventario-lag`
3. ✅ **REPORTEUPSFEDEX** → `/api/torre-control` (el bot RPA de tracking en Dartis queda pendiente como Fase 3b, ver plan)
4. ✅ **Auditoria_LEsp** → `/api/auditoria-etiquetas` (corte del webhook de Telegram a producción pendiente de confirmación, ver plan)

5. ✅ **ArmelliniFormat** → `/api/armellini-post` (agosto 2026)

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
- Las cotizaciones guardadas viven en la tabla `cotizaciones` desde el 2026-08-30. Guardan el `state` completo del wizard en `estado` (JSONB) para poder reabrirlas tal cual, y ademas los totales desnormalizados en columnas propias: esos quedan **congelados** al guardar, asi que una cotizacion historica no cambia si manana cambia una tarifa o el tipo de cambio. Los montos se guardan siempre en USD (`moneda` solo define como se presenta). El catalogo se excluye del JSON al serializar (`estadoSerializable()` en `cotizaciones.js`): pesa cientos de KB y se recarga en cada `init()`. Antes de esto el boton "Guardar cotizacion" escribia en `localStorage` bajo `blis_cotizaciones`, clave que **no se leia en ninguna parte** — el guardado no guardaba nada recuperable
- **Agrocalidad ya no depende del scraping** (2026-08-30). La app oficial AGRO Movil (Flutter) resulto tener un backend REST/JSON en el mismo dominio (`guia.agrocalidad.gob.ec/agrodb/aplicaciones/mvc/AplicacionMovilExternos/`) que expone los mismos datos que el sitio protegido por Imperva, sin captcha ni bloqueo anti-bot. Cadena: `obtenerProductosPorSubtipoProducto/<21 flores|23 follajes>` -> `obtenerDatosProductos/<id_producto>` -> `obtenerPaisProducto/<id_producto>/<movimiento>` -> `obtenerRequisitosPorPais/<id_producto>/<movimiento>/<id_localizacion>`. **El movimiento va con tilde ("Exportación"); sin tilde el servicio responde 200 con lista vacia en vez de un error** — falla en silencio. La cola `agrocalidad_requests` queda con su historial pero el modulo ya no escribe en ella; el repo externo `freddyerazo/AgrocalidadDartis` sigue existiendo y no fue modificado
- **Ojo con `codigo_producto` de Agrocalidad**: NO identifica un producto. El codigo 0001 lo comparten rosa, clavel, crisantemo, aster, gerbera y alstroemeria — casi todo el volumen de Bellaflor. La clave unica y estable es `id_producto` (rosa=18597, Clavel=16700, Crisantemo=16709). Se guarda en `agrocalidad_code` con la letra al frente (`A0001`), igual que la web; verificado contra la web y contra las 157 filas historicas del scraping
- El catalogo de Agrocalidad **repite nombres entre subtipos**: 31 nombres tienen mas de un `id_producto`. 'Acacia' existe como Flor (56725, 2 paises) y como Follaje (29921, 30 paises); lo mismo Eucalipto, Lavanda y Pittosporum variegata. Al mapear una especie nueva hay que elegir la entrada realmente en uso — la de mas paises con requisitos, no la primera que aparece
- Comparacion API vs scraping sobre las 174 combinaciones recargadas: 147 coinciden y 27 no. **Verificado contra la web que la API es la correcta y el scrapeo estaba desactualizado**: Agrocalidad consolido varios requisitos sueltos en uno solo ("REQUISITOS GENERALES PARA CERTIFICACION", id 2951) y cambio requisitos desde julio. Otras 14 devuelven cero porque Agrocalidad no tiene datos para ese destino (sobre todo Chile), limitacion ya documentada en el proyecto original. El texto plano scrapeado se conserva en `requirements` para auditoria
- Rendimiento del modulo Agrocalidad, medido: la API de Agrocalidad tarda ~1,7 s (las dos llamadas, ficha y requisitos, van en paralelo porque son independientes) y **cada round-trip a Supabase cuesta ~195 ms** — las consultas SQL en si tardan 0,3 ms, todo el costo es latencia de red. La primera version hacia 11 round-trips por consulta (insercion fila por fila, violando `rules/coding-style.md`) y tardaba 6,3 s de mediana; con `execute_values` y el mapeo resuelto en una sola query bajo a 2,9 s. Un resultado guardado de las ultimas 24 h se reutiliza y responde en ~1,2 s (`?refrescar=true` fuerza la consulta en vivo). Regla practica para este proyecto: antes de optimizar SQL, contar round-trips
- `countries` guarda el catalogo de destinos de Agrocalidad completo desde el 2026-08-30 (migracion 031). Fuente canonica: `RestWsOperadores/obtenerLozalizacion/0`, que devuelve los 255 paises con {id, nombre} y cuyos ids **coinciden** con los que usa `obtenerRequisitosPorPais` (verificado con EEUU 1987, Chile 46, Paises Bajos 1920, Rusia 1945, España 68, Alemania 57). El cruce por `name_es` dio **255 de 255** sin excepciones — esa columna ya traia el nombre exacto de Agrocalidad. Antes solo 149 paises tenian id, porque el mapeo se habia armado con la union de destinos de 5 productos. Columnas nuevas: `nombre_agrocalidad` (copia fiel del origen, separada de `name_es` que es editable desde BLIS) y `es_bloque_agrocalidad`. Carga reproducible en `backend/scripts/cargar_paises_agrocalidad.py`
- **Agrocalidad publica requisitos a nivel de bloque, no solo de pais**: "Unión Europea" (2062) y "Comunidad económica Euroasiática - CEEA" (2064) aparecen como destino en `obtenerPaisProducto` pero NO estan en el catalogo de paises. Se insertaron en `countries` con `active = false` y `es_bloque_agrocalidad = true`, para que el modulo Agrocalidad pueda ofrecerlos sin que aparezcan en los listados del resto (cotizacion filtra por active). Ojo: `GET /api/countries` **no** filtra por active, asi que ahi si se ven — hoy ninguna pagina del frontend consume ese endpoint
- La API de Agrocalidad devuelve algunos destinos con `id_localizacion` en **null** (San Bartolome y San Martin en el caso de rosa). Sin ese id la consulta de requisitos no se puede armar, asi que `paises_producto()` los descarta: rosa pasa de 157 a 155 destinos ofrecibles
- `countries.cod_agroca` (migracion 032) es el codigo de pais de dos letras. **Ojo con el origen: es ISO 3166-1 alfa-2, NO un dato de Agrocalidad.** Se verificaron los 255 elementos de `obtenerLozalizacion/0` (solo {id, nombre}) y las cadenas del binario de AGRO Movil (solo `nombre_pais` y `pais`): la API no publica ningun codigo de pais. El identificador propio de Agrocalidad sigue siendo `id_localizacion_agrocalidad`. Cobertura: 251 de 257; quedan NULL las 6 entidades que no son paises ISO (Aguas Internacionales, Escocia, Gales, Inglaterra, Unión Europea, CEEA). Origen de los valores: 108 ya estaban bien en `countries.code`, 118 por nombre ISO literal, 25 por equivalencia declarada explicita en `backend/scripts/cargar_cod_agroca.py` (requiere `pycountry`, dependencia solo de ese script, no de produccion)
- **`countries.code` esta mal en 147 de 257 filas**: solo 108 tienen un codigo real de dos letras, el resto lleva el nombre del pais como codigo (`SENEGAL`, `TRINIDAD_Y_TOBAGO`, `SAINT_KITTS_AND_NEVIS`), generado al cargar el catalogo. `cod_agroca` es la columna limpia; `code` se dejo intacta para no romper lo que ya dependa de ella
- `cod_agroca` **no lleva UNIQUE a proposito**: el catalogo de Agrocalidad trae "Catar" (id 2061) y "Qatar" (id 1941) como dos paises distintos y ambos son ISO 'QA'. El duplicado es del origen
- La pestaña Agrocalidad tiene **consulta por pais** (barrido de todo el catalogo contra un mismo destino), equivalente al "Verificar catalogo completo para este pais" del sitio de GitHub. Corre en el frontend con concurrencia 3 y boton de cancelar. Medido: **1,9 s de reloj por especie en vivo** (ese numero ya incluye el paralelismo) = ~2,7 min para las 86 especies; si ya hay resultados de las ultimas 24 h baja a ~0,4 s por especie (37 s el barrido completo). No se hace server-side a proposito: una peticion HTTP de 2,7 min no sobrevive el timeout de Render free
- El historial de Agrocalidad lista **solo las combinaciones que exigen algo** (`GET /api/agrocalidad/requisitos`, parametro `solo_con_requisitos`, por defecto true). El filtro usa `n_requisitos` de la vista, agregado en la migracion 033: cuenta los items estructurados y, si no hay, los marcadores `Rn:` del texto plano del scraping viejo. Contar solo items habria ocultado 7 filas historicas con requisitos reales (Euphorbia a Estados Unidos tiene 12 en texto y 0 items) y las habria mostrado con "0", que es igual de incorrecto
- Sin tests automatizados en `backend/tests/`
- `models/` vacío — toda la lógica de negocio vive directo en `api/*.py`/`services/*.py` con SQL embebido
- **Sin autenticación**: la API en producción esta abierta a internet. Verificado el 2026-08-29: `GET /api/customers` responde 200 sin credenciales, y hay 53 endpoints de escritura sin ninguna dependencia de auth. Mitigación parcial aplicada ese día: CORS dejo de ser `*` (ahora `CORS_ORIGINS`) y `BLIS_API_KEY` exige `X-API-Key` en POST/PUT/PATCH/DELETE. Ojo: **activar `BLIS_API_KEY` rompe el guardado desde el frontend**, que no envía esa cabecera — sirve para integraciones, no sustituye al login. Las tablas `roles`/`profiles` siguen vacías
- `requirements.txt` de la raíz ya no duplica al de `backend/`: solo lo incluye con `-r backend/requirements.txt`. Las versiones estan fijadas con `==` desde el 2026-08-29 (antes cada build de Render instalaba lo último publicado ese día)
- La versión de Python vive en `.python-version` (`3.13`), no en `PYTHON_VERSION` de `render.yaml`: la variable exige un patch exacto y el build falla si no existe, mientras que el archivo deja que Render resuelva el último patch. Antes `render.yaml` declaraba 3.11.0 mientras el entorno local corría 3.13. Si el servicio tiene una `PYTHON_VERSION` puesta a mano en el dashboard de Render, esa gana sobre el archivo y hay que quitarla ahí
- El refresco de Torre de Control ya no bloquea: antes `refrescar()` corría con `await` en el arranque (~22s consultando UPS/FedEx) y el servidor no aceptaba conexiones hasta terminarlo — en Render free ese costo se pagaba en cada despertar. Ahora va en segundo plano vía `lifespan`, y sus tramos síncronos corren en hilos (`asyncio.to_thread`), así que el refresco periódico cada `REFRESH_SECONDS` tampoco congela la API
- El entorno virtual local vive **fuera de OneDrive**, en `C:\dev\venvs\blis` (Python 3.13.14 de Microsoft Store), para que OneDrive no sincronice miles de archivos ni los deshidrate. Se arranca con `.\scripts\dev.ps1` (ver README). Los dos venv rotos que vivían dentro del repo (`.venv`, `.venv-1`) fueron borrados el 2026-08-29: apuntaban a un `python.exe` bajo `AppData\Local\Programs\Python\Python313\` que ya no existe — esa carpeta quedó como residuo sin ejecutable y el único Python del equipo es el de Microsoft Store. Recrearlo si hiciera falta: `python -m venv C:\dev\venvs\blis` y luego `C:\dev\venvs\blis\Scripts\python.exe -m pip install -r backend\requirements.txt`
- 4 módulos nuevos (Agrocalidad, Inventario LAG, Torre de Control, Auditoría de Etiquetas) corren sin credenciales reales configuradas en `.env`/Render — ver la tabla de rutas arriba para la lista exacta por módulo
- Fase 3b (bot RPA de tracking en Dartis) y el corte del webhook de Telegram a producción (Fase 4) quedaron deliberadamente pendientes — ver plan
- Documentación repartida entre `CLAUDE.md`, `BLIS_DOCUMENTACION.md`, `PRODUCT.md`, `AGENTS.md`, `README.md` — `CLAUDE.md`/`AGENTS.md` están al día; **`BLIS_DOCUMENTACION.md` quedó desactualizado**: cubre Proveedores pero no Armellini Post (agregado el 2026-08-23, un día después de la última regeneración del 2026-08-22) — falta regenerarlo
- El XML de operaciones de Expoflor trae `valortotal` y `precio` **inflados** (en el archivo del 2026-08-18: $3.470.872,46 contra $40.635,37 en `dartis_ventas`, y 747 de 751 cajas no cuadran contra tallos×precio). Se guardan en `precio_xml`/`valortotal_xml` solo para auditoría: para dinero se usa `dartis_ventas.total_dolares`
- `expoflor_operaciones_cajas.po` tiene cobertura parcial (~92%): viene vacío en cuentas mayoristas, así que el módulo permite digitarlo
- **OneDrive rompe git en este repo.** El proyecto vive dentro de `OneDrive - Universidad Nacional de Chimborazo`, y OneDrive deshidrata los archivos de `.git` («Archivos a petición»): los packs quedan como `ReparsePoint` y git falla con `fatal: mmap failed: Invalid argument` al hacer `push`. `git fetch` sí funciona — el problema es leer los packs locales. `attrib +P -U` sobre `.git` **no** lo resuelve: los fija pero siguen siendo reparse points. Workaround usado el 2026-08-23: copiar `.git` fuera de OneDrive y empujar con `git --git-dir=<copia> push origin main`. Arreglo de fondo: mover el repositorio fuera de OneDrive, o excluir la carpeta de la sincronización
- **Seguridad pendiente**: el token real de `LAG_PLACE_ORDER_TOKEN` fue pegado en texto plano durante la sesión donde se construyó Posteo de Inventario — rotarlo con Logiztik Alliance Group antes de dar por confiable ese flujo en producción

## Convenciones de código
- Ver `rules/coding-style.md`
- Ver `rules/security.md`
- Commits: `feat:`, `fix:`, `refactor:`, `docs:` (conventional commits)
- Nunca hardcodear credenciales — usar `backend/.env` (excluido del repo)
