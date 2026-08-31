"""Completa en `countries` el mapeo con el catalogo de paises de Agrocalidad.

Fuente: RestWsOperadores/obtenerLozalizacion/0 (255 paises, {id, nombre}).
El cruce es por `name_es` normalizado — esa columna ya trae el nombre exacto de
Agrocalidad desde el proyecto original, y da 255 de 255 sin excepciones.

Escribe solo `id_localizacion_agrocalidad` y `nombre_agrocalidad`; no toca
ningun otro dato de la tabla. Es idempotente: correrlo de nuevo no duplica ni
cambia nada si el catalogo no cambio.

Uso:
    cd backend
    C:\\dev\\venvs\\blis\\Scripts\\python.exe scripts/cargar_paises_agrocalidad.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from psycopg2.extras import execute_values          # noqa: E402
from sqlalchemy import text                         # noqa: E402

from app.database.connection import engine          # noqa: E402
from app.services.agrocalidad_api import _pedir, normalizar   # noqa: E402


def main() -> int:
    catalogo = _pedir("RestWsOperadores/obtenerLozalizacion/0")
    print(f"Catalogo de Agrocalidad: {len(catalogo)} paises")

    por_norm = {normalizar(x["nombre"]): x for x in catalogo}

    with engine.connect() as conn:
        paises = conn.execute(text("""
            SELECT id, code, name, name_es
            FROM countries
            WHERE es_bloque_agrocalidad = false
        """)).mappings().all()

    actualizar, sin_match = [], []
    for p in paises:
        agro = por_norm.get(normalizar(p["name_es"] or "")) \
            or por_norm.get(normalizar(p["name"] or ""))
        if agro:
            actualizar.append((str(p["id"]), agro["id"], agro["nombre"]))
        else:
            sin_match.append(p)

    print(f"  con equivalente en Agrocalidad : {len(actualizar)}")
    print(f"  sin equivalente                : {len(sin_match)}")
    for p in sin_match:
        print(f"     {p['code']}  name='{p['name']}'  name_es='{p['name_es']}'")

    if not actualizar:
        print("Nada que actualizar.")
        return 0

    # En lote: fila por fila serian ~195 ms cada una (ver rules/coding-style.md).
    with engine.begin() as conn:
        cursor = conn.connection.cursor()
        execute_values(cursor, """
            UPDATE countries AS c SET
                id_localizacion_agrocalidad = v.id_loc,
                nombre_agrocalidad          = v.nombre,
                updated_at                  = now()
            FROM (VALUES %s) AS v(id, id_loc, nombre)
            WHERE c.id = v.id::uuid
        """, actualizar)

    with engine.connect() as conn:
        con_id = conn.execute(text("""
            SELECT count(*) FROM countries WHERE id_localizacion_agrocalidad IS NOT NULL
        """)).scalar()
        total = conn.execute(text("SELECT count(*) FROM countries")).scalar()

    print(f"\n>>> {len(actualizar)} paises actualizados")
    print(f">>> countries con id de Agrocalidad: {con_id} de {total} "
          f"(incluye los 2 bloques comerciales)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
