"""API del modulo Agrocalidad: requisitos fitosanitarios de exportacion.

Desde el 2026-08-30 consulta directo la API movil de Agrocalidad
(`services/agrocalidad_api.py`) en vez de encolar una solicitud y disparar un
workflow de GitHub Actions con Playwright. La consulta es SINCRONA: ~2,9 s de
mediana en vivo y ~1,2 s reutilizando un resultado guardado, contra los 30-90 s
del worker. Ya no hacen falta la cola `agrocalidad_requests`, el polling del
frontend ni `GITHUB_TOKEN`.

`agrocalidad_requests` se conserva con su historial (49 filas) pero este modulo
ya no escribe en ella.

Resultados: cabecera en `agrocalidad_requirements`, requisitos estructurados en
`agrocalidad_requisitos` (catalogo, PK = id_requisito de Agrocalidad) y
`agrocalidad_requirement_items` (enlace). Ver migracion 030.
"""

from fastapi import APIRouter, HTTPException, Query
from psycopg2.extras import execute_values
from sqlalchemy import text

from app.database.connection import engine
from app.schemas.agrocalidad import AREAS_VALIDAS, AgrocalidadConsultaRequest
from app.services import agrocalidad_api
from app.services.agrocalidad_api import AgrocalidadError

router = APIRouter(prefix="/agrocalidad", tags=["Agrocalidad"])


@router.get("/catalogo")
def get_catalogo():
    """Especies y paises de BLIS, con su id de Agrocalidad ya mapeado.

    Solo se ofrecen los que tienen mapeo: sin `id_producto_agrocalidad` o sin
    `id_localizacion_agrocalidad` la consulta no se puede armar.
    """
    with engine.connect() as conn:
        especies = conn.execute(text("""
            SELECT id, code, name, name_agrocalidad, id_producto_agrocalidad
            FROM species
            WHERE active = true AND id_producto_agrocalidad IS NOT NULL
            ORDER BY name
        """)).mappings().all()

        sin_mapeo = conn.execute(text("""
            SELECT count(*) FROM species
            WHERE active = true AND id_producto_agrocalidad IS NULL
        """)).scalar()

        # Los bloques comerciales (Unión Europea, CEEA) viven en `countries` con
        # active = false para no aparecer en los listados del resto de modulos,
        # pero aqui SI son destinos validos: Agrocalidad publica requisitos a
        # nivel de bloque.
        paises = conn.execute(text("""
            SELECT id, code, name, name_es, nombre_agrocalidad,
                   id_localizacion_agrocalidad, es_bloque_agrocalidad
            FROM countries
            WHERE id_localizacion_agrocalidad IS NOT NULL
              AND (active = true OR es_bloque_agrocalidad = true)
            ORDER BY es_bloque_agrocalidad, name_es NULLS LAST, name
        """)).mappings().all()

    return {
        "especies": especies,
        "paises": paises,
        "especies_sin_mapeo": sin_mapeo,
        "movimientos": list(agrocalidad_api.MOVIMIENTOS),
        "areas": sorted(AREAS_VALIDAS),
    }


@router.get("/productos")
def buscar_productos(q: str = Query(min_length=2), limite: int = 50):
    """Busca en el catalogo de Agrocalidad (flores + follajes).

    Sirve para mapear especies nuevas o consultar productos que BLIS todavia no
    tiene en `species`.
    """
    try:
        return agrocalidad_api.buscar_productos(q, limite)
    except AgrocalidadError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/paises-disponibles/{id_producto}")
def paises_disponibles(id_producto: int, movimiento: str = "Exportación"):
    """Destinos con requisitos publicados para ese producto.

    Permite mostrar solo los paises que van a devolver algo, en vez de dejar al
    usuario probar uno por uno.
    """
    try:
        return agrocalidad_api.paises_producto(id_producto, movimiento)
    except AgrocalidadError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/requisitos")
