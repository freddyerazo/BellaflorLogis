-- 007_farm_postcosecha_amazing_bfexpoflor.sql
-- Agrega postcosechas AMAZING y BF-EXPOFLOR detectadas en Dartis

INSERT INTO farm_postcosecha (farm_id, postcosecha)
SELECT id, 'AMAZING' FROM farms WHERE code = 'AMAZINGROSES'
ON CONFLICT DO NOTHING;

INSERT INTO farm_postcosecha (farm_id, postcosecha)
SELECT id, 'BF-EXPOFLOR' FROM farms WHERE code = 'EXPOFLOR'
ON CONFLICT DO NOTHING;
