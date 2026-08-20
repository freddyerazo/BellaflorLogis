-- ============================================================
--  002_cargo_agencies.sql
--  Tabla maestra de agencias de carga logística
--  Normaliza los nombres OCR del bot de Telegram hacia un
--  nombre oficial único reutilizable en entregas y Dartis.
-- ============================================================

CREATE TABLE IF NOT EXISTS cargo_agencies (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    code         TEXT        UNIQUE NOT NULL,
    name         TEXT        NOT NULL,
    ocr_variants TEXT[]      DEFAULT '{}',
    type         TEXT        CHECK (type IN ('aerea', 'terrestre', 'ambas')) DEFAULT 'aerea',
    country      TEXT        DEFAULT 'Ecuador',
    active       BOOLEAN     DEFAULT TRUE,
    inactive_date TIMESTAMPTZ,
    updated_at   TIMESTAMPTZ DEFAULT now(),
    created_at   TIMESTAMPTZ DEFAULT now()
);

-- Datos iniciales: 12 agencias identificadas del análisis del sheet OCR
INSERT INTO cargo_agencies (code, name, ocr_variants, type) VALUES
('ONE',   'ONE TEAMCARGO',
  ARRAY['ONE Teamcargo','ONE TEAMCARGO','ONE TEAMCARGO S.A.','One Teamcargo SA'],
  'aerea'),
('PAC',   'PACIFIC AIR CARGO',
  ARRAY['Pacific Air Cargo','PACIFIC AIR CARGO','PACIFIC AIR CARGO S.A.'],
  'aerea'),
('VAL',   'VALUE CARGO',
  ARRAY['Value Cargo','VALUE CARGO','Value Cargo S.A.'],
  'aerea'),
('LDS',   'LDSEXPORT',
  ARRAY['LDSEXPORT','LDS EXPORT','LDS Export','ldsexport'],
  'aerea'),
('FRE',   'FRESH LOGISTICS CARGA',
  ARRAY['Fresh Logistics Carga','Fresh Flower Cargo','FRESH LOGISTICS CARGA'],
  'aerea'),
('LOG',   'LOGIZTIK ALLIANCE',
  ARRAY['LogiztikAlliance','Logiztik Alliance','LOGIZTIK ALLIANCE','LOGIZTIKALLIANCE'],
  'aerea'),
('DSV',   'DSV',
  ARRAY['DSV','DSV S.A.','DSV Air & Sea'],
  'aerea'),
('KN',    'KUEHNE+NAGEL',
  ARRAY['KUEHNE+NAGEL S.A.S.','Kuehne+Nagel','KUEHNE-NAGEL','KUEHNE NAGEL'],
  'aerea'),
('UPS',   'UPS / SAFTEC',
  ARRAY['UPS / SAFTEC','SAFTEC S.A.','UPS','SAFTEC'],
  'aerea'),
('GRN',   'GREENLOG',
  ARRAY['GREEN LOGISTICS GREENLOG S.A.S.','GREENLOG','Green Logistics'],
  'terrestre'),
('FLT',   'FLORAL TECH',
  ARRAY['FLORAL TECH','FLORALTECH','Floral Tech'],
  'terrestre'),
('REC',   'REAL CARGA',
  ARRAY['REAL CARGA','Real Carga'],
  'terrestre'),
('ALI',   'ALIANZA LOGISTIKA',
  ARRAY['ALIANZA LOGISTIKA','Alianza Logistika','ALIANZA LOGISTICA'],
  'aerea'),
('HPL',   'HPLAPOLLO',
  ARRAY['HPLAPOLLO','HPL APOLLO','HPL Apollo'],
  'aerea'),
('DCG',   'DIRECT CARGO',
  ARRAY['DIRECT CARGO','Direct Cargo','DirectCargo'],
  'terrestre'),
('FWF',   'FREIGHTWISE FORWARDING',
  ARRAY['FREIGHTWISE FORWARDING S.A','Freightwise Forwarding','FREIGHTWISE'],
  'aerea')
ON CONFLICT (code) DO NOTHING;
