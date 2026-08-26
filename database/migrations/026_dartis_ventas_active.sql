-- ============================================================
--  026_dartis_ventas_active.sql
--  Cada reimportacion de Dartis debe reconciliar contra lo que ya
--  estaba: actualizar lo que sigue, e inactivar lo que ya no aparece
--  en el archivo nuevo (pedido cancelado, cambio de fecha, etc. --
--  ver caso real: pedido 200546 quedo huerfano hasta que se borro
--  a mano). Antes no habia forma de distinguir "ya no existe" de
--  "sigue vigente pero no cambio".
-- ============================================================

ALTER TABLE dartis_ventas ADD COLUMN active BOOLEAN NOT NULL DEFAULT true;
CREATE INDEX idx_dartis_ventas_active ON dartis_ventas (active);
