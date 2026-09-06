-- ============================================================
--  038_entregas_locales.sql
--  Modulo nuevo: interpreta los recibos OCR del bot de Telegram
--  "EntregasLocales" (Google Sheet, ver INGRESOS_LOCALES_URL) y los
--  cruza contra dartis_ventas, uno a uno por id_pedido.
--
--  Deliberadamente separado de `ingresos_locales.py` / `ingresos-locales.*`
--  (la pestaña existente, un proxy de solo lectura al Sheet) y del bot de
--  Telegram / Apps Script original (carpeta hermana IngresosLocales, repo
--  GitHub freddyerazo/EntregasLocales) — ninguno de los dos se toca.
--  Prefijo de tablas "entregas_locales_" a proposito, para no chocar con
--  el nombre "ingresos_locales" que ya usa la pestaña vieja.
--
--  Flujo: Sheet (via Google Sheets API, no via el Apps Script Web App)
--  -> entregas_locales_raw (espejo verbatim, nunca se reescribe)
--  -> entregas_locales + entregas_locales_detalle (reinterpretado con un
--     LLM propio a partir del texto OCR crudo, no del JSON que ya arma
--     DeepSeek en el bot original)
--  -> dartis_entregas_cruce (una fila por CADA id_pedido de dartis_ventas,
--     sin excepcion de courier: todo pasa primero por una bodega local
--     antes de salir por UPS, FedEx o una agencia terrestre).
-- ============================================================

