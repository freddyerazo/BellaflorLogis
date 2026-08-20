-- ============================================================
--  019_auditoria_etiquetas.sql
--  Auditoria de Etiquetas Especiales: reemplaza las hojas "Despachos"
--  y "Auditorias" de Google Sheets (proyecto externo Auditoria_LEsp) y
--  el CacheService de Apps Script usado para el estado de conversacion
--  del bot de Telegram.
-- ============================================================

CREATE TABLE special_dispatches (
    id              BIGSERIAL PRIMARY KEY,
    fecha           DATE NOT NULL,
    postcosecha     TEXT,
    customer_id     UUID REFERENCES customers(id),
    cliente         TEXT,
    destinatario    TEXT,
    guia_madre      TEXT,
    guia_hija       TEXT,
    cajas           NUMERIC,
    tipo_caja       TEXT,
    etiqueta        TEXT,
    instrucciones   TEXT,
    estado          TEXT DEFAULT 'PENDIENTE',
    auditado_por    TEXT,
    fecha_auditoria TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE (fecha, guia_madre, guia_hija, tipo_caja)
);
CREATE INDEX idx_special_dispatches_estado ON special_dispatches (estado);
CREATE INDEX idx_special_dispatches_fecha ON special_dispatches (fecha);

CREATE TABLE special_dispatch_audits (
    id                  BIGSERIAL PRIMARY KEY,
    dispatch_id         BIGINT REFERENCES special_dispatches(id),
    fecha_hora          TIMESTAMPTZ DEFAULT now(),
    auditor             TEXT,
    cajas_despachadas   NUMERIC,
    piezas_despachadas  NUMERIC,
    tipo_caja_ok        BOOLEAN,
    especie_ok          BOOLEAN,
    etiqueta_ok         BOOLEAN,
    observaciones       TEXT,
    foto_url            TEXT,
    chat_id             TEXT
);

CREATE TABLE telegram_conversation_state (
    chat_id     TEXT PRIMARY KEY,
    paso        TEXT,
    estado      JSONB,
    updated_at  TIMESTAMPTZ DEFAULT now()
);
