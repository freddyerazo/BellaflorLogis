-- ============================================================
--  003_farms.sql
--  Tabla maestra de fincas / exportadoras
--  Normaliza los nombres OCR del bot hacia un nombre oficial
--  y vincula con el código postcosecha de Dartis.
-- ============================================================

CREATE TABLE IF NOT EXISTS farms (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    code                TEXT        UNIQUE NOT NULL,
    name                TEXT        NOT NULL,
    ocr_variants        TEXT[]      DEFAULT '{}',
    dartis_postcosecha  TEXT,
    active              BOOLEAN     DEFAULT TRUE,
    inactive_date       TIMESTAMPTZ,
    updated_at          TIMESTAMPTZ DEFAULT now(),
    created_at          TIMESTAMPTZ DEFAULT now()
);

INSERT INTO farms (code, name, ocr_variants, dartis_postcosecha) VALUES
('EXPOFLOR',
 'EXPOFLOR CIA. LTDA.',
 ARRAY[
   'EXPOFLOR CIA. LTDA.',
   'EXPOFLOR CIA LTDA.',
   'EXPOFLOR CIA LTDA',
   'EXPOFLOR CIA, LTDA.',
   'Exportadora de Flores Expoflor Cia Ltda',
   'EXPOFLOR'
 ],
 'EXPOFLOR'),

('OASISFLOWER',
 'OASISFLOWER SAS',
 ARRAY[
   'OASISFLOWER SAS',
   'OASISFLOWER S.A.S',
   'OASISFLOWER S.A.S.',
   'OASIS FLOWER SAS',
   'OASIS FLOWER S.A.S.',
   'Oasis Flower S.A.S.',
   'OASISFLOWER S AS'
 ],
 'OASIS'),

('AMAZINGROSES',
 'AMAZINGROSES CIA LTDA',
 ARRAY[
   'AMAZINGROSES CIA LTDA',
   'AMAZINGROSES CIA. LTDA.',
   'AMAZINGROSES CIA.LTDA.',
   'AMAZINGROSES CALTDA',
   'AMAZINGROSES CIA,LTDA',
   'Amazing Roses Cia Ltda',
   'AMAZINGROSES'
 ],
 'AMAZING')

ON CONFLICT (code) DO NOTHING;