def list_requisitos(species_id: str | None = None, country_id: str | None = None,
                    solo_con_requisitos: bool = True):
    """Historial de consultas guardadas, con sus requisitos ya estructurados.

    Por defecto lista solo las combinaciones que exigen algo: una especie sin
    requisitos publicados para ese destino no aporta nada al listado. El filtro
    usa `n_requisitos` de la vista, que cuenta tanto los items estructurados
    como los del texto plano del scraping viejo — hay 7 filas historicas con
    requisitos reales (Euphorbia a Estados Unidos tiene 12) y 0 items, y
    filtrarlas por items las habria ocultado.

    Con `solo_con_requisitos=false` se ven todas, incluidas las que dieron cero.
    """
    filtros, params = [], {}
    if species_id:
        filtros.append("species_id = :species_id")
        params["species_id"] = species_id
    if country_id:
        filtros.append("country_id = :country_id")
        params["country_id"] = country_id
    if solo_con_requisitos:
        filtros.append("n_requisitos > 0")
    where = f"WHERE {' AND '.join(filtros)}" if filtros else ""

    with engine.connect() as conn:
        return conn.execute(text(f"""
            SELECT * FROM v_agrocalidad_requisitos
            {where}
            ORDER BY queried_at DESC
            LIMIT 200
        """), params).mappings().all()


@router.get("/requisitos/{requirement_id}")
def get_requisito(requirement_id: str):
    with engine.connect() as conn:
        fila = conn.execute(text("""
            SELECT * FROM v_agrocalidad_requisitos WHERE requirement_id = :id
        """), {"id": requirement_id}).mappings().first()

    if fila is None:
        raise HTTPException(status_code=404, detail="Consulta no encontrada")
    return fila


@router.get("/comparacion")
def comparacion():
    """Agrocalidad vs Ventas: cobertura de lo que Bellaflor realmente exporta.

    Cruza las especies que aparecen en `dartis_ventas` contra el mapeo a
    Agrocalidad y contra los requisitos ya consultados, para responder algo
    concreto: de lo que efectivamente vendemos, ¿que tiene requisitos
    averiguados y que no?

    El cruce por PAIS todavia no se puede armar — `dartis_ventas` no trae el
    pais de destino (solo `cliente` y `destinatario`, que son nombres) — y VUE
    aun no tiene datos cargados. Ambos se informan en `pendientes` para que la
    pantalla lo diga en vez de mostrar una comparacion incompleta como si
    estuviera completa.
    """
    with engine.connect() as conn:
        especies = conn.execute(text("""
            SELECT
                d.especie,
                count(*)                        AS lineas,
                sum(d.total_tallos)             AS tallos,
                sum(d.total_dolares)            AS dolares,
                s.id                            AS species_id,
                s.id_producto_agrocalidad,
                (SELECT count(*) FROM agrocalidad_requirements r
                  WHERE r.species_id = s.id AND r.active) AS consultas,
                (SELECT count(*) FROM v_agrocalidad_requisitos v
                  WHERE v.species_id = s.id AND v.n_requisitos > 0) AS con_requisitos
            FROM dartis_ventas d
            LEFT JOIN species s ON upper(s.name) = upper(d.especie)
            WHERE d.active
            GROUP BY d.especie, s.id, s.id_producto_agrocalidad
            ORDER BY sum(d.total_dolares) DESC NULLS LAST
        """)).mappings().all()

        # ¿ya se puede cruzar por pais?  ¿hay algo de VUE?
        # No alcanza con que exista la columna: hace falta que tenga datos.
        # La columna se agrega con la migracion 034, pero recien se llena
        # cuando se importa un archivo de Ventas que traiga `paisVenta`.
        pais_en_ventas = conn.execute(text("""
            SELECT count(*) FROM dartis_ventas
            WHERE active AND country_id IS NOT NULL
        """)).scalar()

    return {
        "especies": especies,
        "pendientes": {
            "pais_en_ventas": bool(pais_en_ventas),
            "vue": False,
        },
    }


# Una consulta guardada mas nueva que esto se reutiliza en vez de volver a
# pedirsela a Agrocalidad. Los requisitos fitosanitarios cambian pocas veces al
# ano; reconsultar lo mismo cada vez solo agrega 3 s de espera al usuario y
# carga innecesaria sobre un servicio publico del Estado.
HORAS_VIGENCIA = 24


