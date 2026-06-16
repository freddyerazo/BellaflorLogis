"""One-time normalization of import_species_varieties into species and product_sizes."""

from sqlalchemy import text

from app.database.connection import engine

INSERT_SPECIES = text(
    """
    INSERT INTO species (code, name)
    SELECT DISTINCT species_name, species_name
    FROM import_species_varieties
    WHERE species_name IS NOT NULL AND species_name <> ''
    ON CONFLICT (code) DO NOTHING
    """
)

INSERT_PRODUCT_SIZES = text(
    """
    INSERT INTO product_sizes (species_id, size_code)
    SELECT DISTINCT s.id, isv.grade
    FROM import_species_varieties isv
    JOIN species s ON s.code = isv.species_name
    WHERE isv.grade IS NOT NULL AND isv.grade <> ''
    AND NOT EXISTS (
        SELECT 1 FROM product_sizes ps
        WHERE ps.species_id = s.id AND ps.size_code = isv.grade
    )
    """
)

with engine.begin() as conn:
    r1 = conn.execute(INSERT_SPECIES)
    print(f"species inserted: {r1.rowcount}")

    r2 = conn.execute(INSERT_PRODUCT_SIZES)
    print(f"product_sizes inserted: {r2.rowcount}")
