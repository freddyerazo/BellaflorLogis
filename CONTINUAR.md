# Dónde retomar — 2026-09-05

**Reforma de la vista**, primera tanda. Commiteado y subido (`7c55709`).
Antes de eso, el módulo **Agrocalidad** y la importación de Dartis, que siguen
como quedaron el 2026-09-04 y se describen más abajo.

---

## Lo último: reforma de la vista (2026-09-05)

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
