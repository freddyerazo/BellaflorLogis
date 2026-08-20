-- 009_dartis_ventas_vendedor.sql
-- Agrega columna vendedor a dartis_ventas.
-- El formato Ventas Recetas no incluye vendedor; el formato Ventas clásico sí (vendedorPacking).
-- La columna es nullable para compatibilidad con ambos formatos.

ALTER TABLE dartis_ventas ADD COLUMN IF NOT EXISTS vendedor TEXT;

CREATE INDEX IF NOT EXISTS idx_dartis_ventas_vendedor ON dartis_ventas (vendedor);
