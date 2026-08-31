-- ============================================================
--  034_dartis_ventas_pais.sql
--  Pais de destino en las ventas, para poder cruzarlas contra los requisitos
--  de Agrocalidad (que son por pais) y contra VUE.
--
--  El archivo "Ventas" de Dartis paso a traer la columna `paisVenta`
--  (BAHREIN, CANADA, ...). Hasta ahora `dartis_ventas` no tenia ningun dato
--  de pais: solo `cliente` y `destinatario`, que son nombres de empresa.
--
--  Se guardan las dos cosas:
--    pais_venta -> el texto tal como viene del archivo, sin normalizar
--    country_id -> la referencia a countries, resuelta por nombre
--  El texto crudo se conserva para poder re-resolver el mapeo si aparece un
--  pais escrito distinto, sin tener que volver a importar.
-- ============================================================

ALTER TABLE dartis_ventas
    ADD COLUMN IF NOT EXISTS pais_venta TEXT,
    ADD COLUMN IF NOT EXISTS country_id UUID REFERENCES countries(id);

COMMENT ON COLUMN dartis_ventas.pais_venta IS
    'Pais de destino tal como viene en la columna paisVenta del archivo Ventas de Dartis. Texto crudo, sin normalizar.';

COMMENT ON COLUMN dartis_ventas.country_id IS
    'countries.id resuelto desde pais_venta al importar. NULL si el nombre no matcheo ningun pais del catalogo.';

CREATE INDEX IF NOT EXISTS idx_dartis_ventas_country
    ON dartis_ventas (country_id)
    WHERE country_id IS NOT NULL;
