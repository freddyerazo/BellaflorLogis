-- ============================================================
--  017_courier_reconciliation.sql
--  Torre de Control: concilia cajas de dartis_ventas vs manifiestos
--  de UPS/FedEx y entregas de agencias locales.
--  No hace falta un Excel Dartis propio: dartis_ventas ya provee esa
--  informacion (agrupado por id_pedido), ver plan de la Fase 3.
-- ============================================================

CREATE TABLE courier_ups_manifest (
    id                  BIGSERIAL PRIMARY KEY,
    factura             INTEGER NOT NULL,       -- PO extraido de Reference Number(s) = dartis_ventas.id_pedido
    tracking            TEXT NOT NULL,
    referencia          TEXT,                   -- Reference Number(s) crudo (trae tambien el PO de Duoplane)
    estado              TEXT,
    fecha_manifiesto    TEXT,
    ship_to             TEXT,
    destino             TEXT,
    servicio            TEXT,
    entrega_programada  TEXT,
    uploaded_at         TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_courier_ups_manifest_factura ON courier_ups_manifest (factura);

CREATE TABLE courier_fedex_envios (
    id                    BIGSERIAL PRIMARY KEY,
    tracking              TEXT UNIQUE NOT NULL,
    factura               INTEGER,              -- po
    referencia            TEXT,
    destinatario          TEXT,
    ciudad                TEXT,
    awb                   TEXT,
    fecha_envio           TEXT,
    fecha_registro        TIMESTAMPTZ DEFAULT now(),
    estado_fedex          TEXT,
    fecha_entrega_fedex   TEXT
);
CREATE INDEX idx_courier_fedex_envios_factura ON courier_fedex_envios (factura);

CREATE TABLE courier_agency_mapping (
    id                      BIGSERIAL PRIMARY KEY,
    variante_en_sheet       TEXT NOT NULL,
    mapeo_propuesto_dartis  TEXT NOT NULL,
    confianza               TEXT,
    UNIQUE (variante_en_sheet)
);

CREATE TABLE courier_reconciliation (
    id                  BIGSERIAL PRIMARY KEY,
    factura             INTEGER UNIQUE NOT NULL,   -- = dartis_ventas.id_pedido
    courier             TEXT,
    courier_raw         TEXT,
    empresa             TEXT,
    cliente             TEXT,
    destinatario        TEXT,
    vendedor_cliente     TEXT,
    cajas_dartis        NUMERIC,
    fecha_dartis        DATE,
    tracking            TEXT,
    trackings           JSONB,
    detalle_bultos      JSONB,
    trackings_extra     INTEGER,
    bultos_csv          INTEGER,
    estado_csv          TEXT,
    fecha_manifiesto    TEXT,
    servicio            TEXT,
    entrega_programada  TEXT,
    cajas_manifiesto    INTEGER,
    estado_vivo         TEXT,
    entrega_estimada    TEXT,
    ubicacion           TEXT,
    conciliacion        TEXT,
    diferencia          NUMERIC,
    fecha_entrega_real  TEXT,
    foto_url            TEXT,
    cliente_confirmado_ocr BOOLEAN DEFAULT false,
    refreshed_at        TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_courier_reconciliation_conciliacion ON courier_reconciliation (conciliacion);
CREATE INDEX idx_courier_reconciliation_courier ON courier_reconciliation (courier);

CREATE TABLE courier_bot_log (
    id               BIGSERIAL PRIMARY KEY,
    id_pedido        INTEGER,
    tracking_asignado TEXT,
    status           TEXT,
    detalle          TEXT,
    corrido_en       TIMESTAMPTZ DEFAULT now()
);

-- Semilla de courier_agency_mapping: solo filas de confianza "alta*" del
-- CSV curado a mano del proyecto original (mapeo_agencias_entregas_dartis.csv).
-- Las de confianza media/"SIN MAPEO" se excluyen a proposito (ver plan Fase 3).
INSERT INTO courier_agency_mapping (variante_en_sheet, mapeo_propuesto_dartis, confianza) VALUES
('VALUE CARGO', 'VALUE CARGO', 'alta (normalizado exacto)'),
('Fresh Logistics Carga', 'FRESH LOGISTIC', 'alta (confirmado por usuario)'),
('Logiztik Alliance', 'ALIANZA LOGISTIKA', 'alta (regla manual)'),
('FLOWERCARGO S.A.', 'FLOWERCARGO', 'alta (normalizado exacto)'),
('Pacific Air Cargo', 'PACIFIC CARGO', 'alta (regla manual)'),
('GREEN LOGISTICS GREENLOG S.A.S.', 'GREEN LOGISTICS GREENLOG S.A.S.', 'alta (normalizado exacto)'),
('DSV', 'DSV-AIR&SEA S.A.', 'alta (regla manual)'),
('KUEHNE + NAGEL S.A.S.', 'KUEHNE-NAGEL', 'alta (normalizado exacto)'),
('LogiztikAlliance', 'ALIANZA LOGISTIKA', 'alta (regla manual)'),
('KUEHNE+NAGEL S.A.S.', 'KUEHNE-NAGEL', 'alta (normalizado exacto)'),
('SAFTEC S.A.', 'SAFTEC', 'alta (normalizado exacto)'),
('DIRECT CARGO', 'DIRECT CARGO - QUITO', 'alta (regla manual)'),
('FRESH LOGISTICS CARGA', 'FRESH LOGISTIC', 'alta (confirmado por usuario)'),
('Value Cargo', 'VALUE CARGO', 'alta (normalizado exacto)'),
('LOGIKECARGO', 'LOGIKE CARGO', 'alta (normalizado sin espacios)'),
('REAL CARGA', 'REAL CARGO', 'alta (regla manual)'),
('LDSEXPORT', 'LDS EXPORT', 'alta (normalizado sin espacios)'),
('KUEHNE+NAGEL', 'KUEHNE-NAGEL', 'alta (normalizado exacto)'),
('WORLDWIDE CARGO LOGISTICS CIA LTDA', 'WORLD WIDE', 'alta (regla manual)'),
('ONE TEAMCARGO', 'ONETEAMCARGO S.A.', 'alta (normalizado sin espacios)'),
('FREIGHTWISE FORWARDING S.A', 'FREIGHTWISE FORWARDING', 'alta (normalizado exacto)'),
('ONE TEAMCARGO S.A.', 'ONETEAMCARGO S.A.', 'alta (normalizado sin espacios)'),
('Kuehne Nagel', 'KUEHNE-NAGEL', 'alta (normalizado exacto)'),
('Kuehne+Nagel S.A.S.', 'KUEHNE-NAGEL', 'alta (normalizado exacto)'),
('Kuehne + Nagel S.A.S.', 'KUEHNE-NAGEL', 'alta (normalizado exacto)'),
('APOLLO', 'APOLLO FREIGHT ECUADOR', 'alta (confirmado por usuario)'),
('Direct Cargo', 'DIRECT CARGO - QUITO', 'alta (regla manual)'),
('PANATWORLD SA', 'PANATLANTIC', 'alta (confirmado por usuario)'),
('ONE TEAMCARGO SA', 'ONETEAMCARGO S.A.', 'alta (normalizado sin espacios)'),
('FLOWERCARGO SA', 'FLOWERCARGO', 'alta (normalizado exacto)'),
('Kuehne + Nagel', 'KUEHNE-NAGEL', 'alta (normalizado exacto)'),
('PANATWORLD S.A.', 'PANATLANTIC', 'alta (confirmado por usuario)'),
('Kuehne+Nagel', 'KUEHNE-NAGEL', 'alta (normalizado exacto)'),
('FRESH LOGISTIC', 'FRESH LOGISTIC', 'alta (normalizado exacto)'),
('PACIFIC AIR CARGO', 'PACIFIC CARGO', 'alta (regla manual)'),
('ECUADOR CARGO', 'ECUADOR CARGO', 'alta (normalizado exacto)'),
('Real Carga', 'REAL CARGO', 'alta (regla manual)'),
('FLOWERCARGO S.A', 'FLOWERCARGO', 'alta (normalizado exacto)'),
('D&C CARGO', 'D&C CARGO', 'alta (normalizado exacto)'),
('KUEHNE NAGEL', 'KUEHNE-NAGEL', 'alta (normalizado exacto)'),
('ONE TEAMCARGO S.A', 'ONETEAMCARGO S.A.', 'alta (normalizado sin espacios)'),
('OPERFLOR', 'OPERFLOR CIA. LTDA.', 'alta (normalizado exacto)'),
('KUEHNE NAGEL S.A.S.', 'KUEHNE-NAGEL', 'alta (normalizado exacto)'),
('SAFTEC', 'SAFTEC', 'alta (normalizado exacto)'),
('PANATLANTIC', 'PANATLANTIC', 'alta (normalizado exacto)'),
('CHAMPION CARGO ECUADOR', 'CHAMPION CARGO ECUADOR', 'alta (normalizado exacto)'),
('APOLLO FREIGHT ECUADOR', 'APOLLO FREIGHT ECUADOR', 'alta (normalizado exacto)'),
('ONE Teamcargo', 'ONETEAMCARGO S.A.', 'alta (normalizado sin espacios)'),
('Fresh Flower Cargo', 'FRESH FLOWER CARGO', 'alta (normalizado exacto)'),
('Ecuador Cargo', 'ECUADOR CARGO', 'alta (normalizado exacto)'),
('GREEN LOGISTICS', 'GREEN LOGISTICS GREENLOG S.A.S.', 'alta (confirmado por usuario)'),
('FRESH FLOWER CARGO', 'FRESH FLOWER CARGO', 'alta (normalizado exacto)'),
('LOGIKE CARGO', 'LOGIKE CARGO', 'alta (normalizado exacto)'),
('EBF CARGO', 'EBF CARGO', 'alta (normalizado exacto)'),
('PANATWORLDSA', 'PANATLANTIC', 'alta (confirmado por usuario)'),
('KUEHNE-NAGEL', 'KUEHNE-NAGEL', 'alta (normalizado exacto)'),
('LogikeCargo', 'LOGIKE CARGO', 'alta (normalizado sin espacios)'),
('FLOWERCARGO', 'FLOWERCARGO', 'alta (normalizado exacto)'),
('Logistik Alliance', 'ALIANZA LOGISTIKA', 'alta (regla manual)'),
('Fresh Logistics', 'FRESH LOGISTIC', 'alta (confirmado por usuario)'),
('FRESH FLOWER CARGO CIA. LTDA.', 'FRESH FLOWER CARGO', 'alta (normalizado exacto)'),
('REAL CARGO', 'REAL CARGO', 'alta (normalizado exacto)'),
('OPERFLOR CIA. LTDA.', 'OPERFLOR CIA. LTDA.', 'alta (normalizado exacto)'),
('DSV-AIR&SEA S.A.', 'DSV-AIR&SEA S.A.', 'alta (normalizado exacto)'),
('LogiztikAlliance Group', 'ALIANZA LOGISTIKA', 'alta (regla manual)'),
('KUEHNE + NAGEL', 'KUEHNE-NAGEL', 'alta (normalizado exacto)'),
('Flowercargo SA', 'FLOWERCARGO', 'alta (normalizado exacto)'),
('EBF CARGO CIA. LTDA.', 'EBF CARGO', 'alta (normalizado exacto)'),
('GREEN LOGISTICS GREENLOG S.A.S', 'GREEN LOGISTICS GREENLOG S.A.S.', 'alta (normalizado exacto)'),
('FRESH LOGISTICS', 'FRESH LOGISTIC', 'alta (confirmado por usuario)'),
('EBFCARGO CIA. LTDA.', 'EBF CARGO', 'alta (normalizado sin espacios)'),
('KUEHNE + NAGEL, S.A.S.', 'KUEHNE-NAGEL', 'alta (normalizado exacto)'),
('KUEHNE + NAGEL S.A.', 'KUEHNE-NAGEL', 'alta (normalizado exacto)'),
('Kuehne+Nagel S.A.', 'KUEHNE-NAGEL', 'alta (normalizado exacto)'),
('KUEHNE+NAGEL S.A.', 'KUEHNE-NAGEL', 'alta (normalizado exacto)'),
('LOGIZTIK CARGO', 'ALIANZA LOGISTIKA', 'alta (regla manual)'),
('ECUADOR CARGo', 'ECUADOR CARGO', 'alta (normalizado exacto)'),
('GREEN LOGISTICS GREENLOG SAS', 'GREEN LOGISTICS GREENLOG S.A.S.', 'alta (normalizado exacto)'),
('GREEN LOGISTICS GREENLOGS.A.S.', 'GREEN LOGISTICS GREENLOG S.A.S.', 'alta (confirmado por usuario)'),
('DIMENTION FLOWER', 'DIMENTION FLOWERS', 'alta (regla manual)'),
('KUEHNE + NAGEL S.A.S', 'KUEHNE-NAGEL', 'alta (normalizado exacto)'),
('COMERCIALIZADORA DIMENTION', 'DIMENTION FLOWERS', 'alta (regla manual)'),
('UPS', 'UPS', 'alta (normalizado exacto)'),
('ONETEAMCARGO S.A.', 'ONETEAMCARGO S.A.', 'alta (normalizado exacto)'),
('ECUCARGA', 'ECUCARGA', 'alta (normalizado exacto)'),
('LDS EXPORT', 'LDS EXPORT', 'alta (normalizado exacto)'),
('Flowercargo S.A.', 'FLOWERCARGO', 'alta (normalizado exacto)'),
('HPLAPOLLO', 'APOLLO FREIGHT ECUADOR', 'alta (confirmado por usuario, extraido de OCR)'),
('HPLAFOLLO', 'APOLLO FREIGHT ECUADOR', 'alta (confirmado por usuario, extraido de OCR - typo OCR)'),
('UPLAPOLLO', 'APOLLO FREIGHT ECUADOR', 'alta (confirmado por usuario, extraido de OCR - typo OCR)')
ON CONFLICT (variante_en_sheet) DO NOTHING;
