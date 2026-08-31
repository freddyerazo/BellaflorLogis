"""Llena `countries.cod_agroca` con el codigo de pais ISO 3166-1 alfa-2.

POR QUE ISO Y NO AGROCALIDAD
----------------------------
La API de Agrocalidad no entrega ningun codigo de pais: RestWsOperadores/
obtenerLozalizacion/0 devuelve 255 elementos con solo {id, nombre}, y en el
binario de la app AGRO Movil los unicos campos de pais son `nombre_pais` y
`pais`. El codigo de dos letras es el ISO 3166-1 alfa-2, que ya venia correcto
en 108 filas de `countries.code`; el resto se resuelve por nombre.

El identificador propio de Agrocalidad es `id_localizacion_agrocalidad`, no este.

COMO RESUELVE
-------------
1. Si `countries.code` ya son 2 letras, se respeta (fuente de verdad existente).
2. Si el nombre coincide literal con un nombre ISO, se toma ese.
3. Si es un nombre en español sin equivalente literal, se usa la tabla
   EQUIVALENCIAS de abajo — explicita a proposito, para que el mapeo sea
   auditable y no dependa de una busqueda difusa.
4. Las entidades que no son paises ISO quedan en NULL.

Requiere `pycountry`, que es dependencia SOLO de este script (produccion no lo
necesita, por eso no esta en requirements.txt):

    C:\\dev\\venvs\\blis\\Scripts\\python.exe -m pip install pycountry

Uso:
    cd backend
    C:\\dev\\venvs\\blis\\Scripts\\python.exe scripts/cargar_cod_agroca.py
"""

import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pycountry                                    # noqa: E402
from psycopg2.extras import execute_values          # noqa: E402
from sqlalchemy import text                         # noqa: E402

from app.database.connection import engine          # noqa: E402


def norm(s: str) -> str:
    s = str(s or "").strip().upper()
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


# Nombres en español (o variantes historicas) sin coincidencia literal en ISO.
# Explicitos a proposito: un mapeo de paises no se adivina.
EQUIVALENCIAS = {
    "ALEMANIA": "DE", "ANTILLAS HOLANDESAS": "AN", "ARABIA SAUDITA": "SA",
    "AZERBAIYAN": "AZ", "BELGICA": "BE", "BIELORRUSIA": "BY", "BRASIL": "BR",
    "CAMERUN": "CM", "CANADA": "CA", "CATAR": "QA", "CHIPRE": "CY",
    "COREA DEL NORTE": "KP", "COREA DEL SUR": "KR", "COSTA DE MARFIL": "CI",
    "CROACIA": "HR", "DINAMARCA": "DK", "EGIPTO": "EG",
    "EMIRATOS ARABES UNIDOS": "AE", "ESLOVAQUIA": "SK", "ESLOVENIA": "SI",
    "ESPAÑA": "ES", "ESPANA": "ES", "ESTADOS UNIDOS": "US", "ETIOPIA": "ET",
    "FILIPINAS": "PH", "FINLANDIA": "FI", "FRANCIA": "FR", "GRECIA": "GR",
    "GUADALUPE": "GP", "GUAYANA FRANCESA": "GF", "HAITI": "HT", "HUNGRIA": "HU",
    "IRLANDA": "IE", "IRAN": "IR", "ITALIA": "IT", "JAPON": "JP",
    "KIRGUISTAN": "KG", "LETONIA": "LV", "LIBANO": "LB", "LITUANIA": "LT",
    "MALASIA": "MY", "MALDIVAS": "MV", "MARRUECOS": "MA", "MARTINICA": "MQ",
    "MEXICO": "MX", "MOLDAVIA": "MD", "NORUEGA": "NO", "PAISES BAJOS": "NL",
    "PANAMA": "PA", "PERU": "PE", "POLINESIA FRANCESA": "PF", "POLONIA": "PL",
    "REINO UNIDO": "GB", "REPUBLICA CHECA": "CZ", "REPUBLICA DE COREA": "KR",
    "REPUBLICA DE MACEDONIA DEL NORTE": "MK", "REPUBLICA DOMINICANA": "DO",
    "REUNION": "RE", "RUANDA": "RW", "RUMANIA": "RO", "RUSIA": "RU",
    "SIRIA": "SY", "SUDAFRICA": "ZA", "SUDAN": "SD", "SUECIA": "SE",
    "SUIZA": "CH", "SURINAM": "SR", "TAILANDIA": "TH", "TAIWAN": "TW",
    "TAYIKISTAN": "TJ", "TRINIDAD Y TOBAGO": "TT", "TURQUIA": "TR",
    "UCRANIA": "UA", "UZBEKISTAN": "UZ",
    # Nombres que la ISO renombro o escribe distinto
    "CAPE VERDE": "CV",                          # ISO: Cabo Verde
    "LAO PEOPLE S DEMOCRATIC REPUBLIC": "LA",    # el apostrofo se perdio al cargar
    "PALESTINIAN TERRITORY, OCCUPIED": "PS",     # ISO: Palestine, State of
    "SWAZILAND": "SZ",                           # ISO: Eswatini desde 2018
}

