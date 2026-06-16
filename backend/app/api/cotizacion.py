from fastapi import APIRouter
from sqlalchemy import text

from app.database.connection import engine

router = APIRouter()


@router.get("/cotizacion/catalogo")
def get_catalogo():
    """Devuelve todos los catálogos necesarios para el wizard de cotización."""
    with engine.connect() as conn:

        # Países de ORIGEN con tarifa aérea activa en la fecha actual
        paises_origen = conn.execute(text("""
            SELECT DISTINCT c.id, c.code, c.name
            FROM countries c
            INNER JOIN airports a  ON a.country_id = c.id
            INNER JOIN airline_tariffs t ON t.origin_airport_id = a.id
                AND t.active = true
                AND t.valid_from <= CURRENT_DATE
                AND (t.valid_to IS NULL OR t.valid_to >= CURRENT_DATE)
            WHERE c.active = true
            ORDER BY c.name
        """)).mappings().all()

        # Países de DESTINO con tarifa aérea activa en la fecha actual
        paises_destino = conn.execute(text("""
            SELECT DISTINCT c.id, c.code, c.name
            FROM countries c
            INNER JOIN airports a  ON a.country_id = c.id
            INNER JOIN airline_tariffs t ON t.destination_airport_id = a.id
                AND t.active = true
                AND t.valid_from <= CURRENT_DATE
                AND (t.valid_to IS NULL OR t.valid_to >= CURRENT_DATE)
            WHERE c.active = true
            ORDER BY c.name
        """)).mappings().all()

        # species: id, code, name
        especies = conn.execute(text(
            "SELECT * FROM species WHERE active = true ORDER BY name"
        )).mappings().all()

        # varieties: id, species_id, code, name
        variedades = conn.execute(text(
            "SELECT id, species_id, code, name FROM varieties WHERE active = true ORDER BY name"
        )).mappings().all()

        # product_sizes: id, species_id, size_code, description
        grados = conn.execute(text("""
            SELECT ps.id, ps.size_code, ps.description, s.name AS species_name
            FROM product_sizes ps
            JOIN species s ON s.id = ps.species_id
            WHERE ps.active = true
            ORDER BY s.name, ps.size_code
        """)).mappings().all()

        # box_types: id, box_code, box_name, length_cm, width_cm, height_cm, reference_weight_kg
        box_types = conn.execute(text(
            "SELECT * FROM box_types WHERE active = true ORDER BY length_cm DESC"
        )).mappings().all()

        # airlines: id, airline_code, airline_name
        aerolineas = conn.execute(text(
            "SELECT * FROM airlines WHERE active = true ORDER BY airline_name"
        )).mappings().all()

        # rutas activas: qué aerolíneas tienen tarifa vigente por par de aeropuertos
        rutas_activas = conn.execute(text("""
            SELECT DISTINCT
                t.airline_id,
                t.origin_airport_id,
                t.destination_airport_id
            FROM airline_tariffs t
            WHERE t.active = true
                AND t.valid_from <= CURRENT_DATE
                AND (t.valid_to IS NULL OR t.valid_to >= CURRENT_DATE)
        """)).mappings().all()

        # airports: id, iata_code, airport_name, city, country_id
        aeropuertos = conn.execute(text("""
            SELECT a.*, c.code AS country_code, c.name AS country_name
            FROM airports a
            LEFT JOIN countries c ON c.id = a.country_id
            WHERE a.active = true
            ORDER BY a.city
        """)).mappings().all()

        # providers — columnas desconocidas, uso SELECT *
        proveedores = []
        try:
            proveedores = conn.execute(text(
                "SELECT * FROM providers WHERE active = true ORDER BY id"
            )).mappings().all()
        except Exception:
            pass

        # incoterms — columnas desconocidas, uso SELECT *
        incoterms_list = []
        try:
            incoterms_list = conn.execute(text(
                "SELECT * FROM incoterms ORDER BY id"
            )).mappings().all()
        except Exception:
            pass

        # exchange_rates — columnas desconocidas, uso SELECT *
        fx_rates = []
        try:
            fx_rates = conn.execute(text(
                "SELECT * FROM exchange_rates ORDER BY rate_date DESC LIMIT 10"
            )).mappings().all()
        except Exception:
            pass

    return {
        "paises_origen":  [dict(r) for r in paises_origen],
        "paises_destino": [dict(r) for r in paises_destino],
        "especies":       [dict(r) for r in especies],
        "variedades":     [dict(r) for r in variedades],
        "grados":         [dict(r) for r in grados],
        "box_types":      [dict(r) for r in box_types],
        "aerolineas":     [dict(r) for r in aerolineas],
        "rutas_activas":  [dict(r) for r in rutas_activas],
        "aeropuertos":    [dict(r) for r in aeropuertos],
        "proveedores":    [dict(r) for r in proveedores],
        "incoterms":      [dict(r) for r in incoterms_list],
        "exchange_rates": [dict(r) for r in fx_rates],
    }
