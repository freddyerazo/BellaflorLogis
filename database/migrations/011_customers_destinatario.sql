-- 011_customers_destinatario.sql
-- Agrega campo destinatario a customers.
-- En Dartis: cliente = importador/comprador, destinatario = quien recibe fisicamente la mercancia.

ALTER TABLE customers ADD COLUMN IF NOT EXISTS destinatario VARCHAR;