# No son paises ISO: no existe alfa-2 para ellos y deben quedar en NULL.
SIN_ISO = {
    "AGUAS INTERNACIONALES", "ESCOCIA", "GALES", "INGLATERRA",
    "UNION EUROPEA", "COMUNIDAD ECONOMICA EUROASIATICA - CEEA",
}


def indice_iso() -> dict:
    idx = {}
    for p in pycountry.countries:
        for attr in ("name", "common_name", "official_name"):
            v = getattr(p, attr, None)
            if v:
                idx.setdefault(norm(v), p.alpha_2)
    return idx


def resolver(fila, idx) -> tuple:
    """Devuelve (codigo|None, origen)."""
    code = (fila["code"] or "").strip()
    if len(code) == 2 and code.isalpha():
        return code.upper(), "ya estaba en countries.code"

    for campo in ("name_es", "nombre_agrocalidad", "name"):
        n = norm(fila[campo])
        if n in SIN_ISO:
            return None, "no es un pais ISO"
        if n in EQUIVALENCIAS:
            return EQUIVALENCIAS[n], "equivalencia declarada"
        if n in idx:
            return idx[n], "nombre ISO literal"
    return None, "sin equivalencia"


def main() -> int:
    idx = indice_iso()
    with engine.connect() as conn:
        filas = conn.execute(text("""
            SELECT id, code, name, name_es, nombre_agrocalidad
            FROM countries ORDER BY name_es
        """)).mappings().all()

    actualizar, nulos = [], []
    origenes = Counter()
    for f in filas:
        cod, origen = resolver(f, idx)
        origenes[origen] += 1
        if cod:
            actualizar.append((str(f["id"]), cod))
        else:
            nulos.append((f, origen))

    print(f"paises              : {len(filas)}")
    print(f"con codigo resuelto : {len(actualizar)}")
    print(f"sin codigo (NULL)   : {len(nulos)}")
    for origen, n in origenes.most_common():
        print(f"   {n:>4}  {origen}")

    if nulos:
        print("\nsin codigo:")
        for f, motivo in nulos:
            print(f"   {str(f['name_es'])[:44]:46} {motivo}")

    if not actualizar:
        return 0

    with engine.begin() as conn:
        cursor = conn.connection.cursor()
        execute_values(cursor, """
            UPDATE countries AS c
            SET cod_agroca = v.cod, updated_at = now()
            FROM (VALUES %s) AS v(id, cod)
            WHERE c.id = v.id::uuid
        """, actualizar)

    with engine.connect() as conn:
        con = conn.execute(text(
            "SELECT count(*) FROM countries WHERE cod_agroca IS NOT NULL")).scalar()
        dup = conn.execute(text("""
            SELECT cod_agroca, count(*) FROM countries
            WHERE cod_agroca IS NOT NULL GROUP BY 1 HAVING count(*) > 1
        """)).all()

    print(f"\n>>> {len(actualizar)} paises actualizados · {con} con cod_agroca")
    if dup:
        print(">>> codigos compartidos (esperado, el catalogo de Agrocalidad los duplica):")
        for cod, n in dup:
            print(f"      {cod}: {n} filas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
