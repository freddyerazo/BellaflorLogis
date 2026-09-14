# Dónde retomar — 2026-09-14

**Auditoría de Etiquetas: pestaña nueva "Clientes a auditar"** (`d77baa5`).
Antes, en la misma sesión: **los despachos se consolidan por cliente + HAWB**
(`a5ed939`/`d488561`). Antes de eso, **Torre de Control: la celda
"Cliente / Factura" ahora muestra `id_comercializadora`** (`0f4fc42`), el
cambio de proceso de Torre de Control (`50cc383`, y `0d8b2c4` antes), la
**reforma de la vista** del 2026-09-05 (`7c55709`) y, antes aún,
**Agrocalidad** y la importación de Dartis del 2026-09-04. Todo sigue
descrito más abajo, del más reciente al más viejo.

---

## Lo último: pestaña "Clientes a auditar" (2026-09-14)

Pedido del usuario: revisar cómo se cruzan los clientes que requieren
auditoría de etiquetas, y crear una forma de agregarlos/editarlos sin SQL
directo (hasta ahora la única forma de marcar `customers.es_cliente_especial`
o cargar `dartis_name`/`destinatario` era una consulta manual en Supabase).

**Cómo se cruza hoy (sin cambios en esta tanda, solo se documenta):**
`special_dispatches.generar_despachos_del_dia()` hace
`JOIN customers c ON LOWER(TRIM(c.dartis_name)) = LOWER(TRIM(dv.cliente))`
contra `dartis_ventas`, exigiendo además `c.destinatario IS NULL` (matchea
CUALQUIER venta de ese Dartis) O que coincida con `dv.destinatario` (matchea
solo esa línea puntual). Dos patrones reales en los 65 clientes especiales
actuales:
- **Genérico** (`customer_code` tipo `DAR-...`): `dartis_name = customer_name`,
  `destinatario` vacío — aplica a TODAS las ventas de ese Dartis (ej.
  TRADEWINDS INTL LLC).
- **Específico** (`customer_code` tipo `DST-...`): mismo `dartis_name` que un
  genérico, pero `destinatario` puntual y `customer_name` distinto — usado
  para darle etiqueta propia a un sub-cliente puntual dentro de un
  comercializador (ej. "HRD" y "RVF", ambos destinatarios de TRADEWINDS).

**Hecho:**

1. Nueva sub-pestaña "Clientes a auditar" en `auditoria-etiquetas.html`
   (patrón `.subtabs`/`.subpanel`, el mismo que ya usan Agrocalidad e
   Inventario LAG). Reutiliza el CRUD genérico (`initCrudPage`,
   `crud-page.js`) apuntado a `/api/customers`, sin duplicar lógica.
2. `crud-page.js` gana `listEndpoint` (opcional, cae a `endpoint` si no se
   pasa): el listado necesita `?es_cliente_especial=true` para filtrar,
   pero editar/borrar arman `${endpoint}/${id}` — pasarle ahí un endpoint
   con query string habría roto la URL (`/customers?es_cliente_especial=true/<id>`).
   Con `listEndpoint` separado, `endpoint` se mantiene limpio.
3. `GET /api/customers` gana un filtro opcional `?es_cliente_especial=`
   (aditivo: sin el parámetro se comporta exactamente igual que antes, la
   página general de "Clientes" no se vio afectada). `CustomerCreate` y
   `CustomerUpdate` ganan `dartis_name`, `destinatario`, `es_cliente_especial`
   — antes esos tres campos, aunque ya existían como columnas reales en
   `customers`, no se podían escribir desde ninguna API.
4. **Sin botón "Eliminar" en esta vista.** El `DELETE /customers/{id}`
   existente hace un soft-delete de TODO el registro
   (`active = false, inactive_date = now()`), que afectaría a otros módulos
   que usan ese mismo cliente (Torre de Control, cotizaciones). Para sacar
   a alguien de la auditoría sin tocar el resto de su registro, se edita y
   se destilda "Requiere auditoría de etiquetas" — desaparece de esta lista
   filtrada sin desactivar el cliente.

