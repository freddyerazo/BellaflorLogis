-- 012_customers_code_lag.sql
-- Agrega codigo de cliente en el sistema de Alianza Logistika (LAG).
-- Fuente: archivo ID clientes.xlsx, hoja LAG_CUSTOMER_CODE.

ALTER TABLE customers ADD COLUMN IF NOT EXISTS customer_code_lag VARCHAR;

CREATE INDEX IF NOT EXISTS idx_customers_code_lag ON customers (customer_code_lag);
