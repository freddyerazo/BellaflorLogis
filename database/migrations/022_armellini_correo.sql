-- ============================================================
--  022_armellini_correo.sql
--  Aviso por correo de los despachos de Armellini.
--
--  El correo es un RESUMEN (cajas, guia, PO, destinatario): no lleva el
--  XML adjunto. Los destinatarios se configuran por destino de la carga,
--  sobre la misma tabla que ya define el consignee.
-- ============================================================


-- ------------------------------------------------------------
-- Correos por destino. Un destino puede notificar a varias personas.
-- Vacio = ese destino no notifica a nadie (no es un error: simplemente
-- no se envia, y el modulo lo avisa en vez de fallar en silencio).
-- ------------------------------------------------------------
ALTER TABLE armellini_consignees
    ADD COLUMN IF NOT EXISTS emails TEXT[] DEFAULT '{}';


-- ------------------------------------------------------------
-- Registro del envio sobre el propio export. Enviar un correo es una
-- accion hacia afuera: queda anotado a quien se le mando y cuando, para
-- no reenviar por accidente y para poder auditarlo despues.
-- ------------------------------------------------------------
ALTER TABLE armellini_exports
    ADD COLUMN IF NOT EXISTS correo_enviado_at    TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS correo_destinatarios TEXT[] DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS correo_asunto        TEXT;