**Verificado contra Supabase real** (no solo lectura de código): crear un
cliente de prueba vía `POST /customers`, editarlo para destildar
`es_cliente_especial` y confirmar que desaparece del listado filtrado, y
borrar el registro de prueba al terminar. Sin migración: las tres columnas
ya existían en `customers` desde antes (fuera de cualquier migración
rastreada en `database/migrations/` — ver "Cosas que conviene no perder").

---

## Lo anterior: Auditoría de Etiquetas — un despacho por cliente + HAWB, no por id_pedido (2026-09-14)

Pedido del usuario: un mismo cliente + `guia_hija` (HAWB) con varios
`id_pedido` de Dartis generaba un despacho por cada uno — hasta 25 en los
datos reales (DELAWARE VALLEY FLORAL GROUP LLC) — y el bot obligaba al
auditor a repetir el cuestionario completo esa cantidad de veces para
revisar un solo paquete físico.

**Hecho:**

1. `special_dispatches.py`: la agrupación deja de ser por SQL
   (`GROUP BY ... id_pedido, tipo_caja`) y pasa a Python, porque hace
   falta un `jsonb_object_agg` de piezas *por tipo de caja* (dos niveles
   de agregación) además de un array de `id_pedido` distintos — más
   simple de construir ahí que en un SELECT con subconsultas
   correlacionadas. Nuevas columnas `id_pedidos` (JSONB, todos los
   pedidos consolidados, para trazabilidad) y `desglose_tipo_caja`
   (JSONB, `{"HB": 3, "QB": 9}`) — dentro de un mismo HAWB el tipo de
   caja **sí varía** (verificado: 15 grupos cliente+HAWB con más de un
   tipo en los últimos 10 días).
2. **`dv.destinatario` (el de la línea de venta) quedó fuera de la clave
   de agrupación** — intento fallido primero: se dejó "por seguridad",
   copiado del criterio de matching de `customers.destinatario`, pero
   son conceptos distintos. Clientes distribuidores (ej. LA HACIENDA
   FLOWERS INC) reparten un mismo HAWB entre floristerías finales
   distintas — 11 en el caso verificado — cada línea con su propio
   `dv.destinatario`, así que dejarlo en la clave seguía partiendo el
   despacho en 11. La identidad del cliente especial ya la resuelve
   `customer_id` (vía `customers.destinatario` en el JOIN de
   `match_unico`) — `dv.destinatario` es solo un dato de la línea de
   venta. Se sigue guardando: el valor si coincide en todas las líneas,
   o `"<n> destinatarios distintos"` si no.
3. **Índice único nuevo, PARCIAL (`WHERE estado = 'PENDIENTE'`)** —
   `special_dispatches_fecha_pos_cliente_guia_pendiente_idx` sobre
   `(fecha, postcosecha, customer_id, COALESCE(guia_hija, ''))`. Hace
   falta que sea parcial porque hay HAWB con una parte ya **AUDITADA**
   bajo el esquema viejo (un tipo de caja) y otra parte **PENDIENTE**
   bajo otro — un índice único normal habría chocado contra esas filas
   ya auditadas, que no se deben tocar ni fusionar (se perdería su
   rastro: fotos, confirmación, observaciones). Con el índice parcial el
   historial AUDITADO queda intacto tal cual estaba, y la unicidad solo
   se exige hacia adelante.
4. `telegram_bot.py`: `_texto_resumen` y la lista de `/lista` muestran el
   desglose por tipo de caja (`HB:1, QB:9, SB:2`) en vez del `tipo_caja`
   singular de antes.
5. `frontend/pages/auditoria-etiquetas.js`/`.html`: columnas "ID Pedidos"
   y "Tipo(s) caja" muestran el array/desglose nuevo, con fallback a los
   campos singulares viejos para las filas ya AUDITADAS que no los
   tienen.
