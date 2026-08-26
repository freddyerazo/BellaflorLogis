-- ============================================================
--  027_special_dispatches_guia_hija_unique.sql
--  Un despacho ahora se separa tambien por guia_hija: un mismo
--  id_pedido+tipo_caja+postcosecha puede venir repartido en mas de
--  una guia hija (paquete fisico distinto), y cada una debe ser su
--  propio despacho para el auditor -- antes se sumaban en uno solo.
--  Las piezas si se siguen sumando dentro de una misma guia hija
--  (o dentro del grupo sin guia, si viene vacia).
--
--  Se usa un indice unico por expresion con COALESCE(guia_hija, '')
--  en vez de una UNIQUE constraint comun: en Postgres NULL nunca es
--  igual a NULL en un UNIQUE, y las guias siguen llegando vacias en
--  buena parte de los datos -- sin el COALESCE, cada regeneracion
--  duplicaria las filas sin guia en vez de actualizarlas.
-- ============================================================

ALTER TABLE special_dispatches
    DROP CONSTRAINT special_dispatches_fecha_id_pedido_tipo_caja_postcosecha_key;

CREATE UNIQUE INDEX special_dispatches_fecha_id_pedido_tipo_caja_pos_guia_idx
    ON special_dispatches (fecha, id_pedido, tipo_caja, postcosecha, COALESCE(guia_hija, ''));
