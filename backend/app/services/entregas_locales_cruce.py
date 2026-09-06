"""Cruce: cada pedido de Dartis contra su recibo de bodega.

Confirmado con el usuario (2026-09-06): TODO pedido pasa primero por una
bodega local antes de salir, sea cual sea el courier final -- incluidos UPS y
FedEx. Por eso el universo del cruce es `dartis_ventas` completo, sin filtrar
por agencia, y no existe un estado "no aplica".

Estados:
  OK          hay exactamente un recibo que calza
  AMBIGUO     hay mas de un recibo candidato, no se puede elegir solo
  SIN RECIBO  no hay ninguno -- el dato util: falta fotografiar ese recibo

Criterio de match (los tres a la vez):
  1. AGENCIA: la `agencia_carga` de Dartis resuelta contra cargo_agencies,
     aceptando ademas sus equivalencias declaradas (SAFTEC <-> UPS: la bodega
     que recibe para UPS emite el recibo a nombre de SAFTEC, ver migracion 038).
  2. FINCA: la `empresa` de Dartis resuelta contra farms, comparada contra la
     finca de CADA linea del recibo (entregas_locales_detalle), no contra la
     cabecera -- un mismo recibo puede traer tres fincas distintas.
  3. FECHA: dentro de +/- VENTANA_DIAS de la fecha del pedido. No se exige
     coincidencia exacta como en Torre de Control: ahi el objetivo era no dar
     falsos OK, aca es cubrir el 100% de los pedidos, y un recibo se
     fotografia el mismo dia o al siguiente segun a que hora salio el camion.
"""

import logging

from sqlalchemy import text

from app.database.connection import engine

logger = logging.getLogger(__name__)

VENTANA_DIAS = 2

# Un solo SQL para todo el universo en vez de un round-trip por pedido: son
# ~11.000 pedidos y cada ida y vuelta a Supabase cuesta ~195 ms (ver
# rules/coding-style.md). Asi el cruce completo es una sola consulta.
SQL_CRUCE = """
WITH pedidos AS (
    SELECT id_pedido,
           MAX(fecha)         AS fecha,
           MAX(empresa)       AS empresa,
           MAX(agencia_carga) AS agencia_carga
    FROM dartis_ventas
    WHERE active AND agencia_carga IS NOT NULL
    GROUP BY id_pedido
),
pedidos_res AS (
    SELECT p.*,
           (SELECT ca.id FROM cargo_agencies ca
             WHERE upper(ca.dartis_name) = upper(p.agencia_carga)
                OR upper(ca.name)        = upper(p.agencia_carga)
             LIMIT 1) AS agencia_id,
           (SELECT f.id FROM farms f
             WHERE upper(f.name) = upper(p.empresa)
                OR upper(p.empresa) = ANY (SELECT upper(v) FROM unnest(f.ocr_variants) v)
             LIMIT 1) AS finca_id
    FROM pedidos p
),
-- Agencias aceptables por pedido: la propia mas sus equivalentes en
-- cualquiera de las dos direcciones (SAFTEC vale por UPS y viceversa).
agencias_ok AS (
    SELECT pr.id_pedido, pr.agencia_id AS acepta
      FROM pedidos_res pr WHERE pr.agencia_id IS NOT NULL
    UNION
    SELECT pr.id_pedido, e.agencia_id
      FROM pedidos_res pr
      JOIN cargo_agencies_equivalencias e ON e.equivale_a_id = pr.agencia_id
    UNION
    SELECT pr.id_pedido, e.equivale_a_id
      FROM pedidos_res pr
      JOIN cargo_agencies_equivalencias e ON e.agencia_id = pr.agencia_id
),
candidatos AS (
    SELECT DISTINCT pr.id_pedido, el.id AS entrega_id
    FROM pedidos_res pr
    JOIN entregas_locales el
      ON el.fecha_documento BETWEEN pr.fecha - make_interval(days => :ventana)
                               AND pr.fecha + make_interval(days => :ventana)
     AND el.agencia_id IN (SELECT a.acepta FROM agencias_ok a WHERE a.id_pedido = pr.id_pedido)
    JOIN entregas_locales_detalle d
      ON d.entrega_id = el.id
     AND d.finca_id   = pr.finca_id
    WHERE pr.finca_id IS NOT NULL
),
resumen AS (
    SELECT pr.id_pedido,
           count(c.entrega_id)                                   AS n,
           min(c.entrega_id)                                     AS entrega_id,
           array_remove(array_agg(c.entrega_id), NULL)           AS ids
    FROM pedidos_res pr
    LEFT JOIN candidatos c ON c.id_pedido = pr.id_pedido
    GROUP BY pr.id_pedido
)
SELECT id_pedido,
       CASE WHEN n = 0 THEN 'SIN RECIBO'
            WHEN n = 1 THEN 'OK'
            ELSE 'AMBIGUO' END              AS estado,
       CASE WHEN n = 1 THEN entrega_id END  AS entrega_id,
       CASE WHEN n > 1 THEN to_jsonb(ids) END AS candidatos,
       CASE WHEN n >= 1 THEN 'agencia + finca + fecha +/- ' || :ventana || 'd' END AS criterio
FROM resumen
"""


