-- ============================================================
--  023_armellini_dias_entrega.sql
--  Dias entre la salida del camion de Miami y la entrega en destino.
--
--  El correo de pre-alerta lleva dos fechas: "Miami Date" (la salida, que
--  ya tenemos en caja_fecha_transportador) y "DD <destino>" (la entrega).
--  La segunda no esta en ninguna fuente: se calcula sumando este desfase.
--  En los correos enviados a mano, Heinen's iba a 3 dias (Aug-16 -> Aug-19).
-- ============================================================

ALTER TABLE armellini_consignees
    ADD COLUMN IF NOT EXISTS dias_entrega INTEGER NOT NULL DEFAULT 3;

COMMENT ON COLUMN armellini_consignees.dias_entrega IS
    'Dias entre Miami Date y la fecha de entrega (DD) que se anuncia en el correo.';
