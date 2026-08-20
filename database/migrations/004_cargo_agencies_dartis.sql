-- ============================================================
--  004_cargo_agencies_dartis.sql
--  Agrega campo dartis_name a cargo_agencies y sincroniza
--  con los valores reales del campo agenciaCarga de Dartis.
-- ============================================================

ALTER TABLE cargo_agencies
    ADD COLUMN IF NOT EXISTS dartis_name TEXT;

-- Actualizar dartis_name en registros existentes
UPDATE cargo_agencies SET dartis_name = 'ALIANZA LOGISTIKA'              WHERE code = 'ALI';
UPDATE cargo_agencies SET dartis_name = 'DSV-AIR&SEA S.A.'               WHERE code = 'DSV';
UPDATE cargo_agencies SET dartis_name = 'KUEHNE-NAGEL'                   WHERE code = 'KN';
UPDATE cargo_agencies SET dartis_name = 'UPS'                            WHERE code = 'UPS';
UPDATE cargo_agencies SET dartis_name = 'VALUE CARGO'                    WHERE code = 'VAL';
UPDATE cargo_agencies SET dartis_name = 'GREEN LOGISTICS GREENLOG S.A.S.' WHERE code = 'GRN';
UPDATE cargo_agencies SET dartis_name = 'PACIFIC CARGO'                  WHERE code = 'PAC';
UPDATE cargo_agencies SET dartis_name = 'FLOWERCARGO'                    WHERE code = 'FLT';
UPDATE cargo_agencies SET dartis_name = 'SAFTEC'                         WHERE code = 'UPS';

-- Insertar agencias que existen en Dartis pero no en la tabla
INSERT INTO cargo_agencies (code, name, dartis_name, ocr_variants, type) VALUES
('APO', 'APOLLO FREIGHT ECUADOR',
  'APOLLO FREIGHT ECUADOR',
  ARRAY['APOLLO FREIGHT ECUADOR','Apollo Freight','HPLAPOLLO','HPL APOLLO'],
  'aerea'),
('CHP', 'CHAMPION CARGO ECUADOR',
  'CHAMPION CARGO ECUADOR',
  ARRAY['CHAMPION CARGO ECUADOR','Champion Cargo'],
  'aerea'),
('FDX', 'FEDEX',
  'FEDEX',
  ARRAY['FEDEX','FedEx','FEDEX ECUADOR'],
  'aerea'),
('FLC', 'FRESH LOGISTICS CARGA',
  'FRESH LOGISTIC',
  ARRAY['Fresh Logistics Carga','Fresh Flower Cargo','FRESH LOGISTICS CARGA','FRESH LOGISTIC'],
  'aerea')
ON CONFLICT (code) DO UPDATE SET
    dartis_name  = EXCLUDED.dartis_name,
    ocr_variants = EXCLUDED.ocr_variants,
    updated_at   = now();