def recalcular() -> dict:
    """Recalcula el cruce completo y lo escribe en `dartis_entregas_cruce`.

    Se conserva `verificado_manual`: si alguien reviso y confirmo una fila a
    mano, un recalculo no puede borrar ese trabajo. Por eso es UPSERT y no
    TRUNCATE + INSERT como hace Torre de Control -- alli el snapshot es
    puramente derivado, aca hay intervencion humana encima.
    """
    with engine.begin() as conn:
        filas = conn.execute(text(SQL_CRUCE), {"ventana": VENTANA_DIAS}).mappings().all()
        if not filas:
            return {"pedidos": 0, "ok": 0, "ambiguo": 0, "sin_recibo": 0}

        conn.execute(text("""
            INSERT INTO dartis_entregas_cruce
                (id_pedido, entrega_id, estado, candidatos, criterio, actualizado_at)
            SELECT (x->>'id_pedido')::int, (x->>'entrega_id')::bigint,
                   x->>'estado', (x->'candidatos'), x->>'criterio', now()
            FROM jsonb_array_elements(cast(:datos as jsonb)) AS x
            ON CONFLICT (id_pedido) DO UPDATE SET
                entrega_id     = EXCLUDED.entrega_id,
                estado         = EXCLUDED.estado,
                candidatos     = EXCLUDED.candidatos,
                criterio       = EXCLUDED.criterio,
                actualizado_at = now()
        """), {"datos": _json(filas)})

        conteo = conn.execute(text("""
            SELECT estado, count(*) n FROM dartis_entregas_cruce GROUP BY estado
        """)).mappings().all()

    por_estado = {c["estado"]: c["n"] for c in conteo}
    return {
        "pedidos": sum(por_estado.values()),
        "ok": por_estado.get("OK", 0),
        "ambiguo": por_estado.get("AMBIGUO", 0),
        "sin_recibo": por_estado.get("SIN RECIBO", 0),
        "ventana_dias": VENTANA_DIAS,
    }


def _json(filas) -> str:
    import json

    return json.dumps([
        {
            "id_pedido": f["id_pedido"],
            "entrega_id": f["entrega_id"],
            "estado": f["estado"],
            "candidatos": f["candidatos"],
            "criterio": f["criterio"],
        }
        for f in filas
    ])