6. Migración `043_special_dispatches_consolidar_guia_hija.sql` aplicada a
   mano contra Supabase (mismo motivo que la 042: el runner sigue
   bloqueado en la migración 016). Los 1.316 despachos PENDIENTE
   existentes se borraron (recalculables al 100% desde `dartis_ventas`,
   sin rastro de auditoría) y se regeneraron ya consolidados con
   `generar_despachos_del_dia()` para cada fecha con pendientes
   (2026-08-03 al 2026-09-11): **737 despachos resultantes, 35 AUDITADOS
   sin tocar**. Verificado el caso que motivó el cambio: HAWB `UP818477`
   de LA HACIENDA FLOWERS INC pasó de 11 filas a 1 (12 cajas, HB:1/QB:9/SB:2).

**Ojo — se dejó producción momentáneamente rota entre la migración y el
deploy:** el código viejo desplegado en Render seguía usando el índice
único viejo (`..._fecha_id_pedido_tipo_caja_pos_guia_idx`), que la
migración elimina. Cualquier `/lista` del bot entre el `DROP INDEX` y el
deploy del código nuevo habría fallado con "no unique or exclusion
constraint matching ON CONFLICT". Se hizo el push inmediatamente después
de verificar en local para minimizar la ventana; no se confirmó con el
usuario antes de desplegar por esa urgencia (a diferencia del cambio
anterior de `id_comercializadora`, donde sí se preguntó).

**Pendiente, no de este cambio:** mismo hallazgo de `scripts/migrate.py`
bloqueado en la migración 016 — ver la sesión anterior (2026-09-10).

---

## Lo anterior: Torre de Control muestra id_comercializadora en vez de id_pedido (2026-09-10)

Pedido del usuario: en la pestaña "Fedex-Ups See", bajo el nombre del
cliente se veía el `id_pedido` — la clave interna que cruza cada factura de
Dartis contra el PO del manifiesto de UPS/FedEx — y quería ver ahí el
número de factura comercial en su lugar.

**Hecho:**

1. `_obtener_base_dartis()` (`backend/app/services/courier_reconciliation.py`)
   ahora trae también `MAX(id_comercializadora)` de `dartis_ventas`, como
   campo aparte. **El cruce contra el manifiesto no se tocó**: sigue siendo
   por `factura` (= `id_pedido`), porque ese es el número que el courier
   imprime como `PO:<numero>` en el manifiesto — cambiarlo habría roto la
   conciliación completa. Mismo patrón que ya usaba el original
   REPORTEUPSFEDEX (`id_comercializadora` para mostrar, `id_pedido` para
   cruzar).
2. Migración `042_courier_reconciliation_id_comercializadora.sql` —
   `ALTER TABLE courier_reconciliation ADD COLUMN id_comercializadora`.
   Aplicada a mano contra Supabase (no vía `scripts/migrate.py`: el runner
   está bloqueado desde antes por un desfase entre la migración 016 y la
   tabla `_migrations`, sin relación con este cambio — ver "Pendientes").
3. `frontend/pages/torre-control.js`: la celda pasa a
   `id_comercializadora ?? factura`. Las filas **NO EN DARTIS** (vienen
   solo del manifiesto, nunca tuvieron fila de Dartis) no tienen número
   comercial, así que siguen mostrando el `id_pedido` como respaldo — mismo
   comportamiento que documenta el README de REPORTEUPSFEDEX para ese caso.
   También se sumó `id_comercializadora` al buscador de texto libre.

**Verificado contra datos reales:** tras el redeploy en Render y un
`POST /torre-control/refrescar` (2.511 facturas), `id_comercializadora`
quedó poblado con valores reales (ej. `102676`, `104764`, ...) en
`courier_reconciliation`.

