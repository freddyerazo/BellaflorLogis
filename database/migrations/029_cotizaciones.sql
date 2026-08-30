-- ============================================================
--  029_cotizaciones.sql
--  Persistencia de las cotizaciones del wizard de exportacion.
--
--  Contexto: hasta ahora el boton "Guardar cotizacion" escribia en
--  localStorage bajo la clave "blis_cotizaciones" (frontend/pages/
--  cotizaciones.js) y esa clave no se leia en ninguna parte de la app.
--  El resultado era un guardado que no guardaba: el dato moria en el
--  navegador de esa persona, no se podia reabrir ni comparar, y no se
--  compartia con el resto del equipo.
--
--  Diseno: se guarda el estado COMPLETO del wizard en `estado` (JSONB)
--  para poder reabrir la cotizacion exactamente como quedo, y ademas se
--  desnormalizan las cabeceras y los totales en columnas propias. Esa
--  duplicacion es deliberada: el listado y las comparaciones se resuelven
--  sin abrir el JSON, y los totales quedan congelados al momento de
--  guardar — si manana cambia una tarifa aerea o el tipo de cambio, la
--  cotizacion historica sigue diciendo lo que dijo cuando se emitio.
--
--  Los montos se guardan en USD, que es la moneda base del calculo en
--  cotizaciones.js: `moneda` y `eur_to_usd` (dentro de `estado`) solo
--  definen como se PRESENTA. Guardar en USD evita que una cotizacion en
--  EUR quede sin forma de reconstruir el monto original.
-- ============================================================

CREATE TABLE IF NOT EXISTS cotizaciones (
    id                  BIGSERIAL   PRIMARY KEY,

    -- Identificacion
    nombre              TEXT        NOT NULL,   -- rotulo que digita el usuario
    creado_por          TEXT,                   -- texto libre: no hay auth todavia
    creado_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    active              BOOLEAN     NOT NULL DEFAULT true,  -- borrado logico

    -- Cabecera desnormalizada (para el listado, sin abrir el JSONB)
    ruta                TEXT,       -- "Ecuador -> Paises Bajos"
    aeropuerto_origen   TEXT,       -- IATA
    aeropuerto_destino  TEXT,       -- IATA
    incoterm            TEXT,
    moneda              TEXT        NOT NULL DEFAULT 'USD',  -- solo presentacion
    producto            TEXT,       -- "Rosa Freedom"

    -- Volumenes
    cajas               INTEGER,
    total_stems         INTEGER,
    total_kg_real       NUMERIC(12,2),
    total_chargeable    NUMERIC(12,2),

    -- Totales por seccion, congelados al guardar (USD)
    fob_usd             NUMERIC(12,4),  -- precio unitario por tallo
    s1_usd              NUMERIC(14,2),  -- producto (FOB x tallos)
    s2_usd              NUMERIC(14,2),  -- documentos de exportacion
    s3_usd              NUMERIC(14,2),  -- flete aereo
    s4_usd              NUMERIC(14,2),  -- fitosanitario
    s5_usd              NUMERIC(14,2),  -- logistica en destino
    total_usd           NUMERIC(14,2),
    cost_per_stem       NUMERIC(12,6),
    cost_per_box        NUMERIC(14,4),

    -- Estado completo del wizard, para reabrir la cotizacion tal cual
    estado              JSONB       NOT NULL
);

-- El listado siempre pide las activas mas recientes primero.
CREATE INDEX IF NOT EXISTS idx_cotizaciones_activas
    ON cotizaciones (creado_at DESC)
    WHERE active = true;
