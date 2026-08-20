-- ============================================================
--  005_farm_postcosecha.sql
--  Tabla de códigos postcosecha vinculados a fincas.
--  Una finca puede tener múltiples postcosechas en Dartis.
-- ============================================================

-- Eliminar campo simple que ya no aplica
ALTER TABLE farms DROP COLUMN IF EXISTS dartis_postcosecha;

-- Tabla puente finca ↔ postcosecha
CREATE TABLE IF NOT EXISTS farm_postcosecha (
    id           UUID  PRIMARY KEY DEFAULT gen_random_uuid(),
    farm_id      UUID  NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    postcosecha  TEXT  NOT NULL,
    active       BOOLEAN DEFAULT TRUE,
    created_at   TIMESTAMPTZ DEFAULT now(),
    UNIQUE (farm_id, postcosecha)
);

-- Insertar postcosechas de las 3 fincas principales
INSERT INTO farm_postcosecha (farm_id, postcosecha)
SELECT id, 'BELLA6'      FROM farms WHERE code = 'EXPOFLOR'
ON CONFLICT DO NOTHING;

INSERT INTO farm_postcosecha (farm_id, postcosecha)
SELECT id, 'BOUQUETERA'  FROM farms WHERE code = 'EXPOFLOR'
ON CONFLICT DO NOTHING;

INSERT INTO farm_postcosecha (farm_id, postcosecha)
SELECT id, 'BELLA1'      FROM farms WHERE code = 'EXPOFLOR'
ON CONFLICT DO NOTHING;

INSERT INTO farm_postcosecha (farm_id, postcosecha)
SELECT id, 'OASISFLOWER' FROM farms WHERE code = 'OASISFLOWER'
ON CONFLICT DO NOTHING;

INSERT INTO farm_postcosecha (farm_id, postcosecha)
SELECT id, 'AMAZINGROSES' FROM farms WHERE code = 'AMAZINGROSES'
ON CONFLICT DO NOTHING;

-- Vista útil: postcosecha con nombre de finca
CREATE OR REPLACE VIEW v_farm_postcosecha AS
SELECT
    fp.id,
    fp.postcosecha,
    f.code   AS farm_code,
    f.name   AS farm_name,
    fp.active
FROM farm_postcosecha fp
JOIN farms f ON f.id = fp.farm_id
ORDER BY f.name, fp.postcosecha;
