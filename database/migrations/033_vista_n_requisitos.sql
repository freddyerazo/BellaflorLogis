-- ============================================================
--  033_vista_n_requisitos.sql
--  Agrega `n_requisitos` a v_agrocalidad_requisitos.
--
--  Por que hace falta: el historial de la pestaña muestra una columna
--  "Requisitos" y debe listar solo las combinaciones que efectivamente exigen
--  algo. Contar `jsonb_array_length(requisitos)` no alcanza, porque las filas
--  que quedaron del scraping viejo tienen 0 items estructurados pero SI tienen
--  requisitos en el texto plano `requirements` (formato "R1: ... | R2: ...").
--  Ejemplo real: Euphorbia -> Estados Unidos tiene 12 requisitos en el texto y
--  0 items. Filtrar por items la habria ocultado; mostrarla con "0" es igual de
--  incorrecto.
--
--  n_requisitos resuelve las dos: usa los items estructurados y, si no hay,
--  cuenta los marcadores Rn: del texto historico.
--
--  Estado al momento de crearla (275 filas activas):
--     238  api      con items          -> se listan
--      37  api      sin requisitos     -> quedan fuera
--       7  scraping con texto (1 a 12) -> se listan, con su conteo real
--      15  scraping sin nada           -> quedan fuera
-- ============================================================

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
    ) AS requisitos,
    -- Cuantos requisitos exige esta combinacion, sirva el formato que sirva.
    GREATEST(
        (SELECT count(*) FROM agrocalidad_requirement_items i
         WHERE i.requirement_id = r.id),
        -- Fallback para las filas historicas del scraping: marcadores "Rn:"
        COALESCE((SELECT count(*)
                  FROM regexp_matches(r.requirements, 'R[0-9]+:', 'g')), 0)
    )::int AS n_requisitos
FROM agrocalidad_requirements r
JOIN species   s ON s.id = r.species_id
JOIN countries c ON c.id = r.country_id
WHERE r.active = true;

COMMENT ON VIEW v_agrocalidad_requisitos IS
    'Consultas de Agrocalidad con sus requisitos ya agregados. `requisitos` es el detalle estructurado (vacio en las filas del scraping viejo); `n_requisitos` es el conteo real y cubre ambos formatos.';
