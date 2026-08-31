-- ============================================================
--  030_agrocalidad_api.sql
--  Adecua el modulo Agrocalidad a los datos que entrega la API movil
--  de Agrocalidad, en reemplazo del scraping con Playwright.
--
--  Contexto: hasta ahora el unico origen era el scraping del sitio
--  guia.agrocalidad.gob.ec/.../consultaRequisitoComercio.php (protegido por
--  Imperva, de ahi el worker con Chromium en GitHub Actions). Se descubrio
--  que el backend de la app AGRO Movil expone los MISMOS datos como API REST
--  JSON, sin captcha ni bloqueo anti-bot, respondiendo la cadena completa en
--  ~2,4 s contra los 30-90 s del scraping.
--
--  Endpoints (base guia.agrocalidad.gob.ec/agrodb/aplicaciones/mvc/
--  AplicacionMovilExternos/):
--    obtenerProductosPorSubtipoProducto/21  -> 2056 flores cortadas
--    obtenerProductosPorSubtipoProducto/23  ->  228 follajes
--    obtenerDatosProductos/<id_producto>    -> ficha (cientifico, partida, area)
--    obtenerPaisProducto/<id_producto>/Exportacion        -> paises con requisitos
--    obtenerRequisitosPorPais/<id_producto>/Exportacion/<id_localizacion>
--  OJO: el movimiento va como la palabra "Exportacion" CON TILDE; sin tilde
--  el servicio responde 200 con lista vacia, sin error.
--
--  Cambio de fondo: la API devuelve los requisitos como objetos con
--  id_requisito estable, no como el texto plano "R1: ... | R2: ..." que
--  armaba el scraper. Medido sobre 27 consultas reales: 129 requisitos
--  devueltos pero solo 12 distintos (10,8x de repeticion) — el texto se
--  guarda una vez en un catalogo y las combinaciones solo lo referencian.
-- ============================================================


-- ------------------------------------------------------------
-- 1. Mapeo exacto especie -> producto de Agrocalidad
--
-- Hoy el match se hace por texto (species.name_agrocalidad) y se resuelve en
-- cada consulta con normalizacion de acentos y scoring de prefijos. Con la API
-- el id numerico es exacto y estable, asi que se guarda una sola vez.
-- name_agrocalidad se conserva: sigue siendo util para el match inicial y para
-- las especies todavia sin id.
-- ------------------------------------------------------------
ALTER TABLE species
    ADD COLUMN IF NOT EXISTS id_producto_agrocalidad INTEGER;

COMMENT ON COLUMN species.id_producto_agrocalidad IS
    'id_producto en el catalogo de Agrocalidad (subtipo 21 flores / 23 follajes). Exacto y estable; reemplaza el match por nombre.';


-- ------------------------------------------------------------
-- 2. Mapeo exacto pais -> localizacion de Agrocalidad
--
-- countries.name_es ya guarda el nombre tal como aparece en Agrocalidad. El id
-- numerico evita depender de que ese texto coincida caracter por caracter.
-- ------------------------------------------------------------
ALTER TABLE countries
    ADD COLUMN IF NOT EXISTS id_localizacion_agrocalidad INTEGER;

COMMENT ON COLUMN countries.id_localizacion_agrocalidad IS
    'id_localizacion en Agrocalidad, devuelto por obtenerPaisProducto.';


