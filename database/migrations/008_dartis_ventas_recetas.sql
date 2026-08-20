-- ============================================================
--  008_dartis_ventas_recetas.sql
--  Tabla única de ventas Dartis basada en Ventas Recetas.
--  Reemplaza la tabla dartis_ventas anterior.
-- ============================================================

DROP TABLE IF EXISTS dartis_ventas CASCADE;

CREATE TABLE dartis_ventas (
    id                  BIGSERIAL   PRIMARY KEY,
    fecha               DATE,
    dae                 TEXT,
    id_comercializadora INTEGER,
    id_pedido           INTEGER,
    empresa             TEXT,
    cliente             TEXT,
    destinatario        TEXT,
    postcosecha         TEXT,
    especie             TEXT,
    guia_madre          TEXT,
    guia_hija           TEXT,
    tipo_caja           TEXT,
    total_piezas        NUMERIC(12,6),
    total_tallos        INTEGER,
    total_dolares       NUMERIC(12,2),
    importado_at        TIMESTAMPTZ DEFAULT now(),
    UNIQUE (id_pedido, guia_madre, guia_hija, tipo_caja)
);

-- Índices para cruces frecuentes
CREATE INDEX IF NOT EXISTS idx_dartis_ventas_guia_madre  ON dartis_ventas (guia_madre);
CREATE INDEX IF NOT EXISTS idx_dartis_ventas_guia_hija   ON dartis_ventas (guia_hija);
CREATE INDEX IF NOT EXISTS idx_dartis_ventas_postcosecha ON dartis_ventas (postcosecha);
CREATE INDEX IF NOT EXISTS idx_dartis_ventas_fecha       ON dartis_ventas (fecha);
