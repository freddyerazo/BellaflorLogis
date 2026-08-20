-- 014_customers_dartis_name.sql
-- Agrega dartis_name a customers: nombre exacto como aparece en Dartis ERP.
-- Permite cruzar dartis_ventas.cliente con customers sin depender del nombre largo de LAG.

ALTER TABLE customers ADD COLUMN IF NOT EXISTS dartis_name VARCHAR;

CREATE INDEX IF NOT EXISTS idx_customers_dartis_name ON customers (dartis_name);
