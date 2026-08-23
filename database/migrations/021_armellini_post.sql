-- ============================================================
--  021_armellini_post.sql
--  Modulo Armellini Post: genera el XML AelisShipperEDI que Armellini
--  (carrier de Miami) espera para las entregas de Bellaflor.
--
--  Contexto: en el WMS de LAG el carrier figura como "ARMELLINI NO EDI",
--  es decir LAG no transmite EDI a Armellini. Por eso el XML se arma aparte.
--  Reemplaza los scripts sueltos del proyecto externo "ArmelliniFormat".
--
--  Fuente de datos: el XML de operaciones que emite Expoflor
--  (ReservasExportadores / XMLOperaciones*_EXPOFL.xml). Se eligio sobre el
--  reporte ResumenCodigosDeBarra y sobre las APIs de LAG porque es el unico
--  origen que trae, a nivel de caja fisica: barcode, dimensiones, codigo de
--  producto, PO, factura y la fecha/carrier de salida desde Miami.
--
--  dartis_ventas NO puede reemplazarlo: esta agregada por
--  (pedido, guia, especie, tipo_caja). Ejemplo real: la guia hija
--  A76027925 son 232 cajas en el XML y 2 filas en dartis_ventas.
-- ============================================================


-- ------------------------------------------------------------
-- Cajas del XML de operaciones de Expoflor. Una fila por caja fisica.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS expoflor_operaciones_cajas (
    id                    BIGSERIAL   PRIMARY KEY,

    -- Trazabilidad del archivo de origen
    archivo               TEXT        NOT NULL,
    importado_at          TIMESTAMPTZ DEFAULT now(),

    -- Nivel masterAwb
    awb                   TEXT        NOT NULL,   -- 11 digitos sin separadores (= dartis_ventas.guia_madre)
    fecha_despacho        DATE,
    origen                TEXT,
    destino               TEXT,

    -- Nivel House
    hawb                  TEXT        NOT NULL,   -- = dartis_ventas.guia_hija
    codigo_cultivo        TEXT,
    nombre_cultivo        TEXT,                   -- "EXPOFLOR CIA. LTDA." (nombre corto)

    -- Nivel box
    numero_dae            TEXT,                   -- = dartis_ventas.dae
    codigo_cliente        TEXT,
    nombre_cliente        TEXT,                   -- = dartis_ventas.destinatario (NO .cliente)
    codigo_pieza          TEXT        NOT NULL UNIQUE,  -- barcode: identidad de la caja
    codigo_producto       TEXT,                   -- ya viene en codigo Armellini (LYS = LYSIMACHIA)
    descripcion_producto  TEXT,
    descripcion_variedad  TEXT,
    empaque               TEXT,                   -- QB / EB / HB
    factura               INTEGER,                -- = dartis_ventas.id_pedido
    unidades              INTEGER,                -- tallos
    piezas                NUMERIC(10,4),
    kilos                 NUMERIC(10,3),
    po                    TEXT,                   -- cobertura parcial: vacio en varias cuentas mayoristas

    -- Dimensiones. El XML las trae en cm; Armellini las pide en pulgadas.
    -- La regla round(cm/2.54) se verifico contra las columnas Largo/Ancho/Alto
    -- Inch del reporte ResumenCodigosDeBarra: coincide en el 100% de los casos.
    largo_cm              NUMERIC(10,2),
    ancho_cm              NUMERIC(10,2),
    alto_cm               NUMERIC(10,2),
    largo_inch            INTEGER GENERATED ALWAYS AS (round(largo_cm / 2.54)) STORED,
    ancho_inch            INTEGER GENERATED ALWAYS AS (round(ancho_cm / 2.54)) STORED,
    alto_inch             INTEGER GENERATED ALWAYS AS (round(alto_cm  / 2.54)) STORED,

    -- Salida desde la bodega de Miami
    carrier_miami         TEXT,                   -- = truck_company.id_logistic_carrier (HEB/ARM/ART/AAX = Armellini; HEB es "ARMELLINI NO EDI")
    fecha_carrier         DATE,                   -- alimenta <Shipdate>; el centinela 1900-01-01 se guarda como NULL

    -- Valores del XML. NO son confiables: la suma de valortotal del archivo
    -- del 2026-08-18 da $3.470.872,46 contra $40.635,37 en dartis_ventas
    -- (85x), y 747 de 751 cajas no cuadran contra tallos x precio.
    -- Se conservan solo para auditoria. Usar dartis_ventas.total_dolares.
    precio_xml            NUMERIC(12,4),
    valortotal_xml        NUMERIC(14,4)
);

