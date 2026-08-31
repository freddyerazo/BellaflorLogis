-- ============================================================
--  032_countries_cod_agroca.sql
--  Codigo de pais de dos letras en `countries`, para cruzar destinos.
--
--  ORIGEN DEL DATO — leer antes de usarlo:
--  La API de Agrocalidad NO entrega ningun codigo de pais. Se verificaron los
--  255 elementos de RestWsOperadores/obtenerLozalizacion/0 (solo {id, nombre})
--  y las cadenas del binario de la app AGRO Movil (solo `nombre_pais` y
--  `pais`). No existe ISO, sigla ni abreviatura en ningun endpoint.
--
--  Por eso `cod_agroca` se llena con el **ISO 3166-1 alfa-2**, que es el
--  estandar de dos letras (NL, US, CL, EC). Es un dato DERIVADO del estandar
--  internacional, no publicado por Agrocalidad. El identificador propio de
--  Agrocalidad sigue siendo `id_localizacion_agrocalidad`, que es el que va en
--  la ruta de obtenerRequisitosPorPais.
--
--  Origen de cada valor (medido sobre las 257 filas):
--    108  ya estaba correcto en `countries.code`
--    116  nombre que coincide literal con el nombre ISO
--     27  equivalencia español->ingles declarada explicitamente en el script
--     10  quedan NULL (ver abajo)
--
--  NO lleva restriccion UNIQUE a proposito: el catalogo de Agrocalidad trae
--  "Catar" (id 2061) y "Qatar" (id 1941) como dos paises distintos, y ambos
--  son ISO 'QA'. El duplicado es del origen, no de BLIS.
-- ============================================================

ALTER TABLE countries
    ADD COLUMN IF NOT EXISTS cod_agroca VARCHAR(2);

COMMENT ON COLUMN countries.cod_agroca IS
    'Codigo de pais ISO 3166-1 alfa-2 (NL, US, CL). DERIVADO del estandar ISO: Agrocalidad no publica codigos de pais, solo id y nombre. Queda NULL en las 6 entidades que no son paises ISO (Aguas Internacionales, Escocia, Gales, Inglaterra, Unión Europea, CEEA). Sin UNIQUE: Agrocalidad lista "Catar" y "Qatar" por separado y ambos son QA.';

-- Busqueda por codigo (cruces contra otras fuentes que usen alfa-2).
CREATE INDEX IF NOT EXISTS idx_countries_cod_agroca
    ON countries (cod_agroca)
    WHERE cod_agroca IS NOT NULL;