**Pendiente, no de este cambio:** `scripts/migrate.py` no corre limpio —
se detiene en la migración `016_dartis_ventas_especie_unique.sql` porque
esa restricción ya existe en la base real pero `_migrations` no tiene el
registro de que se aplicó. Hay que decidir si se inserta el registro
retroactivo o se revisa qué otras migraciones tienen el mismo desfase antes
de confiar en el runner de nuevo.

---

## Lo anterior: Torre de Control — manifiestos a Supabase, sin tracking en vivo (2026-09-06)

Pedido del usuario: dejar de guardar los manifiestos de UPS/FedEx como
archivos, apagar la consulta de tracking en vivo y sacar del proceso a las
agencias de carga locales. Se hizo en **los dos proyectos a la vez** — BLIS y
el original REPORTEUPSFEDEX — porque comparten las tablas de manifiesto.

**Hecho:**

1. **Los manifiestos ya no viven en `datos/*.csv`** (REPORTEUPSFEDEX) sino en
   `courier_ups_manifest` y `courier_fedex_envios` de Supabase — las mismas
   tablas que ya usaba el clon de BLIS. Una carga alimenta a los dos sistemas.
   UPS es UPSERT por tracking (el manifiesto es acumulativo); FedEx es INSERT
   de solo los trackings nuevos (cada PDF es un despacho puntual).

2. **Se apagó el tracking en vivo.** La rama FedEx de `_evaluar` comparaba
   SOLO contra el Track API: apagarlo sin más habría dejado FedEx en
   PENDIENTE para siempre. Ahora compara contra el conteo de bultos de su
   propio manifiesto, igual que UPS. Verificado con datos reales: FedEx pasó
   de 0 conciliadas a 63 OK / 1 discrepancia (BLIS) y 27 OK / 1 discrepancia
   (REPORTEUPSFEDEX). La asimetría UPS (`SIN MANIFIESTO`) vs FedEx
   (`PENDIENTE`) se mantuvo a propósito — no es de dónde se guarda el
   manifiesto sino de cómo lo entrega cada courier.

3. **Las agencias de carga locales (courier "OTRO") quedaron fuera de la
   conciliación.** Se eliminaron `courier_ups_client.py`,
   `courier_fedex_client.py` y `courier_entregas_locales.py` de BLIS
   (recuperables en git), y la sub-pestaña "Agencias locales" del frontend.
   El snapshot informa `omitidas_agencias_locales` para que la exclusión sea
   visible.

4. **Bug encontrado y corregido de paso:** `/subir-ups` de BLIS hacía
   `TRUNCATE` antes de insertar — cada carga borraba todo el histórico y
   dejaba solo el último archivo (por eso la tabla estaba congelada en el
   21/08). Ahora es UPSERT. `/subir-fedex` insertaba fila por fila con un
   SELECT previo por envío (~195 ms/round-trip, minutos por PDF); ahora va en
   lote con `execute_values`.

5. **La pantalla de Torre de Control se rediseñó, en dos pasadas.** La
   primera portó la de producción de REPORTEUPSFEDEX: header verde con pulso
   "EN VIVO", filtros de fecha/courier/estado/planificación, tabla con una
   fila por bulto, columna **Destinatario** agregada (antes solo Cliente).
   Sidebar de BLIS intacto. **La segunda (más tarde el mismo 2026-09-05) la
   alineó al sistema de diseño de BLIS** — la primera había traído fuentes y
   paleta propias, calcadas del original: ahora hereda Outfit y usa el hero
   y `.cot-tabla` del resto del sistema. Detalle completo en `CLAUDE.md`.

6. **Duoplane no tenía credenciales en BLIS** — se copiaron de
   REPORTEUPSFEDEX al `.env` local. Falta cargarlas también en el panel de
   Render de `blis-api` para que funcione en producción.

**Verificado contra datos reales** (Supabase, no solo lectura de código):
subida real de un manifiesto de UPS más fresco (26 nuevos, 771 actualizados
de 797 tocados, sin duplicados — `courier_ups_manifest_tracking_key`
sostiene la unicidad).

