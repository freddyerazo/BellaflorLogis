"""
migrate.py — Ejecuta todas las migraciones SQL en orden sobre Supabase.

Uso:
    cd BLIS/backend
    python ../scripts/migrate.py

Requisito: archivo backend/.env con DATABASE_URL configurado.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# ── Rutas ────────────────────────────────────────────────────────────────────
SCRIPT_DIR     = Path(__file__).resolve().parent
BLIS_DIR       = SCRIPT_DIR.parent
MIGRATIONS_DIR = BLIS_DIR / "database" / "migrations"
ENV_FILE       = BLIS_DIR / "backend" / ".env"

# ── Cargar .env ───────────────────────────────────────────────────────────────
load_dotenv(ENV_FILE)
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌  DATABASE_URL no encontrado.")
    print(f"    Crea el archivo: {ENV_FILE}")
    print("    Con el contenido: DATABASE_URL=postgresql://postgres:[PASSWORD]@db.<ref>.supabase.co:5432/postgres")
    sys.exit(1)

# ── Tabla de control de migraciones ──────────────────────────────────────────
CREATE_MIGRATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS _migrations (
    id         SERIAL      PRIMARY KEY,
    filename   TEXT        UNIQUE NOT NULL,
    applied_at TIMESTAMPTZ DEFAULT now()
);
"""

# ── Ejecutar ──────────────────────────────────────────────────────────────────
def main():
    engine = create_engine(DATABASE_URL)

    with engine.begin() as conn:
        conn.execute(text(CREATE_MIGRATIONS_TABLE))

        applied = {
            row[0]
            for row in conn.execute(text("SELECT filename FROM _migrations"))
        }

    # Ordenar archivos .sql por nombre (001_, 002_, ...)
    sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

    if not sql_files:
        print("⚠️  No se encontraron archivos .sql en:", MIGRATIONS_DIR)
        sys.exit(0)

    print(f"\n📂  Migraciones encontradas: {len(sql_files)}\n")

    pendientes = [f for f in sql_files if f.name not in applied]

    if not pendientes:
        print("✅  Todas las migraciones ya están aplicadas. Nada que hacer.\n")
        sys.exit(0)

    with engine.begin() as conn:
        for sql_file in pendientes:
            sql = sql_file.read_text(encoding="utf-8")
            print(f"  ⏳  Aplicando: {sql_file.name} ...", end=" ")
            try:
                conn.execute(text(sql))
                conn.execute(
                    text("INSERT INTO _migrations (filename) VALUES (:fn)"),
                    {"fn": sql_file.name},
                )
                print("✅")
            except Exception as err:
                print(f"\n❌  Error en {sql_file.name}:\n    {err}")
                raise

    print(f"\n🎉  {len(pendientes)} migración(es) aplicada(s) correctamente.\n")


if __name__ == "__main__":
    main()
