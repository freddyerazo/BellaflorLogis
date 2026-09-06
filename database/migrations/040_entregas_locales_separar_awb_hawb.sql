-- ============================================================
--  040_entregas_locales_separar_awb_hawb.sql
--  "numero_guia" (migracion 039) en realidad puede traer dos numeros
--  distintos de guia aerea: AWB/MAWB (numero maestro de la aerolinea --
--  son el mismo concepto, MAWB es solo el nombre completo de AWB, no un
--  tercer campo) y HAWB (house, del consolidador/forwarder, que SI puede
--  diferir del AWB).
--
--  Verificado sobre las 3.515 filas reales: 1.212 recibos traen AWB y HAWB
--  a la vez, y 232 de ellos con valores claramente distintos bajo cada
--  etiqueta (ej. AWB 14511884596 / HAWB 1096850 -- no son el mismo numero
--  repetido). Un solo campo "numero_guia" perderia esa distincion.
--
--  Nota: esta migracion originalmente agrego tambien una columna "mawb"
--  separada; se corrigio en el mismo dia (ver aplicacion posterior
--  "entregas_locales_mawb_es_awb") porque MAWB = AWB, no un tercer campo.
--  El archivo ya refleja el estado final, sin la columna mawb.
-- ============================================================

ALTER TABLE entregas_locales_detalle
  ADD COLUMN IF NOT EXISTS awb TEXT,
  ADD COLUMN IF NOT EXISTS hawb TEXT;

-- Si algo ya se cargo con el campo generico, se migra a awb por defecto
-- (es el mas comun cuando el recibo no distingue master/house).
UPDATE entregas_locales_detalle
  SET awb = numero_guia
  WHERE awb IS NULL AND numero_guia IS NOT NULL;

ALTER TABLE entregas_locales_detalle
  DROP COLUMN IF EXISTS numero_guia;

CREATE INDEX IF NOT EXISTS entregas_locales_detalle_awb_idx
  ON entregas_locales_detalle (awb);
CREATE INDEX IF NOT EXISTS entregas_locales_detalle_hawb_idx
  ON entregas_locales_detalle (hawb);