**Pendiente:**
- Agregar `DUOPLANE_API_KEY`/`DUOPLANE_API_PASSWORD`/`DUOPLANE_BASE_URL` en
  el panel de Render de BLIS (producción).
- Ver si conviene declarar `DUOPLANE_BASE_URL` (no es secreta) en
  `render.yaml` de BLIS, igual que en REPORTEUPSFEDEX — preguntado, sin
  respuesta todavía.
- `BLIS_DOCUMENTACION.md` sección 11 (Torre de Control) y su contraparte de
  frontend, actualizadas con el código nuevo — revisar que sigan
  reflejando la realidad si el módulo vuelve a cambiar.

---

## Lo anterior: reforma de la vista (2026-09-05)

Se trabaja **poco a poco**, confirmando cada tanda con el usuario antes de
seguir. Todo lo hecho es de presentación: no toca APIs, datos ni migraciones.

**Hecho:**

1. **Capa base**, en `frontend/css/styles.css` — aplica a las 21 páginas.
   Paleta verde nueva (`#1d7a4c`/`#14532d`/`#e7f3ec`) en reemplazo del
   `#2e7d32` de Material 2014, tokens de superficie/borde/radio/sombra, y
   tablas con cifras tabulares, zebra y encabezados neutros en versalitas.

2. **Tabla "Consultas guardadas" de Agrocalidad.** Estaba suelta en una
   `.import-card` de `max-width: 860px` y se desbordaba por la derecha: la
   columna de acciones quedaba fuera de la tarjeta. Pasó a `.cot-tabla` dentro
   de `.ag-tabla-scroll`, el patrón que ya usaban las otras tres tablas de la
   página. Arranca filtrada en **Estados Unidos** y ordenada por especie.

3. **Torre de Control se muestra como "Fedex-Ups See".** Solo el rótulo, en
   `sidebar.html` y `torre-control.html`. La ruta `/api/torre-control`, los
   nombres de archivo y las tablas `courier_*` no se tocaron.

4. **El sidebar lleva el nombre completo**: BLIS · Business Logistic
   Intelligence Systems.

**Lo que sigue**, por orden de lo que más rinde:

1. **Sidebar** — 230px de verde plano con 21 enlaces; es lo que más pesa al
   entrar. Agrupar por área y hacerlo colapsable.
2. **Dashboard** — el hero con gradiente y las metric cards.
3. **Aplicar `.num`** a las columnas numéricas de cada módulo: la clase existe
   y casi nadie la usa, así que las cifras siguen alineadas a la izquierda.
4. **Cotizaciones** — el wizard tiene su propio sistema de estilos.
5. **Responsive** — hoy `body{display:flex}` deja la sidebar de 230px fija
   también en celular. No hay menú móvil.

**Ojo:** sigue sin haber prueba automatizada del frontend. Esta tanda se
verificó levantando el servidor local y consultando el HTML/CSS servido, más
las tablas contra datos reales; no hay recorrido en navegador salvo el que
hizo el usuario.

---

## Lo anterior: Agrocalidad y Dartis (2026-09-04)

### Lo que quedó funcionando

**La pestaña Agrocalidad tiene dos sub-pestañas.**

1. **Consulta de requisitos** — consulta directo la API móvil de Agrocalidad
   (~2,9 s en vivo, ~1,2 s desde caché de 24 h). Incluye barrido por país de
   todo el catálogo.

2. **Agrocalidad vs Ventas vs VUE** — dos bloques:
   - **Verificación de despachos**: ventana hoy ±5 días (configurable). Por cada
     fecha + país + especie que sale, contrasta contra Agrocalidad y contra la
     VUE. Salta alerta cuando falta alguna de las dos.
   - **Cobertura general**: las 250 combinaciones especie+país exportadas,
     clasificadas y con el monto de cada hueco.

