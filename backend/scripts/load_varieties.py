"""One-time load of varieties from import_species_varieties, linked to species."""

from sqlalchemy import text

from app.database.connection import engine

INSERT_VARIETIES = text(
    """
    INSERT INTO varieties (species_id, name)
    SELECT DISTINCT s.id, isv.variety_name
    FROM import_species_varieties isv
    JOIN species s ON s.code = isv.species_name
    WHERE isv.variety_name IS NOT NULL AND isv.variety_name <> ''
    AND NOT EXISTS (
        SELECT 1 FROM varieties v
        WHERE v.species_id = s.id AND v.name = isv.variety_name
    )
    """
)

with engine.begin() as conn:
    r = conn.execute(INSERT_VARIETIES)
    print(f"varieties inserted: {r.rowcount}")
