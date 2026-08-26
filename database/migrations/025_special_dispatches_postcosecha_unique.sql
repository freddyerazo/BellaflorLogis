-- ============================================================
--  025_special_dispatches_postcosecha_unique.sql
--  Un mismo id_pedido puede tener lineas en mas de una poscosecha
--  (ej. distintas variedades del mismo pedido vienen de fincas
--  distintas). La clave unica (fecha, id_pedido, tipo_caja) de la
--  migracion 024 no distinguia esas lineas -- colisionaban entre si
--  y una pisaba (o directamente ocultaba) a la otra en la lista del
--  auditor. Se agrega postcosecha a la clave.
-- ============================================================

ALTER TABLE special_dispatches
    DROP CONSTRAINT special_dispatches_fecha_id_pedido_tipo_caja_key;

ALTER TABLE special_dispatches
    ADD CONSTRAINT special_dispatches_fecha_id_pedido_tipo_caja_postcosecha_key
    UNIQUE (fecha, id_pedido, tipo_caja, postcosecha);
