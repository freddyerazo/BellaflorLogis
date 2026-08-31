# Dónde retomar — 2026-08-31

Trabajo en curso sobre el módulo **Agrocalidad** y la **importación de Dartis**.
Lo cerrado está commiteado y en producción; lo que quedó a medio camino está
abajo, con lo que falta hacer y por qué.

---

## ⚠️ Lo primero: hay cambios SIN COMMITEAR y SIN VERIFICAR

```
 M backend/app/api/dartis_import.py
?? database/migrations/035_dartis_ventas_variedad.sql
```

**La migración 035 YA ESTÁ APLICADA en Supabase** (la columna
`dartis_ventas.variedad_receta` existe, con 0 filas cargadas), pero el archivo
`.sql` no está commiteado. Si alguien clona el repo hoy, la base tiene una
columna que las migraciones del repo no explican.

**El importador modificado NO se probó.** El ensayo con rollback contra los
archivos reales quedó a mitad de camino. **No subir archivos por la pantalla
hasta correrlo**, porque el importador toca 24.388 filas.

### Cómo verificarlo antes de seguir

Hay un script de ensayo en el scratchpad de la sesión:
`scratchpad/ensayo_import.py` — corre `_import_recetas` y `_enrich_ventas`
contra los archivos reales dentro de una transacción con **rollback**, así que
no escribe nada. Si ya no está, se rehace: abrir los dos workbooks, llamar a
las dos funciones dentro de `conn.begin()` y hacer `trans.rollback()` al final.

Archivos con los que se estaba probando:

```
C:/Users/coordinacion/OneDrive - BELLAFLOR GROUP INC/BFG/Downloads/
    Ventas Recetas2026-08-30 21_45_43.xlsx   (16 columnas, CON variedad_receta)
    Ventas Recetas2026-08-29 21_02_28.xlsx   (15 columnas, sin variedad)
    Ventas2026-08-30 20_58_26.xlsx           ( 9 columnas, con paisVenta)
```

Qué mirar en el ensayo: que `tipo_caja` no quede con números, que `guia_madre`
no quede con nombres de variedad, y que `total_tallos` no quede en NULL. Los
tres serían señal de que el mapeo de columnas se corrió.

---

## Qué se hizo hoy (commiteado y en producción)

### Agrocalidad dejó de scrapear

La app oficial AGRO Móvil resultó tener un backend REST/JSON en el mismo
dominio que el sitio protegido por Imperva, sin captcha ni bloqueo. Se
descubrió leyendo `libapp.so` del APK (la app es Flutter).

La pestaña pasó de 30-90 s a **~2,9 s** en vivo y **~1,2 s** reutilizando
resultado guardado. Desaparecieron GitHub Actions, Playwright, la cola
`agrocalidad_requests`, el polling y `GITHUB_TOKEN` — que era justo lo que
tenía la pestaña colgada.

**Trampa que hay que recordar:** el movimiento va con tilde (`Exportación`).
Sin tilde el servicio responde 200 con lista vacía en vez de error.

### Sub-pestañas

Se dividió en "Consulta de requisitos" y "Agrocalidad vs Ventas vs VUE",
con el patrón `.subtabs`/`.subpanel` que ya usaban inventario-lag y
torre-control.

### Países

`countries` quedó con los 255 países de Agrocalidad (`id_localizacion_agrocalidad`,
`nombre_agrocalidad`), más los 2 bloques comerciales (Unión Europea, CEEA) que
Agrocalidad trata como destino y no están en su catálogo de países. Se
insertaron con `active = false` para no aparecer en los listados del resto.

`cod_agroca` es **ISO 3166-1 alfa-2, NO un dato de Agrocalidad** — su API no
publica códigos de país. 251 de 257 resueltos.

### País en las ventas

El archivo Ventas trae `paisVenta`. Se agregaron `pais_venta` y `country_id`
a `dartis_ventas`. Del archivo del 30/08: **2.017 filas con país, 20 de 20
países resueltos**, cubriendo del 24 al 28 de agosto (1.040 de 12.368 pedidos).

---

## El problema de fondo que apareció: Dartis mueve las columnas

El importador leía por **posición fija**. Dartis agregó columnas dos veces:

- `paisVenta` en Ventas → corrió `vendedorPacking` un lugar. Con el código
  viejo, importar habría escrito nombres de país dentro de `vendedor` en las
  24.042 filas.
