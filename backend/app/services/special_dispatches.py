"""Genera los "despachos" a auditar (clientes especiales) directo desde
dartis_ventas — reemplaza el paso manual de "descargar Excel de ventas y
subirlo a la pagina" del proyecto original Auditoria_LEsp.

Verificado en la sesion de planificacion: los archivos "Ventas Auditoria
Etiquetas...xlsx" que se subian a mano tienen exactamente las columnas
empresa/cliente/destinatario/fecha/guia_madre/guia_hija/postcosecha/
tipo_caja/total, y coinciden fila por fila con dartis_ventas agrupada por
guia_madre+guia_hija+tipo_caja (total = SUM(total_piezas)).
"""

from datetime import date as date_type
from typing import Optional

from psycopg2.extras import execute_values
from sqlalchemy import text

from app.database.connection import engine


def generar_despachos_del_dia(fecha: Optional[date_type] = None) -> dict:
    """Idempotente: se puede llamar en cada /lista del bot sin duplicar
    filas (indice unico en fecha+id_pedido+tipo_caja+postcosecha+guia_hija
    -- un mismo id_pedido puede tener lineas en mas de una poscosecha, y
    dentro de una poscosecha repartirse en mas de una guia hija, cada una
    su propio despacho fisico). Si un despacho ya existia y sigue
    PENDIENTE, se actualiza con los datos mas recientes de dartis_ventas
    (Dartis puede reimportarse con cantidades corregidas o completadas
    despues de la primera vez) -- si ya quedo AUDITADO no se toca, para no
    pisar un resultado de auditoria ya registrado."""
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
        # por fila de venta, para no generar la misma clave de despacho dos
        # veces bajo dos clientes distintos (eso rompia el insert masivo de
        # abajo con "ON CONFLICT DO UPDATE command cannot affect row a second
        # time", y en el insert fila por fila anterior quedaba en silencio con
        # el ultimo que ganara la carrera).
        #
        # Se agrupa por id_pedido (no por guia_madre): en los datos recientes de
        # Dartis las guias llegan vacias, y como NULL != NULL en un UNIQUE comun,
        # agrupar por guia dejaba la deduplicacion sin efecto. id_pedido si viene
        # siempre poblado (mismo campo que usa Torre de Control). guia_hija SI se
        # incluye en el agrupamiento (piezas unidas por destinatario, separadas
        # por guia hija): un mismo pedido puede repartirse en varios paquetes
        # fisicos distintos, cada uno su propio despacho para el auditor. Las
        # lineas sin guia hija (NULL) se agrupan entre si como un solo despacho,
        # via el comportamiento nativo de GROUP BY (a diferencia de un UNIQUE,
        # aqui SI junta todos los NULL en un mismo grupo).
        filas = conn.execute(text(f"""
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
                   id_pedido, MAX(guia_madre) AS guia_madre, guia_hija,
                   tipo_caja, MAX(customer_name) AS etiqueta, SUM(total_piezas) AS cajas
            FROM match_unico
            WHERE rn = 1
            GROUP BY fecha, postcosecha, matched_customer_id, cliente, destinatario,
                     id_pedido, tipo_caja, guia_hija
        """), params).mappings().all()

        # Insercion masiva via execute_values (mismo patron que dartis_import.py
        # y courier_reconciliation.py): con decenas de despachos, hacer un
        # INSERT por fila tardaba ~200ms/round-trip a Supabase cada uno -- en
        # /lista eso se traducia en 10-15s de espera para el auditor en cada
        # comando. En un solo lote es menos de 1s.
        tuples = [
            (f["fecha"], f["postcosecha"], f["customer_id"], f["cliente"], f["destinatario"],
             f["id_pedido"], f["guia_madre"], f["guia_hija"], f["cajas"], f["tipo_caja"], f["etiqueta"])
            for f in filas
        ]
        insertados = actualizados = 0
        if tuples:
            raw = conn.connection.cursor()
            resultados = execute_values(raw, """
                INSERT INTO special_dispatches
                    (fecha, postcosecha, customer_id, cliente, destinatario, id_pedido, guia_madre, guia_hija,
                     cajas, tipo_caja, etiqueta)
                VALUES %s
                ON CONFLICT (fecha, id_pedido, tipo_caja, postcosecha, (COALESCE(guia_hija, ''))) DO UPDATE SET
                    cajas = EXCLUDED.cajas, guia_madre = EXCLUDED.guia_madre, guia_hija = EXCLUDED.guia_hija,
                    destinatario = EXCLUDED.destinatario, etiqueta = EXCLUDED.etiqueta
                WHERE special_dispatches.estado = 'PENDIENTE'
                RETURNING (xmax = 0) AS es_insercion
            """, tuples, page_size=1000, fetch=True)
            insertados = sum(1 for r in resultados if r[0])
            actualizados = sum(1 for r in resultados if not r[0])

    return {"encontrados": len(filas), "insertados": insertados, "actualizados": actualizados}


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
