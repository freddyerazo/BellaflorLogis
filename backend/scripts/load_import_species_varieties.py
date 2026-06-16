"""One-time load of backups/Tabla.csv into import_species_varieties."""

import csv
from pathlib import Path

from sqlalchemy import text

from app.database.connection import engine

CSV_PATH = Path(__file__).resolve().parents[2] / "backups" / "Tabla.csv"

with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    rows = [
        {
            "species_name": row["species"].strip(),
            "variety_name": row["variety"].strip(),
            "grade": row["grade"].strip(),
        }
        for row in reader
    ]

print(f"Read {len(rows)} rows from {CSV_PATH}")

with engine.begin() as conn:
    conn.execute(text("TRUNCATE TABLE import_species_varieties"))
    conn.execute(
        text(
            """
            INSERT INTO import_species_varieties (species_name, variety_name, grade)
            VALUES (:species_name, :variety_name, :grade)
            """
        ),
        rows,
    )

print("Done.")