def obtener_cruce(estado: str | None = None, texto: str | None = None,
                  desde: str | None = None, hasta: str | None = None,
                  limite: int = 500) -> list[dict]:
    """Filas del cruce para la pantalla.

    Los datos del pedido (fecha, empresa, agencia) se traen con JOIN a
    dartis_ventas en vez de guardarse copiados en dartis_entregas_cruce: si
    Dartis se reimporta y corrige algo, la pantalla lo refleja sin recalcular
    el cruce (decision del 2026-09-06, migracion 041).

    El universo lo manda dartis_ventas, no la tabla de cruce: asi cada pedido
    aparece SIEMPRE, incluso los que todavia no se procesaron -- que es
    justamente el requisito de cobertura del 100%.
    """
    condiciones = []
    params: dict = {"limite": limite}

    if estado == "SIN PROCESAR":
        condiciones.append("c.id IS NULL")
    elif estado:
        condiciones.append("c.estado = :estado")
        params["estado"] = estado
    if desde:
        condiciones.append("v.fecha >= :desde")
        params["desde"] = desde
    if hasta:
        condiciones.append("v.fecha <= :hasta")
        params["hasta"] = hasta
    if texto:
        condiciones.append("(v.id_pedido::text ILIKE :texto OR v.empresa ILIKE :texto "
                           "OR v.agencia_carga ILIKE :texto OR e.numero_ingreso ILIKE :texto)")
        params["texto"] = f"%{texto}%"

    where = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""

    with engine.connect() as conn:
        return [dict(f) for f in conn.execute(text(f"""
            WITH v AS (
                SELECT id_pedido,
                       MAX(fecha)          AS fecha,
                       MAX(empresa)        AS empresa,
                       MAX(agencia_carga)  AS agencia_carga,
                       round(SUM(total_piezas)) AS cajas
                FROM dartis_ventas
                WHERE active AND agencia_carga IS NOT NULL
                GROUP BY id_pedido
            )
            SELECT v.id_pedido, v.fecha, v.empresa, v.agencia_carga, v.cajas,
                   COALESCE(c.estado, 'SIN PROCESAR') AS estado,
                   c.criterio, c.verificado_manual, c.candidatos,
                   e.id            AS entrega_id,
                   e.numero_ingreso,
                   e.fecha_documento,
                   e.agencia_raw,
                   e.foto_url
            FROM v
            LEFT JOIN dartis_entregas_cruce c ON c.id_pedido = v.id_pedido
            LEFT JOIN entregas_locales e      ON e.id = c.entrega_id
            {where}
            ORDER BY v.fecha DESC NULLS LAST, v.id_pedido DESC
            LIMIT :limite
        """), params).mappings().all()]


def resumen() -> dict:
    """Contadores para las tarjetas de la pantalla."""
    with engine.connect() as conn:
        universo = conn.execute(text("""
            SELECT count(DISTINCT id_pedido) FROM dartis_ventas
            WHERE active AND agencia_carga IS NOT NULL
        """)).scalar()
        por_estado = {f["estado"]: f["n"] for f in conn.execute(text("""
            SELECT estado, count(*) n FROM dartis_entregas_cruce GROUP BY estado
        """)).mappings()}
        recibos = conn.execute(text("SELECT count(*) FROM entregas_locales")).scalar()
        crudos = conn.execute(text("SELECT count(*) FROM entregas_locales_raw")).scalar()
        sin_interpretar = conn.execute(text("""
            SELECT count(*) FROM entregas_locales_raw r
            LEFT JOIN entregas_locales e ON e.raw_id = r.id
            WHERE e.id IS NULL AND r.texto_ocr IS NOT NULL AND length(r.texto_ocr) > 30
        """)).scalar()

    procesados = sum(por_estado.values())
    return {
        "pedidos_dartis": universo,
        "ok": por_estado.get("OK", 0),
        "ambiguo": por_estado.get("AMBIGUO", 0),
        "sin_recibo": por_estado.get("SIN RECIBO", 0),
        "sin_procesar": max(universo - procesados, 0),
        "recibos_interpretados": recibos,
        "recibos_crudos": crudos,
        "recibos_sin_interpretar": sin_interpretar,
    }