- `variedad_receta` en Recetas, **insertada en el medio** (posición 9) → corrió
  `guia_madre`, `guia_hija`, `tipo_caja` y los tres totales. `tipo_caja` ("QB")
  habría terminado en `total_piezas`.

Ambos importadores ahora ubican las columnas **por nombre de encabezado**
(`_mapear_columnas`), con dos detalles que costaron encontrar:

1. El encabezado de Dartis viene **partido en dos filas**: los nombres de campo
   arriba y los subtítulos del total (piezas/tallos/dólares) abajo. El mapeo
   mira ambas.
2. La clave obligatoria (`IdPedido`) **tiene que estar en la fila del
   encabezado**. Al principio se aceptaba encontrarla en la siguiente, y
   entonces una fila vacía anterior pasaba por encabezado y devolvía un mapeo
   incompleto — los totales quedaban sin mapear.

Verificado que los tres formatos mapean bien: Recetas nuevo (16 campos),
Recetas viejo (15, sin variedad, retrocompatible) y Ventas (4).

---

## La decisión que se tomó sobre la variedad

La clave única de `dartis_ventas` es
`(id_pedido, guia_madre, guia_hija, tipo_caja, especie)` — **no incluye la
variedad**. Medido sobre el archivo del 30/08: las 9.511 filas colapsan en
2.017 claves, y **702 de esas claves traen más de una variedad**. Un pedido de
BOUQUETS llega a **53 variedades** distintas, por ser producto compuesto.

**Decisión: se mantiene el grano y `variedad_receta` guarda la lista completa**
de variedades de esa línea, separadas por coma. No se pierde información, no se
multiplican las filas y no se toca ninguno de los 6 módulos que leen
`dartis_ventas` (Torre de Control, Armellini, Auditoría de Etiquetas, Expoflor,
entregas locales, conciliación).

Se descartó cambiar el grano a variedad: habría llevado la tabla de 24.388 a
unas 114.000 filas y habría exigido revisar esos 6 módulos para que no dupliquen.

Ese cambio ya está escrito en `_import_recetas` pero **es exactamente lo que
falta verificar**.

---

## Pendientes, en orden

1. **Correr el ensayo con rollback** contra los tres archivos y revisar los
   controles. Sin eso no conviene importar.
2. **Commitear** `dartis_import.py` y la migración 035.
3. **Importar** los dos archivos por la pantalla y revisar que `variedad_receta`
   se haya llenado (hoy hay 0 filas con variedad).
4. **VUE.** No hay ningún dato en BLIS: ni tablas, ni columnas. Falta que
   Bellaflor pase una muestra del archivo de la Ventanilla Única para armar el
   importador. Es la pata que falta de la pestaña de comparación.
5. **Tercera pestaña.** Se pidieron tres y solo se definieron dos; la tercera
   quedó sin decidir.
6. **Actualizar la comparación a especie+país.** Hoy la pestaña cruza solo por
   especie porque se armó cuando no había país. Con el país cargado ya se puede:
   de **182 combinaciones especie+país exportadas** esa semana, 82 tienen
   requisitos averiguados, **92 están mapeadas pero nunca se consultaron** y 7
   no tienen mapeo.

---

## Cosas sueltas que conviene no perder

- **BOUQUETS factura $2.037.431 —el primero por lejos— y no tiene mapeo en
  Agrocalidad**, por ser producto compuesto y no una especie. Aparece en la
  pestaña de comparación.
- El archivo `Ventas2026-08-30 20_58_26.xlsx` se coló en el commit `e93526d` y
  después se sacó del tracking. **Sigue en el historial de git** — si molesta,
  sacarlo exige reescribir commits ya empujados.
- `codigo_producto` de Agrocalidad **no identifica un producto**: el 0001 lo
  comparten rosa, clavel, crisantemo, aster, gerbera y alstroemeria. Para
  cruzar se usa `id_producto`.
- Hay 13 especies sin mapear a Agrocalidad. Tres ni siquiera son flores
  (`CARTON BOX`, `STAND - COUNTER`, `BIOMASA CAÑAMO EN SECO`).
- Regla que salió del perfilado: **antes de optimizar SQL, contar
  round-trips**. Cada uno cuesta ~195 ms contra Supabase y las consultas en sí
  tardan 0,3 ms.
- **Nada del frontend se probó en navegador** en toda esta tanda. Lo único
  ejecutado fue `renderResultadoPais`, con un DOM simulado.
