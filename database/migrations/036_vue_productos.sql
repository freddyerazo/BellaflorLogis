-- ============================================================
--  036_vue_productos.sql
--  Registro de la Ventanilla Unica Ecuatoriana (VUE): que productos esta
--  autorizada cada empresa a exportar y hacia que paises.
--
--  Origen: el archivo "Lista de Producto.xls" que se descarga de la VUE. Es un
--  .xls legacy (OLE2), no xlsx — por eso el importador usa xlrd.
--
--  El archivo es POR RUC: cada empresa descarga el suyo. Bellaflor exporta con
--  tres (Expoflor, Oasisflower, Amazingroses), asi que la tabla se llena
--  subiendo un archivo por empresa y la clave unica incluye el ruc.
--
--  ACTUALIZA, NO BORRA: el upsert refresca lo que ya existe y agrega lo nuevo,
--  pero nunca da de baja filas. Una autorizacion que deje de aparecer en un
--  archivo posterior queda igual, porque un archivo parcial no es prueba de
--  que la autorizacion se haya revocado.
--
--  LLAVE DE CRUCE — lo que hace util esta tabla:
--    codigo_producto  = "A0001", el mismo formato que agrocalidad_requirements
--                       .agrocalidad_code (con la letra al frente)
--    partida          = los 10 primeros digitos de la subpartida, que coinciden
--                       con agrocalidad_requirements.tariff_heading
--    pais_cod         = ISO alfa-2, el mismo que countries.cod_agroca
--  Verificado: los 56 paises del archivo de Expoflor resuelven contra
--  cod_agroca sin excepciones, y 60 de 81 pares (codigo, partida) de BLIS
--  coinciden con la VUE.
--
--  OJO: codigo_producto NO identifica un producto por si solo. En el archivo de
--  Expoflor, A0001 cubre ROSA, CLAVEL, CRISANTEMO, ASTER, GERBERA,
--  ALSTROEMERIA, ACHILLEA y MINICLAVEL — la misma colision que ya tiene
--  Agrocalidad. Lo que las distingue es la subpartida, por eso va en la clave.
-- ============================================================

CREATE TABLE IF NOT EXISTS vue_productos (
    id                  BIGSERIAL   PRIMARY KEY,

    -- A quien pertenece el registro
    ruc                 TEXT        NOT NULL,
    empresa             TEXT,                     -- rotulo que pone el usuario al subir

    -- Clasificacion que trae la VUE
    actividad_comercial TEXT,                     -- prdt_act_cd
    tipo_producto       TEXT,                     -- prdt_type_cd

    -- Producto
    codigo_producto     TEXT        NOT NULL,     -- prdt_cd, "A0001"
    subpartida          TEXT        NOT NULL,     -- hc, 18 digitos tal cual
    partida             TEXT,                     -- 10 primeros, para cruzar
    nombre_producto     TEXT,                     -- prdt_nm
    nombre_cientifico   TEXT,                     -- prdt_stn (viene vacio en el archivo actual)

    -- Destino
    pais_cod            TEXT        NOT NULL,     -- org_ntn_cd, ISO alfa-2
    country_id          UUID        REFERENCES countries(id),

    -- Trazabilidad
    archivo             TEXT,
    importado_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (ruc, codigo_producto, subpartida, pais_cod)
);

COMMENT ON TABLE vue_productos IS
    'Autorizaciones de exportacion de la Ventanilla Unica, por RUC. Se actualiza con cada archivo subido y nunca se borra: un archivo parcial no prueba que una autorizacion se haya revocado.';

COMMENT ON COLUMN vue_productos.codigo_producto IS
    'prdt_cd de la VUE, formato "A0001". Coincide con agrocalidad_requirements.agrocalidad_code. NO identifica un producto por si solo: hay que combinarlo con la subpartida.';

COMMENT ON COLUMN vue_productos.partida IS
    'Los 10 primeros digitos de la subpartida. Es lo que cruza contra agrocalidad_requirements.tariff_heading.';

COMMENT ON COLUMN vue_productos.pais_cod IS
    'ISO alfa-2 del destino. Cruza contra countries.cod_agroca.';

-- El cruce de la verificacion entra por aqui.
CREATE INDEX IF NOT EXISTS idx_vue_cruce
    ON vue_productos (codigo_producto, partida, pais_cod);

CREATE INDEX IF NOT EXISTS idx_vue_ruc
    ON vue_productos (ruc);
