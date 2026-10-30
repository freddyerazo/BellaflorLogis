-- Revision de seguridad 2026-10-30: activa Row Level Security en tablas que
-- no lo tenian. Sin politica = acceso denegado por defecto para cualquier
-- rol que no sea dueno de la tabla -- BLIS se conecta siempre con un rol que
-- no pasa por RLS (DATABASE_URL), asi que esto no cambia nada en su
-- operacion normal.
--
-- Un par de tablas de courier quedan deliberadamente fuera de esta
-- migracion por una dependencia externa que hay que resolver antes --
-- ver nota en CLAUDE.md, no detallar aqui (repo publico).

ALTER TABLE public.armellini_exports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cotizaciones ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.telegram_conversation_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dartis_ventas_duplicados_respaldo ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.special_dispatch_audits ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.truck_company ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agrocalidad_requirement_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agrocalidad_requisitos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.vue_productos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public._migrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.expoflor_operaciones_cajas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.special_dispatches ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.farms ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.farm_postcosecha ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.armellini_consignees ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.armellini_product_overrides ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.courier_agency_mapping ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.courier_reconciliation ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dartis_ventas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.courier_bot_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.entregas_locales ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.entregas_locales_detalle ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.entregas_locales_raw ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cargo_agencies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cargo_agencies_equivalencias ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dartis_entregas_cruce ENABLE ROW LEVEL SECURITY;
