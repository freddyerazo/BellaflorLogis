-- ============================================================
--  042_courier_reconciliation_id_comercializadora.sql
--  Torre de Control (Fedex-Ups See): la columna "Factura" del tablero
--  mostraba dartis_ventas.id_pedido -- que sigue siendo la clave de cruce
--  contra el PO del manifiesto de UPS/FedEx y no se toca. El usuario pidio
--  mostrar ahi en su lugar el numero de factura comercial
--  (dartis_ventas.id_comercializadora), igual que ya hacia el proyecto
--  original REPORTEUPSFEDEX.
-- ============================================================

ALTER TABLE courier_reconciliation ADD COLUMN id_comercializadora INTEGER;
