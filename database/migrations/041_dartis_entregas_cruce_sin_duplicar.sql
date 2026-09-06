-- ============================================================
--  041_dartis_entregas_cruce_sin_duplicar.sql
--  dartis_entregas_cruce guardaba fecha_dartis/empresa/agencia_carga como
--  copia de dartis_ventas. Se quitan: viven en un solo lugar (dartis_ventas)
--  y se consultan siempre con JOIN por id_pedido, para que nunca queden
--  desactualizadas si dartis_ventas cambia despues del cruce.
--
--  A diferencia de courier_reconciliation (Torre de Control), que SI
--  denormaliza estos mismos campos a proposito -- ese snapshot se reemplaza
--  entero en cada refresco (TRUNCATE + INSERT), asi que nunca queda viejo.
--  dartis_entregas_cruce en cambio se actualiza fila por fila segun se van
--  resolviendo los recibos, así que una copia fija si podria quedar
--  desactualizada frente al dato real.
-- ============================================================

ALTER TABLE dartis_entregas_cruce
  DROP COLUMN IF EXISTS fecha_dartis,
  DROP COLUMN IF EXISTS empresa,
  DROP COLUMN IF EXISTS agencia_carga;