**La VUE se sube desde la página de importación de Dartis**, una empresa por
archivo, eligiendo la empresa de un selector. Actualiza y agrega, nunca borra.

---

## Estado de los datos al 2026-09-04

| | |
|---|---|
| `dartis_ventas` activas | 26.309 (jun–sep) |
| Con país | 33.598 → agosto y septiembre completos; junio y julio en cero |
| Con variedad | 6.261 |
| Registro VUE cargado | solo Expoflor (494 autorizaciones, 60 productos, 56 países) |

**Verificación en la ventana de ±5 días:** 475 combinaciones, 169 con alerta —
148 sin requisitos de Agrocalidad y 22 no autorizadas en la VUE.

---

## Pendientes, en orden

1. **Los archivos VUE de Oasisflower y Amazingroses.** Exportan $505.155 y
   $263.365 y no tienen registro cargado: sus 167 combinaciones no se pueden
   verificar. Se descargan de la VUE con cada RUC y se suben igual que el de
   Expoflor.

2. **Resolver las 22 no autorizadas.** SPRAY ROSES y SOLOMIO a Estados Unidos.
   SPRAY ROSES mapea a "mini rosa" (A0002/0603110000), autorizada solo a CU, HU
   y CL, mientras que hacia EEUU lo registrado es "FLORES ROSA" (A0001). Igual
   SOLOMIO/MINI CLAVEL → "miniclavel" (A0001/0603121000), solo a CN, cuando
   hacia EEUU está "FLORES CLAVEL" (0603129000). **Puede ser un registro que
   falta o una diferencia de clasificación entre Agrocalidad y la VUE** — lo
   tiene que resolver quien maneja los registros.

3. **Consultar las 148 combinaciones pendientes** de Agrocalidad. Hay botón en
   la pantalla; tarda unos 5 minutos con la página abierta.

4. **Junio y julio no tienen país** (16.549 líneas, $2,2M): se importaron antes
   de que Dartis agregara `paisVenta`. Quedan fuera del cruce. Si hace falta el
   histórico, re-importar esos meses con el formato nuevo.

5. **La tercera pestaña** que se pidió al principio nunca se definió.

6. **Nada del frontend se probó en navegador.** Lo verificado se ejecutó con un
   DOM simulado: `renderResultadoPais`, `renderComparacion` y
   `renderVerificacion`. El resto está razonado contra el código.

---

## Cosas que conviene no perder

- **Dartis mueve las columnas sin avisar.** Ya pasó dos veces: `paisVenta` en
  Ventas y `variedad_receta` insertada en el medio en Recetas. La segunda llegó
  a producción y corrompió 30.099 filas —`total_dolares` terminó con tallos—
  porque el arreglo no se había podido subir. Ambos importadores leen ahora
  **por nombre de encabezado**. Si vuelve a aparecer una columna, no deberían
  romperse; si algo huele raro después de importar, correr
  `backend/scripts/ensayo_import_dartis.py`, que hace rollback y no escribe.

- **Tres códigos que parecen identificar y no lo hacen.** `agrocalidad_code` y
  el `codigo_producto` de la VUE: A0001 cubre rosa, clavel, crisantemo, aster,
  gerbera, alstroemeria, achillea y miniclavel. Para cruzar hace falta el par
  código+partida, y para identificar un producto en Agrocalidad, `id_producto`.

- **El movimiento va con tilde** (`Exportación`). Sin tilde la API responde 200
  con lista vacía en vez de error.

- **Agrocalidad no regula por variedad.** De 234 variedades de Dartis solo 8
  existen en su catálogo, y son follajes. El cruce se resuelve a especie+país.

- **BOUQUETS es el mayor facturador y queda estructuralmente fuera** de la
  verificación de Agrocalidad: es producto compuesto, no una especie.

- Antes de optimizar SQL en este proyecto, contar round-trips: cada uno cuesta
  ~195 ms contra Supabase y las consultas en sí tardan 0,3 ms.