CREATE INDEX IF NOT EXISTS idx_exp_ops_awb     ON expoflor_operaciones_cajas (awb);
CREATE INDEX IF NOT EXISTS idx_exp_ops_hawb    ON expoflor_operaciones_cajas (hawb);
CREATE INDEX IF NOT EXISTS idx_exp_ops_factura ON expoflor_operaciones_cajas (factura);
CREATE INDEX IF NOT EXISTS idx_exp_ops_carrier ON expoflor_operaciones_cajas (carrier_miami, fecha_carrier);


-- ------------------------------------------------------------
-- Nombre legal de la finca, tal como lo espera Armellini en <FarmName>.
-- Ni el XML ni dartis_ventas lo traen: ambos dicen "EXPOFLOR CIA. LTDA.",
-- pero Armellini recibe "EXPORTADORA DE FLORES EXPOFLOR CIA. LTDA.".
-- ------------------------------------------------------------
ALTER TABLE farms ADD COLUMN IF NOT EXISTS legal_name TEXT;

UPDATE farms SET legal_name = 'EXPORTADORA DE FLORES EXPOFLOR CIA. LTDA.'
WHERE code = 'EXPOFLOR' AND legal_name IS NULL;


-- ------------------------------------------------------------
-- Consignee de Armellini por destinatario. Es el unico campo del XML
-- que no existe en ninguna fuente: se siembra a mano.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS armellini_consignees (
    id              BIGSERIAL   PRIMARY KEY,
    destinatario    TEXT        NOT NULL UNIQUE,  -- = expoflor_operaciones_cajas.nombre_cliente
    consignee_code  TEXT        NOT NULL,
    descripcion     TEXT,
    active          BOOLEAN     DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

INSERT INTO armellini_consignees (destinatario, consignee_code, descripcion) VALUES
('Heinen''s', 'FA00140', 'Destino de los XML generados a mano hasta 2026-08')
ON CONFLICT (destinatario) DO NOTHING;


-- ------------------------------------------------------------
-- Override de codigo de producto. Normalmente vacia: el XML de operaciones
-- ya trae el codigo que usa Armellini (se confirmo LYS = LYSIMACHIA contra
-- los XML enviados). Existe por si algun producto no coincide.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS armellini_product_overrides (
    id                BIGSERIAL   PRIMARY KEY,
    codigo_producto   TEXT        NOT NULL UNIQUE,  -- el que trae el XML
    armellini_code    TEXT        NOT NULL,         -- el que debe salir
    motivo            TEXT,
    created_at        TIMESTAMPTZ DEFAULT now()
);


-- ------------------------------------------------------------
-- Historial de XML generados: permite reimprimir un envio y detectar
-- cajas mandadas dos veces. El flujo con scripts no dejaba rastro.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS armellini_exports (
    id            BIGSERIAL   PRIMARY KEY,
    filename      TEXT        NOT NULL,
    shipdate      TEXT        NOT NULL,           -- MM/DD/YY, tal como va en el XML
    shipper_code  TEXT        NOT NULL,
    total_cajas   INTEGER     NOT NULL,
    awbs          TEXT[]      DEFAULT '{}',
    pos           TEXT[]      DEFAULT '{}',
    barcodes      TEXT[]      DEFAULT '{}',
    avisos        TEXT[]      DEFAULT '{}',
    xml_content   TEXT        NOT NULL,
    created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_armellini_exports_created ON armellini_exports (created_at DESC);


-- ------------------------------------------------------------
-- HEB = "ARMELLINI NO EDI": la ruta de Armellini que no recibe transmision
-- EDI, y por eso la que obliga a generar este XML a mano. Es el codigo que
-- llevan las cajas de Heinen's (destinatario de los 5 XML historicos).
-- Faltaba en el catalogo de 139 carriers cargado en 020_truck_company.sql.
-- ------------------------------------------------------------
INSERT INTO truck_company (carrier_name, sub_carrier_name, country, id_logistic_carrier)
VALUES ('ARMELLINI', 'ARMELLINI NO EDI', 'UNITED STATES OF AMERICA', 'HEB')
ON CONFLICT (id_logistic_carrier) DO NOTHING;