@router.post("/consultar")
def consultar(payload: AgrocalidadConsultaRequest, refrescar: bool = False):
    """Consulta Agrocalidad y guarda el resultado.

    Si ya hay una consulta guardada de las ultimas `HORAS_VIGENCIA` horas se
    devuelve esa (respuesta en ~0,4 s en vez de ~3,7 s). Con `?refrescar=true`
    se fuerza la consulta en vivo.
    """
    if payload.area_code not in AREAS_VALIDAS:
        raise HTTPException(status_code=400,
                            detail=f"area_code invalido: {payload.area_code}")
    if payload.trade_type not in agrocalidad_api.MOVIMIENTOS:
        raise HTTPException(
            status_code=400,
            detail=f"trade_type invalido: {payload.trade_type}. "
                   f"Debe ser uno de {list(agrocalidad_api.MOVIMIENTOS)}")

    # --- mapeo + consulta vigente, en un solo viaje ---
    # Cada round-trip a Supabase cuesta ~195 ms, asi que se resuelve todo junto:
    # los ids de Agrocalidad y si ya hay un resultado reutilizable.
    with engine.connect() as conn:
        mapeo = conn.execute(text(f"""
            SELECT
                (SELECT row_to_json(e) FROM (
                    SELECT id, name, id_producto_agrocalidad
                    FROM species WHERE id = :species_id) e) AS especie,
                (SELECT row_to_json(p) FROM (
                    SELECT id, name_es, id_localizacion_agrocalidad
                    FROM countries WHERE id = :country_id) p) AS pais,
                (SELECT id FROM agrocalidad_requirements
                  WHERE species_id = :species_id AND country_id = :country_id
                    AND trade_type = :trade_type AND area_code = :area_code
                    AND active = true AND fuente = 'api'
                    AND queried_at > now() - interval '{HORAS_VIGENCIA} hours'
                ) AS vigente
        """), {"species_id": str(payload.species_id),
               "country_id": str(payload.country_id),
               "trade_type": payload.trade_type,
               "area_code": payload.area_code}).mappings().first()

    especie = mapeo["especie"]
    pais = mapeo["pais"]

    # Resultado reciente: se devuelve sin molestar a Agrocalidad.
    if mapeo["vigente"] and not refrescar:
        with engine.connect() as conn:
            fila = conn.execute(text(
                "SELECT * FROM v_agrocalidad_requisitos WHERE requirement_id = :id"
            ), {"id": str(mapeo["vigente"])}).mappings().first()
        if fila is not None:
            return {**dict(fila), "desde_cache": True}

    if especie is None:
        raise HTTPException(status_code=404, detail="Especie no encontrada")
    if pais is None:
        raise HTTPException(status_code=404, detail="País no encontrado")
    if not especie["id_producto_agrocalidad"]:
        raise HTTPException(
            status_code=422,
            detail=f"La especie {especie['name']} no está mapeada al catálogo de "
                   f"Agrocalidad. Búscala en /api/agrocalidad/productos y carga "
                   f"species.id_producto_agrocalidad.")
    if not pais["id_localizacion_agrocalidad"]:
        raise HTTPException(
            status_code=422,
            detail=f"El país {pais['name_es']} no está mapeado al catálogo de "
                   f"Agrocalidad.")

    # --- consulta en vivo ---
    try:
        resultado = agrocalidad_api.consultar(
            especie["id_producto_agrocalidad"],
            pais["id_localizacion_agrocalidad"],
            payload.trade_type,
        )
    except AgrocalidadError as e:
        raise HTTPException(status_code=502, detail=str(e))

    ficha = resultado["ficha"]
    reqs = resultado["requisitos"]

    # --- guardar ---
    with engine.begin() as conn:
        # Catalogo de requisitos: el texto se guarda una sola vez y se reutiliza.
        # En lote — fila por fila serian ~195 ms cada una (ver rules/coding-style.md).
        if reqs:
            cursor = conn.connection.cursor()
            execute_values(cursor, """
                INSERT INTO agrocalidad_requisitos
                    (id_requisito, nombre, requisito, detalle_impreso)
                VALUES %s
                ON CONFLICT (id_requisito) DO UPDATE SET
                    nombre = EXCLUDED.nombre,
                    requisito = EXCLUDED.requisito,
                    detalle_impreso = EXCLUDED.detalle_impreso,
                    visto_ultima_vez = now(),
                    updated_at = now()
            """, [(r["id_requisito"], r["nombre"], r.get("requisito"),
                   r.get("detalle_impreso")) for r in reqs])

        # Cabecera. La clave unica (especie, pais, tipo, area) hace de cache:
        # reconsultar actualiza la fila en vez de duplicarla.
        fila = conn.execute(text("""
            INSERT INTO agrocalidad_requirements (
                species_id, country_id, trade_type, area_code, status,
                matched_product_name, scientific_name, tariff_heading,
                agrocalidad_code, id_producto, tipo, id_subtipo_producto,
                subtipo, unidad_medida, id_localizacion, fuente, queried_at
            ) VALUES (
                :species_id, :country_id, :trade_type, :area_code, :status,
                :producto, :cientifico, :partida,
                :codigo, :id_producto, :tipo, :id_subtipo,
                :subtipo, :unidad, :id_localizacion, 'api', now()
            )
            ON CONFLICT (species_id, country_id, trade_type, area_code)
            DO UPDATE SET
                status = EXCLUDED.status,
                matched_product_name = EXCLUDED.matched_product_name,
                scientific_name = EXCLUDED.scientific_name,
                tariff_heading = EXCLUDED.tariff_heading,
                agrocalidad_code = EXCLUDED.agrocalidad_code,
                id_producto = EXCLUDED.id_producto,
                tipo = EXCLUDED.tipo,
                id_subtipo_producto = EXCLUDED.id_subtipo_producto,
                subtipo = EXCLUDED.subtipo,
                unidad_medida = EXCLUDED.unidad_medida,
                id_localizacion = EXCLUDED.id_localizacion,
                fuente = 'api',
                active = true,
                queried_at = now(),
                updated_at = now()
            RETURNING id
        """), {
            "species_id": str(payload.species_id),
            "country_id": str(payload.country_id),
            "trade_type": payload.trade_type,
            "area_code": payload.area_code,
            "status": resultado["status"],
            "producto": ficha.get("producto"),
            "cientifico": ficha.get("cientifico"),
            "partida": ficha.get("partida_arancelaria"),
            "codigo": agrocalidad_api.codigo_con_letra(ficha.get("codigo_producto")),
            "id_producto": ficha.get("id_producto"),
            "tipo": ficha.get("tipo"),
            "id_subtipo": ficha.get("id_subtipo_producto"),
            "subtipo": ficha.get("subtipo"),
            "unidad": ficha.get("unidad_medida"),
            "id_localizacion": pais["id_localizacion_agrocalidad"],
        }).mappings().first()

        requirement_id = fila["id"]

        # Enlaces: se reemplazan, para que una reconsulta refleje bajas de
        # requisitos y no solo altas.
        conn.execute(text(
            "DELETE FROM agrocalidad_requirement_items WHERE requirement_id = :id"
        ), {"id": str(requirement_id)})

        if reqs:
            cursor = conn.connection.cursor()
            execute_values(cursor, """
                INSERT INTO agrocalidad_requirement_items
                    (requirement_id, id_requisito, orden)
                VALUES %s
                ON CONFLICT (requirement_id, id_requisito) DO NOTHING
            """, [(str(requirement_id), r["id_requisito"], orden)
                  for orden, r in enumerate(reqs, 1)])

    with engine.connect() as conn:
        fila = conn.execute(text(
            "SELECT * FROM v_agrocalidad_requisitos WHERE requirement_id = :id"
        ), {"id": str(requirement_id)}).mappings().first()

    return {**dict(fila), "desde_cache": False}
