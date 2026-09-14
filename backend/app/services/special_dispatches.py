"""Genera los "despachos" a auditar (clientes especiales) directo desde
dartis_ventas — reemplaza el paso manual de "descargar Excel de ventas y
subirlo a la pagina" del proyecto original Auditoria_LEsp.

Un despacho = un HAWB (guia_hija) de un cliente especial, sin importar
cuantos id_pedido o tipos de caja de Dartis lo componen (pedido del
usuario, 2026-09-14): antes se generaba un despacho por
id_pedido+tipo_caja+guia_hija, y un mismo cliente+HAWB con varios pedidos
(hasta 20 en los datos reales) obligaba al auditor a repetir el
cuestionario completo una vez por pedido para revisar UN SOLO paquete
fisico. `id_pedidos` (JSONB) guarda todos los pedidos consolidados para
trazabilidad, y `desglose_tipo_caja` (JSONB, {tipo_caja: cajas}) porque
dentro de un mismo HAWB el tipo de caja SI varia (verificado contra datos
reales: HAWB con HB+QB+SB mezclados).
"""

from collections import defaultdict
from datetime import date as date_type
from typing import Optional

from psycopg2.extras import execute_values, Json
from sqlalchemy import text

from app.database.connection import engine


def generar_despachos_del_dia(fecha: Optional[date_type] = None) -> dict:
    """Idempotente: se puede llamar en cada /lista del bot sin duplicar
    filas (indice unico en fecha+postcosecha+customer_id+destinatario+
    guia_hija). Si un despacho ya existia y sigue PENDIENTE, se actualiza
    con los datos mas recientes de dartis_ventas (Dartis puede
    reimportarse con cantidades corregidas o completadas despues de la
    primera vez) -- si ya quedo AUDITADO no se toca, para no pisar un
    resultado de auditoria ya registrado."""
    with engine.begin() as conn:
        filtro_fecha = "dv.fecha = :fecha" if fecha else "dv.fecha = CURRENT_DATE"
        params = {"fecha": fecha} if fecha else {}

        # Cuando customers.destinatario esta poblado (varios clientes especiales
        # comparten el mismo dartis_name, ej. 7 destinatarios de TRADEWINDS INTL LLC,
        # o Montse que es destinatario de Easyflowers S.A), tambien se exige que
        # coincida con dv.destinatario -- si no, cualquiera de esos clientes
        # calzaria con cualquier venta de ese comprador sin distinguir a quien iba.
        # Un mismo dv puede calzar con el cliente "padre" (destinatario NULL,
        # matchea cualquier venta de ese comprador) Y con un destinatario
        # especifico a la vez -- ROW_NUMBER se queda solo con el mas especifico
        # por fila de venta, para no contar la misma linea dos veces bajo dos
        # clientes distintos.
        #
        # La agrupacion final (fecha+postcosecha+customer_id+destinatario+
        # guia_hija) se hace en Python, no en SQL: hace falta un
        # jsonb_object_agg de piezas POR tipo_caja (que requiere sumar antes
        # de agregar, dos niveles de GROUP BY) ademas de un array de
        # id_pedido distintos -- mas simple y legible construirlo aqui que
        # en un solo SELECT con subconsultas correlacionadas.
        lineas = conn.execute(text(f"""
            WITH match_unico AS (
                SELECT dv.*, c.id AS matched_customer_id, c.customer_name,
                       ROW_NUMBER() OVER (
                           PARTITION BY dv.id
                           ORDER BY (c.destinatario IS NOT NULL AND TRIM(c.destinatario) != '') DESC
                       ) AS rn
                FROM dartis_ventas dv
                JOIN customers c ON LOWER(TRIM(c.dartis_name)) = LOWER(TRIM(dv.cliente))
                    AND (
                        c.destinatario IS NULL OR TRIM(c.destinatario) = ''
                        OR LOWER(TRIM(c.destinatario)) = LOWER(TRIM(dv.destinatario))
                    )
                WHERE c.es_cliente_especial = true AND dv.active = true AND {filtro_fecha}
            )
            SELECT fecha, postcosecha, matched_customer_id AS customer_id, cliente, destinatario,
                   guia_hija, guia_madre, customer_name, id_pedido, tipo_caja, total_piezas
            FROM match_unico
            WHERE rn = 1
        """), params).mappings().all()

        grupos: dict[tuple, dict] = {}
        for f in lineas:
            # dv.destinatario NO entra en la clave -- es el destinatario final de
            # CADA linea de venta, y en clientes que son distribuidores (ej. LA
            # HACIENDA FLOWERS INC) varia de linea a linea dentro de un mismo HAWB
            # (once floristerias finales distintas bajo el mismo despacho fisico).
            # La identidad del cliente especial ya la resuelve customer_id (via
            # customers.destinatario en el JOIN de match_unico). Ver migracion 043.
            clave = (f["fecha"], f["postcosecha"], f["customer_id"], f["guia_hija"])
            g = grupos.get(clave)
            if g is None:
                g = grupos[clave] = {
                    "fecha": f["fecha"], "postcosecha": f["postcosecha"], "customer_id": f["customer_id"],
                    "cliente": f["cliente"], "guia_hija": f["guia_hija"],
                    "guia_madre": f["guia_madre"], "etiqueta": f["customer_name"],
                    "cajas": 0.0, "id_pedidos": set(), "desglose_tipo_caja": defaultdict(float),
                    "destinatarios": set(),
                }
            piezas = float(f["total_piezas"] or 0)
            g["cajas"] += piezas
            g["id_pedidos"].add(f["id_pedido"])
            g["desglose_tipo_caja"][f["tipo_caja"] or "SIN_TIPO"] += piezas
            if f["destinatario"]:
                g["destinatarios"].add(f["destinatario"])
            if not g["guia_madre"] and f["guia_madre"]:
                g["guia_madre"] = f["guia_madre"]

        for g in grupos.values():
            distintos = sorted(g.pop("destinatarios"))
            if len(distintos) == 1:
                g["destinatario"] = distintos[0]
            elif len(distintos) > 1:
                g["destinatario"] = f"{len(distintos)} destinatarios distintos"
            else:
                g["destinatario"] = None

        # Insercion masiva via execute_values (mismo patron que dartis_import.py
        # y courier_reconciliation.py): con decenas de despachos, hacer un
        # INSERT por fila tardaba ~200ms/round-trip a Supabase cada uno -- en
        # /lista eso se traducia en 10-15s de espera para el auditor en cada
        # comando. En un solo lote es menos de 1s.
        tuples = [
            (g["fecha"], g["postcosecha"], g["customer_id"], g["cliente"], g["destinatario"],
             g["guia_madre"], g["guia_hija"], g["cajas"], g["etiqueta"],
             Json(sorted(p for p in g["id_pedidos"] if p is not None)),
             Json(dict(g["desglose_tipo_caja"])))
            for g in grupos.values()
        ]
        insertados = actualizados = 0
        if tuples:
            raw = conn.connection.cursor()
            resultados = execute_values(raw, """
                INSERT INTO special_dispatches
                    (fecha, postcosecha, customer_id, cliente, destinatario, guia_madre, guia_hija,
                     cajas, etiqueta, id_pedidos, desglose_tipo_caja)
                VALUES %s
                ON CONFLICT (fecha, postcosecha, customer_id, (COALESCE(guia_hija, '')))
                WHERE (estado = 'PENDIENTE')
                DO UPDATE SET
                    cajas = EXCLUDED.cajas, guia_madre = EXCLUDED.guia_madre,
                    destinatario = EXCLUDED.destinatario, etiqueta = EXCLUDED.etiqueta,
                    id_pedidos = EXCLUDED.id_pedidos, desglose_tipo_caja = EXCLUDED.desglose_tipo_caja
                RETURNING (xmax = 0) AS es_insercion
            """, tuples, page_size=1000, fetch=True)
            insertados = sum(1 for r in resultados if r[0])
            actualizados = sum(1 for r in resultados if not r[0])

    return {"encontrados": len(grupos), "insertados": insertados, "actualizados": actualizados}


def despachos_pendientes(poscosecha: Optional[str] = None) -> list[dict]:
    """Solo del dia de hoy: el bot no muestra la fecha en el mensaje de cada
    despacho, asi que mezclar dias distintos en la misma lista numerada podia
    llevar al auditor a auditar algo que todavia no ha salido fisicamente."""
    with engine.connect() as conn:
        filtro = "AND postcosecha = :pos" if poscosecha else ""
        params = {"pos": poscosecha} if poscosecha else {}
        rows = conn.execute(text(f"""
            SELECT * FROM special_dispatches
            WHERE estado = 'PENDIENTE' AND fecha = CURRENT_DATE {filtro}
            ORDER BY postcosecha, cliente
        """), params).mappings().all()
    return [dict(r) for r in rows]


def poscosechas_pendientes() -> list[str]:
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT DISTINCT postcosecha FROM special_dispatches
            WHERE estado = 'PENDIENTE' AND fecha = CURRENT_DATE
            ORDER BY postcosecha
        """)).all()
    return [r[0] for r in rows if r[0]]
