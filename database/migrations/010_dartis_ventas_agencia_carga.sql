-- 010_dartis_ventas_agencia_carga.sql
-- Agrega columna agencia_carga a dartis_ventas.
-- Se rellena cruzando con el formato Ventas clásico por id_pedido.

ALTER TABLE dartis_ventas ADD COLUMN IF NOT EXISTS agencia_carga TEXT;

CREATE INDEX IF NOT EXISTS idx_dartis_ventas_agencia_carga ON dartis_ventas (agencia_carga);
