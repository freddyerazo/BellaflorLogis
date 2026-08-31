-- ============================================================
--  035_dartis_ventas_variedad.sql
--  Variedad de la receta en las ventas.
--
--  El archivo "Ventas Recetas" de Dartis paso a traer `variedad_receta`
--  INSERTADA EN EL MEDIO (posicion 9), lo que corrio guia_madre, guia_hija,
--  tipo_caja y los tres totales un lugar a la derecha. Por eso el importador
--  ahora ubica las columnas por nombre de encabezado y no por posicion.
--
--  OJO CON EL GRANO: la clave unica de dartis_ventas es
--  (id_pedido, guia_madre, guia_hija, tipo_caja, especie), que NO incluye la
--  variedad. Medido sobre el archivo del 2026-08-30: 9.511 filas de datos
--  colapsan en 2.017 claves, y 702 de esas claves traen mas de una variedad
--  (un pedido de BOUQUETS llega a tener 53 variedades distintas, por ser un
--  producto compuesto). Mientras la clave no cambie, la columna guarda la
--  variedad de UNA de las lineas agrupadas, no todas.
-- ============================================================

ALTER TABLE dartis_ventas
    ADD COLUMN IF NOT EXISTS variedad_receta TEXT;

COMMENT ON COLUMN dartis_ventas.variedad_receta IS
    'Variedad de la columna variedad_receta del archivo Ventas Recetas. La clave unica de la tabla no incluye la variedad, asi que en las lineas que agrupan varias (702 de 2.017 en el archivo del 2026-08-30) este campo guarda solo una de ellas.';