-- ------------------------------------------------------------
-- 3. Catalogo de requisitos
--
-- Un requisito es el mismo objeto para todas las combinaciones que lo exigen:
-- el id 93 ("Certificado Fitosanitario de Exportacion") aparecio en 26 de 27
-- consultas de prueba. Se guarda una sola vez.
--
-- visto_primera_vez / visto_ultima_vez permiten detectar altas y bajas: si
-- Agrocalidad deja de devolver un requisito, su fecha de ultima vista queda
-- congelada sin perder el historico de lo que se exigia antes.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agrocalidad_requisitos (
    id_requisito       INTEGER     PRIMARY KEY,   -- el id de Agrocalidad, no uno propio
    nombre             TEXT        NOT NULL,      -- titulo corto
    requisito          TEXT,                      -- texto completo, con saltos de linea
    detalle_impreso    TEXT,                      -- variante para el certificado fisico
    visto_primera_vez  TIMESTAMPTZ NOT NULL DEFAULT now(),
    visto_ultima_vez   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ------------------------------------------------------------
-- 4. Enlace consulta <-> requisitos
--
-- Una fila por requisito exigido en esa combinacion especie/pais/tipo/area.
-- `orden` preserva la secuencia en que Agrocalidad los devuelve, que es la
-- que ve el usuario en la app.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agrocalidad_requirement_items (
    requirement_id  UUID     NOT NULL REFERENCES agrocalidad_requirements(id) ON DELETE CASCADE,
    id_requisito    INTEGER  NOT NULL REFERENCES agrocalidad_requisitos(id_requisito),
    orden           SMALLINT NOT NULL,
    PRIMARY KEY (requirement_id, id_requisito)
);

CREATE INDEX IF NOT EXISTS idx_agro_items_requisito
    ON agrocalidad_requirement_items (id_requisito);


-- ------------------------------------------------------------
-- 5. Datos del producto que ahora entrega la ficha de la API
--
-- scientific_name, tariff_heading y agrocalidad_code ya existian (los sacaba
-- el scraper); se agregan los que solo da la API.
--
-- Sobre agrocalidad_code: el sitio web muestra "A0007" y la API devuelve
-- "0007". Verificado en 8 especies (Achillea, Alstroemeria, Aster, Clavel,
-- Gerbera, rosa, Ammi majus, Crisantemo): la regla es exacta,
-- agrocalidad_code = 'A' || codigo_producto. Tambien verificado que las 157
-- filas historicas con codigo usan el prefijo 'A' sin excepcion, todas de
-- area SV. Por eso NO se agrega una columna aparte: las filas de la API
-- graban en agrocalidad_code ya con la letra, igual que la web, y el formato
-- queda unificado entre ambos origenes. El valor crudo de la API se recupera
-- con substring(agrocalidad_code from 2).
--
-- ADVERTENCIA para cruces: codigo_producto NO identifica un producto. Medido
-- sobre 32 productos hay 26 codigos distintos, y el codigo 0001 lo comparten
-- Achillea, Alstroemeria, Aster, Clavel, Crisantemo y rosa — es decir, casi
-- todo el volumen de Bellaflor. La clave unica y estable es id_producto
-- (rosa=18597, Clavel=16700, Crisantemo=16709).
-- ------------------------------------------------------------
ALTER TABLE agrocalidad_requirements
    ADD COLUMN IF NOT EXISTS id_producto          INTEGER,
    ADD COLUMN IF NOT EXISTS tipo                 TEXT,
    ADD COLUMN IF NOT EXISTS id_subtipo_producto  INTEGER,
    ADD COLUMN IF NOT EXISTS subtipo              TEXT,
    ADD COLUMN IF NOT EXISTS unidad_medida        TEXT,
    ADD COLUMN IF NOT EXISTS id_localizacion      INTEGER,
    ADD COLUMN IF NOT EXISTS fuente               TEXT NOT NULL DEFAULT 'api';

COMMENT ON COLUMN agrocalidad_requirements.agrocalidad_code IS
    'Codigo de Agrocalidad en formato de la web: A + codigo_producto de la API (ej. API "0007" -> "A0007"). NO es identificador unico de producto: el 0001 lo comparten rosa, clavel, crisantemo y otros. Para cruzar usar id_producto.';

COMMENT ON COLUMN agrocalidad_requirements.id_producto IS
    'id_producto de Agrocalidad. Clave UNICA y estable del producto; es la que debe usarse para cruces.';

COMMENT ON COLUMN agrocalidad_requirements.fuente IS
    'api = API movil de Agrocalidad; scraping = worker con Playwright (origen historico).';

-- Las 196 filas que ya existian vienen del scraping, no de la API.
UPDATE agrocalidad_requirements
SET fuente = 'scraping'
WHERE fuente = 'api'
  AND queried_at < '2026-08-30';

-- `requirements` (texto plano "R1: ... | R2: ...") se CONSERVA: es el unico
-- formato que tienen las 196 filas historicas y lo que hoy lee el frontend.
-- Para las filas nuevas se llena por compatibilidad, pero la fuente de verdad
-- pasa a ser agrocalidad_requirement_items.
COMMENT ON COLUMN agrocalidad_requirements.requirements IS
    'Texto plano aplanado (R1: ... | R2: ...). Historico del scraping y compatibilidad del frontend; la fuente estructurada es agrocalidad_requirement_items.';


-- ------------------------------------------------------------
-- 6. Vista de lectura: una consulta con sus requisitos ya armados
--
-- Evita que cada lector tenga que rehacer el join de tres tablas.
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW v_agrocalidad_requisitos AS
SELECT
    r.id                AS requirement_id,
    r.species_id,
    s.name              AS especie,
    r.country_id,
    c.name_es           AS pais,
    r.trade_type,
    r.area_code,
    r.status,
    r.scientific_name,
    r.tariff_heading,
    r.id_producto,
    r.agrocalidad_code,
    r.fuente,
    r.queried_at,
    COALESCE(
        (SELECT jsonb_agg(
                    jsonb_build_object(
                        'id_requisito',    q.id_requisito,
                        'nombre',          q.nombre,
                        'requisito',       q.requisito,
                        'detalle_impreso', q.detalle_impreso
                    ) ORDER BY i.orden)
         FROM agrocalidad_requirement_items i
         JOIN agrocalidad_requisitos q ON q.id_requisito = i.id_requisito
         WHERE i.requirement_id = r.id),
        '[]'::jsonb
    ) AS requisitos
FROM agrocalidad_requirements r
JOIN species   s ON s.id = r.species_id
JOIN countries c ON c.id = r.country_id
WHERE r.active = true;
