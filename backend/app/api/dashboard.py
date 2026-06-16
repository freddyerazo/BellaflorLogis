from fastapi import APIRouter
from sqlalchemy import text

from app.database.connection import engine

router = APIRouter()


@router.get("/dashboard/summary")
def dashboard_summary():
    with engine.connect() as conn:
        summary = conn.execute(
            text(
                """
                SELECT
                    (SELECT COUNT(*) FROM species)          AS species,
                    (SELECT COUNT(*) FROM varieties)        AS varieties,
                    (SELECT COUNT(*) FROM product_sizes)    AS product_sizes,
                    (SELECT COUNT(*) FROM box_types)        AS box_types,
                    (SELECT COUNT(*) FROM airports)         AS airports,
                    (SELECT COUNT(*) FROM airlines)         AS airlines,
                    (SELECT COUNT(*) FROM customers)        AS customers,
                    (SELECT COUNT(*) FROM markets)          AS markets,
                    (SELECT COUNT(*) FROM providers)        AS providers,
                    (SELECT COUNT(*) FROM incoterms)        AS incoterms,
                    (SELECT COUNT(*) FROM cost_components)  AS cost_components,
                    (SELECT COUNT(*) FROM roles)            AS roles,
                    (SELECT COUNT(*) FROM profiles)         AS profiles,
                    (SELECT COUNT(*) FROM scenario_headers) AS scenarios
                """
            )
        ).mappings().first()

        # Top 5 especies por número de variedades
        top_species = conn.execute(
            text(
                """
                SELECT s.name AS species_name, COUNT(v.id) AS variety_count
                FROM species s
                LEFT JOIN varieties v ON v.species_id = s.id AND v.active = true
                WHERE s.active = true
                GROUP BY s.id, s.name
                ORDER BY variety_count DESC
                LIMIT 5
                """
            )
        ).mappings().all()

        # Distribución de tipos de caja (con dimensiones)
        box_distribution = conn.execute(
            text(
                """
                SELECT box_code, box_name, length_cm, width_cm, height_cm
                FROM box_types
                WHERE active = true
                ORDER BY length_cm DESC
                LIMIT 8
                """
            )
        ).mappings().all()

        # Último escenario calculado
        last_scenario = conn.execute(
            text(
                """
                SELECT
                    sh.scenario_code,
                    sh.scenario_name,
                    sh.created_at,
                    COUNT(sd.id) AS detail_lines,
                    SUM(sd.boxes) AS total_boxes,
                    SUM(sd.chargeable_weight_kg) AS total_chargeable_kg,
                    (
                        SELECT SUM(scr.amount)
                        FROM scenario_cost_results scr
                        WHERE scr.scenario_id = sh.id
                    ) AS total_cost_usd
                FROM scenario_headers sh
                LEFT JOIN scenario_details sd ON sd.scenario_id = sh.id
                GROUP BY sh.id, sh.scenario_code, sh.scenario_name, sh.created_at
                ORDER BY sh.created_at DESC
                LIMIT 1
                """
            )
        ).mappings().first()

        # Componentes de costo del último escenario
        cost_breakdown = []
        if last_scenario:
            cost_breakdown = conn.execute(
                text(
                    """
                    SELECT cc.component_name, scr.amount, scr.currency_code
                    FROM scenario_cost_results scr
                    JOIN cost_components cc ON cc.id = scr.cost_component_id
                    JOIN scenario_headers sh ON sh.id = scr.scenario_id
                    ORDER BY sh.created_at DESC, scr.amount DESC
                    LIMIT 10
                    """
                )
            ).mappings().all()

        return {
            "summary": dict(summary),
            "top_species": [dict(r) for r in top_species],
            "box_distribution": [dict(r) for r in box_distribution],
            "last_scenario": dict(last_scenario) if last_scenario else None,
            "cost_breakdown": [dict(r) for r in cost_breakdown],
        }
