-- ============================================================
--  031_countries_agrocalidad.sql
--  Completa en `countries` toda la informacion de destino que entrega
--  Agrocalidad, para las 255 filas y no solo para las consultadas.
--
--  Fuente canonica: RestWsOperadores/obtenerLozalizacion/0 del backend de la
--  app AGRO Movil. Devuelve 255 elementos con {id, nombre} — exactamente la
--  misma cantidad que tiene `countries`, y los ids coinciden con los que usa
--  obtenerPaisProducto / obtenerRequisitosPorPais (verificado con Estados
--  Unidos 1987, Chile 46, Paises Bajos 1920, Rusia 1945, España 68,
--  Alemania 57).
--
--  El cruce por `name_es` da 255 de 255 sin excepciones: esa columna ya venia
--  cargada con el nombre exacto de Agrocalidad desde el proyecto original.
--  Antes de esto solo 149 paises tenian id, porque el mapeo se habia armado
--  con la union de los destinos de 5 productos.
--
--  Agrocalidad no publica mas atributos de pais que id y nombre; por eso las
--  unicas columnas nuevas son el nombre de origen y la marca de bloque.
-- ============================================================


-- ------------------------------------------------------------
-- 1. Nombre exacto tal como lo publica Agrocalidad
--
-- Se guarda aparte de `name_es` a proposito: `name_es` es editable desde BLIS
-- y si alguien lo corrige (una tilde, un "Paises"/"Países") el cruce por
-- nombre deja de funcionar sin aviso. `nombre_agrocalidad` es la copia fiel
-- del origen y queda como respaldo para re-mapear si hiciera falta.
-- ------------------------------------------------------------
ALTER TABLE countries
    ADD COLUMN IF NOT EXISTS nombre_agrocalidad VARCHAR;

COMMENT ON COLUMN countries.nombre_agrocalidad IS
    'Nombre exacto del pais en el catalogo de Agrocalidad (RestWsOperadores/obtenerLozalizacion/0). Copia fiel del origen; no editar a mano.';

COMMENT ON COLUMN countries.id_localizacion_agrocalidad IS
    'id_localizacion de Agrocalidad. Es el valor que va en la ruta de obtenerRequisitosPorPais/<id_producto>/<movimiento>/<id_localizacion>.';


-- ------------------------------------------------------------
-- 2. Bloques comerciales
--
-- Agrocalidad publica algunos requisitos a nivel de bloque y no de pais:
-- "Unión Europea" (2062) y "Comunidad económica Euroasiática - CEEA" (2064)
-- aparecen como destino en obtenerPaisProducto pero NO estan en el catalogo de
-- paises. Se marcan para poder ofrecerlos en el modulo Agrocalidad sin que se
-- confundan con paises reales.
-- ------------------------------------------------------------
ALTER TABLE countries
    ADD COLUMN IF NOT EXISTS es_bloque_agrocalidad BOOLEAN NOT NULL DEFAULT false;

COMMENT ON COLUMN countries.es_bloque_agrocalidad IS
    'true = no es un pais sino un bloque comercial destino de Agrocalidad (Unión Europea, CEEA). Se insertan con active = false para no aparecer en los listados del resto de modulos.';


-- ------------------------------------------------------------
-- 3. Mapeo de los 255 paises
--
-- El cruce se hace por `name_es` normalizado (mayusculas sin tildes) contra el
-- catalogo, que se carga desde el script de datos. Aqui solo queda la
-- estructura; la carga vive en scripts, para poder revisarla antes de aplicarla.
-- ------------------------------------------------------------

-- Los dos bloques se insertan aqui porque son datos fijos, no un cruce:
-- active = false para que queden fuera de los listados existentes
-- (cotizacion.py y el modulo Agrocalidad filtran por active = true).
INSERT INTO countries (code, name, name_es, nombre_agrocalidad,
                       id_localizacion_agrocalidad, es_bloque_agrocalidad, active)
VALUES
    ('AGRO-UE',   'European Union',            'Unión Europea',
     'Unión Europea', 2062, true, false),
    ('AGRO-CEEA', 'Eurasian Economic Union',   'Comunidad económica Euroasiática - CEEA',
     'Comunidad económica Euroasiática - CEEA', 2064, true, false)
ON CONFLICT (code) DO UPDATE SET
    name_es = EXCLUDED.name_es,
    nombre_agrocalidad = EXCLUDED.nombre_agrocalidad,
    id_localizacion_agrocalidad = EXCLUDED.id_localizacion_agrocalidad,
    es_bloque_agrocalidad = true,
    updated_at = now();


-- ------------------------------------------------------------
-- 4. Indice para el cruce inverso (id de Agrocalidad -> pais de BLIS)
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_countries_localizacion_agrocalidad
    ON countries (id_localizacion_agrocalidad)
    WHERE id_localizacion_agrocalidad IS NOT NULL;
