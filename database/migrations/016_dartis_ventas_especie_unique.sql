-- ============================================================
--  016_dartis_ventas_especie_unique.sql
--  Corrige la clave única de dartis_ventas: una misma guia_madre +
--  guia_hija + tipo_caja transporta legitimamente varias especies
--  (una "receta"/caja puede combinar varias flores). La clave
--  anterior no incluia especie, por lo que al importar se perdian
--  en silencio todas las lineas de especie salvo la ultima del
--  archivo (~41% de las lineas del reporte Dartis).
-- ============================================================

ALTER TABLE dartis_ventas
    DROP CONSTRAINT dartis_ventas_id_pedido_guia_madre_guia_hija_tipo_caja_key;

ALTER TABLE dartis_ventas
    ADD CONSTRAINT dartis_ventas_id_pedido_guia_madre_guia_hija_tipo_caja_especie_key
    UNIQUE (id_pedido, guia_madre, guia_hija, tipo_caja, especie);
