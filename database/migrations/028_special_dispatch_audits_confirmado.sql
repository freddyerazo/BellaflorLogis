-- ============================================================
--  028_special_dispatch_audits_confirmado.sql
--  Simplifica el formulario del bot: en vez de 3 preguntas Si/No
--  (tipo de caja, especie, etiqueta) + cajas + piezas + nombre del
--  auditor por separado, se muestra un resumen unico del despacho
--  y el auditor solo confirma o no confirma que coincide con la
--  venta. El auditor se captura solo del perfil de Telegram (ya no
--  se pregunta). Las fotos pasan de una sola a varias.
--
--  Hay 1 auditoria real ya registrada en produccion (probada por un
--  auditor de verdad) -- se preserva migrando sus datos al nuevo
--  esquema en vez de perderla.
-- ============================================================

ALTER TABLE special_dispatch_audits
    ADD COLUMN confirmado BOOLEAN,
    ADD COLUMN foto_urls TEXT[];

UPDATE special_dispatch_audits
SET confirmado = (tipo_caja_ok AND especie_ok AND etiqueta_ok),
    foto_urls = CASE WHEN foto_url IS NOT NULL THEN ARRAY[foto_url] ELSE '{}' END;

ALTER TABLE special_dispatch_audits
    ALTER COLUMN confirmado SET NOT NULL,
    ALTER COLUMN foto_urls SET NOT NULL,
    ALTER COLUMN foto_urls SET DEFAULT '{}',
    DROP COLUMN piezas_despachadas,
    DROP COLUMN tipo_caja_ok,
    DROP COLUMN especie_ok,
    DROP COLUMN etiqueta_ok,
    DROP COLUMN foto_url;
