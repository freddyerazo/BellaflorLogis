-- ============================================================
--  039_entregas_locales_separar_campos.sql
--  Separa campos que el Sheet original (y el diseño inicial de la
--  migracion 038) traian mezclados en uno solo, perdiendo informacion real:
--
--  1. "N Guia / Ingreso" -> numero_ingreso (cabecera) + numero_guia (detalle)
--     Verificado sobre las 3.515 filas reales: 877 recibos traen los DOS
--     numeros a la vez y son cosas distintas -- INGRESO es el numero interno
--     de la bodega para todo el documento (un bodeguero, un chofer, una
--     placa, una temperatura para todo el camion); el AWB/HAWB es la guia
--     aerea de CADA finca dentro del mismo recibo. Ejemplo real (fila 2364,
--     EBF CARGO): un solo "INGRESO: ING-00150881" pero tres AWB distintos,
--     uno por cada "EXP:" (AMAZINGROSES 235-78409645, ASOMARILYNROSES
--     172-04024300, SARITA ROSES 145-11658183) -- por eso numero_guia va en
--     el detalle (una fila por finca), no en la cabecera.
--
--  2. "Total Fulls / PCS" -> total_fulls + total_piezas, ambos en el
--     detalle (uno por finca): "TOTAL: 1.75 / 7" son dos numeros distintos,
--     fulls (decimal) y piezas (entero), no un solo dato.
-- ============================================================

-- ---------- Cabecera: reemplaza numero_guia_ingreso por numero_ingreso ----------
ALTER TABLE entregas_locales
  ADD COLUMN IF NOT EXISTS numero_ingreso TEXT;

-- Si algo ya se cargo con el campo viejo (deberia estar vacio, la tabla es
-- nueva), se migra por las dudas antes de soltarlo.
UPDATE entregas_locales
  SET numero_ingreso = numero_guia_ingreso
  WHERE numero_ingreso IS NULL AND numero_guia_ingreso IS NOT NULL;

ALTER TABLE entregas_locales
  DROP COLUMN IF EXISTS numero_guia_ingreso;

-- ---------- Detalle: agrega numero_guia (AWB, por finca) y total_piezas ----------
ALTER TABLE entregas_locales_detalle
  ADD COLUMN IF NOT EXISTS numero_guia TEXT,
  ADD COLUMN IF NOT EXISTS total_piezas NUMERIC;

CREATE INDEX IF NOT EXISTS entregas_locales_numero_ingreso_idx
  ON entregas_locales (numero_ingreso);
CREATE INDEX IF NOT EXISTS entregas_locales_detalle_numero_guia_idx
  ON entregas_locales_detalle (numero_guia);
