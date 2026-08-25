-- ============================================================
--  024_special_dispatches_id_pedido.sql
--  guia_madre/guia_hija llegan vacios en los datos recientes de Dartis
--  (0% poblados el 2026-08-27), y NULL != NULL en un UNIQUE constraint --
--  eso deja sin proteccion contra duplicados cuando se regeneran
--  despachos con guias vacias. id_pedido si viene siempre poblado en
--  dartis_ventas, asi que reemplaza a guia_madre/guia_hija como clave
--  de deduplicacion (mismo campo que ya usa Torre de Control).
-- ============================================================

ALTER TABLE special_dispatches ADD COLUMN id_pedido INTEGER;

ALTER TABLE special_dispatches
    DROP CONSTRAINT special_dispatches_fecha_guia_madre_guia_hija_tipo_caja_key;

ALTER TABLE special_dispatches
    ADD CONSTRAINT special_dispatches_fecha_id_pedido_tipo_caja_key
    UNIQUE (fecha, id_pedido, tipo_caja);

CREATE INDEX idx_special_dispatches_id_pedido ON special_dispatches (id_pedido);
