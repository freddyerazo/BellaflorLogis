-- ============================================================
--  037_courier_manifiestos_unicidad.sql
--  Aplicada el 2026-09-05 vía MCP; este archivo la deja registrada
--  en el repositorio (faltaba — se aplico antes de escribir el .sql).
--
--  El manifiesto de UPS es acumulativo: el mismo archivo se vuelve a subir
--  con filas ya cargadas. Sin unicidad por tracking, cada carga duplicaba
--  los bultos de una factura e inventaba DISCREPANCIA. courier_fedex_envios
--  ya tenia UNIQUE(tracking) desde su creacion.
-- ============================================================

ALTER TABLE courier_ups_manifest
  ADD CONSTRAINT courier_ups_manifest_tracking_key UNIQUE (tracking);

-- Los cruces se hacen siempre por factura (= IdFactura de DARTIS, el token
-- "PO:<numero>" del manifiesto de UPS).
CREATE INDEX IF NOT EXISTS courier_ups_manifest_factura_idx
  ON courier_ups_manifest (factura);
CREATE INDEX IF NOT EXISTS courier_fedex_envios_factura_idx
  ON courier_fedex_envios (factura);

-- Trazabilidad de la carga: de que archivo vino cada fila y cuando se actualizo.
ALTER TABLE courier_ups_manifest
  ADD COLUMN IF NOT EXISTS archivo text,
  ADD COLUMN IF NOT EXISTS actualizado_at timestamptz DEFAULT now();
ALTER TABLE courier_fedex_envios
  ADD COLUMN IF NOT EXISTS archivo text,
  ADD COLUMN IF NOT EXISTS actualizado_at timestamptz DEFAULT now();
