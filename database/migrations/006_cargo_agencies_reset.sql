-- ============================================================
--  006_cargo_agencies_reset.sql
--  Reconstruye cargo_agencies con los nombres exactos de Dartis
--  como referencia oficial (campo dartis_name = name).
-- ============================================================

TRUNCATE TABLE cargo_agencies RESTART IDENTITY CASCADE;

INSERT INTO cargo_agencies (code, name, dartis_name, ocr_variants, type) VALUES

('ALI', 'ALIANZA LOGISTIKA',
  'ALIANZA LOGISTIKA',
  ARRAY['ALIANZA LOGISTIKA','Alianza Logistika','ALIANZA LOGISTICA','LogiztikAlliance','Logiztik Alliance','LOGIZTIKALLIANCE'],
  'aerea'),

('APO', 'APOLLO FREIGHT ECUADOR',
  'APOLLO FREIGHT ECUADOR',
  ARRAY['APOLLO FREIGHT ECUADOR','Apollo Freight Ecuador','HPLAPOLLO','HPL APOLLO','HPL Apollo'],
  'aerea'),

('CHP', 'CHAMPION CARGO ECUADOR',
  'CHAMPION CARGO ECUADOR',
  ARRAY['CHAMPION CARGO ECUADOR','Champion Cargo Ecuador','CHAMPION CARGO'],
  'aerea'),

('DSV', 'DSV-AIR&SEA S.A.',
  'DSV-AIR&SEA S.A.',
  ARRAY['DSV-AIR&SEA S.A.','DSV','DSV S.A.','DSV Air & Sea'],
  'aerea'),

('FDX', 'FEDEX',
  'FEDEX',
  ARRAY['FEDEX','FedEx','FEDEX ECUADOR','Fed Ex'],
  'aerea'),

('FLC', 'FLOWERCARGO',
  'FLOWERCARGO',
  ARRAY['FLOWERCARGO','FLOWERCARGO S.A.','Flower Cargo','FLORAL TECH','FLORALTECH'],
  'aerea'),

('FRS', 'FRESH LOGISTIC',
  'FRESH LOGISTIC',
  ARRAY['FRESH LOGISTIC','Fresh Logistics Carga','Fresh Flower Cargo','FRESH LOGISTICS CARGA','Fresh Logistics'],
  'aerea'),

('GRN', 'GREEN LOGISTICS GREENLOG S.A.S.',
  'GREEN LOGISTICS GREENLOG S.A.S.',
  ARRAY['GREEN LOGISTICS GREENLOG S.A.S.','GREENLOG','Green Logistics','GREEN LOGISTICS'],
  'terrestre'),

('KN',  'KUEHNE-NAGEL',
  'KUEHNE-NAGEL',
  ARRAY['KUEHNE-NAGEL','KUEHNE+NAGEL S.A.S.','Kuehne+Nagel','KUEHNE NAGEL','Kuehne-Nagel'],
  'aerea'),

('PAC', 'PACIFIC CARGO',
  'PACIFIC CARGO',
  ARRAY['PACIFIC CARGO','Pacific Air Cargo','PACIFIC AIR CARGO','PACIFIC AIR CARGO S.A.'],
  'aerea'),

('SFT', 'SAFTEC',
  'SAFTEC',
  ARRAY['SAFTEC','SAFTEC S.A.','UPS / SAFTEC'],
  'aerea'),

('UPS', 'UPS',
  'UPS',
  ARRAY['UPS','UPS ECUADOR','UPS / SAFTEC'],
  'aerea'),

('VAL', 'VALUE CARGO',
  'VALUE CARGO',
  ARRAY['VALUE CARGO','Value Cargo','Value Cargo S.A.'],
  'aerea')

ON CONFLICT (code) DO UPDATE SET
    name         = EXCLUDED.name,
    dartis_name  = EXCLUDED.dartis_name,
    ocr_variants = EXCLUDED.ocr_variants,
    type         = EXCLUDED.type,
    updated_at   = now();
