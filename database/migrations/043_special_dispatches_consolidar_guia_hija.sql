-- ============================================================
--  043_special_dispatches_consolidar_guia_hija.sql
--  Auditoria de Etiquetas: un despacho pasa de ser por
--  (fecha, id_pedido, tipo_caja, postcosecha, guia_hija) a ser por
--  (fecha, postcosecha, customer_id, guia_hija) -- pedido del usuario: un
--  mismo cliente+HAWB podia traer hasta 20 id_pedido distintos, cada uno
--  su propia ronda de preguntas en el bot para auditar fisicamente UN
--  SOLO paquete. Ahora es una sola auditoria por HAWB, con el desglose de
--  cajas por tipo (HB/QB/SB/...) en el resumen, porque dentro de un mismo
--  HAWB el tipo de caja SI varia (verificado contra datos reales: 15
--  grupos cliente+HAWB con mas de un tipo de caja en los ultimos 10 dias).
--
--  OJO -- `destinatario` (el de dartis_ventas, no el de customers) NO
--  entra en la clave: se probo primero incluyendolo "por seguridad" y
--  fallo contra datos reales -- clientes que son distribuidores (ej. LA
--  HACIENDA FLOWERS INC) reparten UN mismo HAWB entre once floristerias
--  finales distintas, cada linea con su propio dv.destinatario, y eso
--  seguia partiendo el despacho en once. `customer_id` (matched_customer_id
--  en el motor) ya resuelve la identidad del cliente especial via
--  customers.destinatario en el JOIN -- dv.destinatario es un dato de
--  visualizacion de la linea de venta, no parte de la identidad del
--  despacho. Se sigue guardando (unificado si coincide entre todas las
--  lineas, o "<n> destinatarios distintos" si no) pero fuera de la clave.
--
--  id_pedido y tipo_caja (columnas antiguas, singulares) se dejan intactas
--  en las filas ya AUDITADAS -- las nuevas filas consolidadas usan las
--  columnas nuevas en su lugar y dejan las antiguas en NULL.
--
--  El indice unico nuevo es PARCIAL (solo filas PENDIENTE): verificado
--  contra datos reales, existen HAWB con una parte ya AUDITADA bajo un
--  tipo de caja viejo y otra parte todavia PENDIENTE bajo otro -- un
--  indice unico normal (sin el WHERE) choca contra esas filas AUDITADAS
--  historicas, que no se deben tocar ni fusionar (perderian su rastro de
--  auditoria: fotos, confirmacion, observaciones). Con el indice parcial,
--  el historial AUDITADO queda intacto tal cual estaba, y la unicidad
--  solo se exige hacia adelante, entre despachos PENDIENTE.
--
--  Los despachos PENDIENTE existentes se borran aqui mismo: son 100%
--  recalculables desde dartis_ventas, y `generar_despachos_del_dia()` los
--  vuelve a crear ya consolidados la proxima vez que corra para cada
--  fecha (ver CONTINUAR.md para el detalle de la regeneracion).
-- ============================================================

ALTER TABLE special_dispatches
    ADD COLUMN id_pedidos JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN desglose_tipo_caja JSONB NOT NULL DEFAULT '{}'::jsonb;

DELETE FROM special_dispatches WHERE estado = 'PENDIENTE';

DROP INDEX IF EXISTS special_dispatches_fecha_id_pedido_tipo_caja_pos_guia_idx;

CREATE UNIQUE INDEX special_dispatches_fecha_pos_cliente_guia_pendiente_idx
    ON special_dispatches (fecha, postcosecha, customer_id, COALESCE(guia_hija, ''))
    WHERE estado = 'PENDIENTE';