-- ---------- 1. Espejo verbatim del Sheet ----------
-- `fila_sheet` es la llave natural (numero de fila real en el Google Sheet)
-- que permite sincronizar de forma idempotente: releer el Sheet y hacer
-- UPSERT por este numero nunca duplica una fila ya traida.
CREATE TABLE IF NOT EXISTS entregas_locales_raw (
    id                  BIGSERIAL   PRIMARY KEY,
    fila_sheet          INTEGER     UNIQUE NOT NULL,
    fecha_registro      TEXT,       -- tal como llega: dd/MM/yyyy (cuando la foto llego al bot)
    hora_registro       TEXT,
    fecha_documento     TEXT,       -- fecha impresa en el recibo fisico
    hora_documento      TEXT,
    empresa_logistica   TEXT,       -- texto crudo, sin normalizar (ver el desorden real: 191 variantes de ~36 agencias)
    nombre_chofer       TEXT,
    cedula              TEXT,
    placa               TEXT,
    finca_exportador    TEXT,       -- puede traer varias fincas separadas por " | " en un mismo recibo
    nombre_cliente      TEXT,       -- idem, uno o varios separados por " | "
    numero_guia_ingreso TEXT,
    detalle_cajas       TEXT,
    total_fulls_pcs     TEXT,
    temperatura         TEXT,
    observaciones       TEXT,
    ver_foto_url        TEXT,
    texto_ocr           TEXT,       -- columna Q del Sheet: el texto OCR crudo, antes de que el bot lo estructure.
                                     -- Es el insumo para la reinterpretacion propia (no se usa el JSON del bot original)
    sincronizado_at     TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS entregas_locales_raw_fecha_idx
  ON entregas_locales_raw (fecha_documento);

-- ---------- 2. Cabecera limpia, un registro por recibo ----------
CREATE TABLE IF NOT EXISTS entregas_locales (
    id                    BIGSERIAL   PRIMARY KEY,
    raw_id                BIGINT      NOT NULL UNIQUE REFERENCES entregas_locales_raw(id),
    fecha_documento       DATE,
    hora_documento        TEXT,       -- se deja texto: el recibo no siempre trae HH:mm limpio
    numero_guia_ingreso   TEXT,
    agencia_id            UUID        REFERENCES cargo_agencies(id),
    agencia_raw           TEXT        NOT NULL,  -- texto tal como vino, por si agencia_id queda sin resolver
    nombre_chofer         TEXT,
    cedula                TEXT,
    placa                 TEXT,
    temperatura_c         NUMERIC,
    observaciones         TEXT,
    foto_url              TEXT,
    calidad_ocr           TEXT        CHECK (calidad_ocr IN ('alta', 'media', 'baja')),
    modelo_interpretacion TEXT,       -- que LLM/version produjo esta lectura -- trazabilidad si se cambia de proveedor
    interpretado_at       TIMESTAMPTZ,
    created_at            TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS entregas_locales_fecha_idx
  ON entregas_locales (fecha_documento);
CREATE INDEX IF NOT EXISTS entregas_locales_agencia_idx
  ON entregas_locales (agencia_id);

-- ---------- 3. Detalle: un recibo puede traer varias fincas/clientes ----------
-- Reemplaza el string "FINCA A | FINCA B" del bot original por filas
-- separadas -- es la parte central del pedido de "informacion mas clara".
CREATE TABLE IF NOT EXISTS entregas_locales_detalle (
    id            BIGSERIAL   PRIMARY KEY,
    entrega_id    BIGINT      NOT NULL REFERENCES entregas_locales(id) ON DELETE CASCADE,
    finca_id      UUID        REFERENCES farms(id),
    finca_raw     TEXT        NOT NULL,
    cliente       TEXT,
    cajas_detalle TEXT,       -- texto tipo "FB:2 HB:1", se conserva para auditoria
    total_fulls   NUMERIC,
    created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS entregas_locales_detalle_entrega_idx
  ON entregas_locales_detalle (entrega_id);
CREATE INDEX IF NOT EXISTS entregas_locales_detalle_finca_idx
  ON entregas_locales_detalle (finca_id);

-- ---------- 4. Equivalencia bodega <-> courier ----------
-- Hallazgo real en los datos: la bodega que recibe para UPS se llama SAFTEC
-- en el recibo fisico ("UPS / SAFTEC", "SAFTEC S.A." aparecen como variantes
-- en ambas agencias desde la migracion 002). Dartis registra el pedido con
-- agencia_carga = 'UPS' (el courier final), no 'SAFTEC' (la bodega). Sin este
-- vinculo, ningun recibo de SAFTEC calzaria jamas contra un pedido de UPS.
--
-- Se modela aparte (no fusionando las agencias) porque cargo_agencies.name
-- debe seguir igual al texto exacto de Dartis (asi quedo definido en la
-- migracion 006) -- SAFTEC y UPS siguen siendo agencias distintas para ese
-- proposito, y solo se declaran equivalentes para el cruce de este modulo.
CREATE TABLE IF NOT EXISTS cargo_agencies_equivalencias (
    id            BIGSERIAL   PRIMARY KEY,
    agencia_id    UUID        NOT NULL REFERENCES cargo_agencies(id),
    equivale_a_id UUID        NOT NULL REFERENCES cargo_agencies(id),
    motivo        TEXT,
    UNIQUE (agencia_id, equivale_a_id)
);

INSERT INTO cargo_agencies_equivalencias (agencia_id, equivale_a_id, motivo)
SELECT sft.id, ups.id, 'SAFTEC opera la bodega receptora de UPS en Ecuador'
FROM cargo_agencies sft, cargo_agencies ups
WHERE sft.code = 'SFT' AND ups.code = 'UPS'
ON CONFLICT DO NOTHING;

-- ---------- 5. El cruce: una fila por CADA id_pedido de dartis_ventas ----------
-- Cobertura universal a proposito (confirmado con el usuario 2026-09-06):
-- todo pedido -- sea UPS, FedEx o agencia local -- pasa primero por una
-- bodega local antes de salir, asi que todos deben tener recibo. No existe
-- un estado "no aplica" por courier.
CREATE TABLE IF NOT EXISTS dartis_entregas_cruce (
    id                BIGSERIAL   PRIMARY KEY,
    id_pedido         INTEGER     NOT NULL UNIQUE,
    fecha_dartis      DATE,       -- denormalizado desde dartis_ventas, para filtrar sin join
    empresa           TEXT,       -- finca exportadora (dartis_ventas.empresa), denormalizado
    agencia_carga     TEXT,       -- dartis_ventas.agencia_carga, denormalizado
    entrega_id        BIGINT      REFERENCES entregas_locales(id),
    estado            TEXT        NOT NULL CHECK (estado IN ('OK', 'SIN RECIBO', 'AMBIGUO')),
    candidatos        JSONB,      -- ids de entregas_locales candidatas cuando estado = 'AMBIGUO'
    criterio          TEXT,       -- que combinacion de campos hizo match -- trazabilidad
    verificado_manual BOOLEAN     DEFAULT FALSE,
    actualizado_at    TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS dartis_entregas_cruce_estado_idx
  ON dartis_entregas_cruce (estado);
CREATE INDEX IF NOT EXISTS dartis_entregas_cruce_fecha_idx
  ON dartis_entregas_cruce (fecha_dartis);
