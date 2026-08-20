-- ============================================================
--  018_customers_cliente_especial.sql
--  Reemplaza la tabla "clientes_especiales" del proyecto externo
--  Auditoria_LEsp (Supabase separada sfxesqkwizncyfdbsqta) por un
--  simple flag en customers. Verificado contra los datos reales: las
--  columnas etiqueta/instrucciones de esa tabla son 100% redundantes
--  (etiqueta == cliente y instrucciones vacio en las 53 filas), asi
--  que un booleano captura toda la informacion real sin perder nada.
-- ============================================================

ALTER TABLE customers ADD COLUMN es_cliente_especial BOOLEAN DEFAULT false;
