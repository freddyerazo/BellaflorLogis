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

from sqlalchemy import text

from app.database.connection import engine


def generar_despachos_del_dia(fecha: Optional[date_type] = None) -> dict:
    """Idempotente: se puede llamar en cada /lista del bot sin duplicar
    filas (UNIQUE en fecha+id_pedido+tipo_caja+postcosecha -- un mismo
    id_pedido puede tener lineas en mas de una poscosecha). Si un despacho
    ya existia y sigue PENDIENTE, se actualiza con los datos mas recientes
    de dartis_ventas (Dartis puede reimportarse con cantidades corregidas
    o completadas despues de la primera vez) -- si ya quedo AUDITADO no se
    toca, para no pisar un resultado de auditoria ya registrado."""
    with engine.begin() as conn:
        filtro_fecha = "dv.fecha = :fecha" if fecha else "dv.fecha = CURRENT_DATE"
        params = {"fecha": fecha} if fecha else {}

        # Cuando customers.destinatario esta poblado (varios clientes especiales
        # comparten el mismo dartis_name, ej. 7 destinatarios de TRADEWINDS INTL LLC,
        # o Montse que es destinatario de Easyflowers S.A), tambien se exige que
        # coincida con dv.destinatario -- si no, cualquiera de esos clientes
        # calzaria con cualquier venta de ese comprador sin distinguir a quien iba.
        #
        # Se agrupa por id_pedido (no por guia_madre/guia_hija): en los datos
        # recientes de Dartis las guias llegan vacias, y como NULL != NULL en el
        # UNIQUE de la tabla, agrupar por guia dejaba la deduplicacion sin efecto.
        # id_pedido si viene siempre poblado (mismo campo que usa Torre de Control).
        filas = conn.execute(text(f"""
            SELECT dv.fecha, dv.postcosecha, c.id AS customer_id, dv.cliente, dv.destinatario,
                   dv.id_pedido, MAX(dv.guia_madre) AS guia_madre, MAX(dv.guia_hija) AS guia_hija,
                   dv.tipo_caja, c.customer_name AS etiqueta, SUM(dv.total_piezas) AS cajas
            FROM dartis_ventas dv
            JOIN customers c ON LOWER(TRIM(c.dartis_name)) = LOWER(TRIM(dv.cliente))
                AND (
                    c.destinatario IS NULL OR TRIM(c.destinatario) = ''
                    OR LOWER(TRIM(c.destinatario)) = LOWER(TRIM(dv.destinatario))
                )
            WHERE c.es_cliente_especial = true AND dv.active = true AND {filtro_fecha}
            GROUP BY dv.fecha, dv.postcosecha, c.id, dv.cliente, dv.destinatario,
                     dv.id_pedido, dv.tipo_caja, c.customer_name
        """), params).mappings().all()

        insertados = 0
        actualizados = 0
        for f in filas:
            r = conn.execute(text("""
                INSERT INTO special_dispatches
                    (fecha, postcosecha, customer_id, cliente, destinatario, id_pedido, guia_madre, guia_hija,
                     cajas, tipo_caja, etiqueta)
                VALUES (:fecha, :postcosecha, :customer_id, :cliente, :destinatario, :id_pedido, :guia_madre, :guia_hija,
                        :cajas, :tipo_caja, :etiqueta)
                ON CONFLICT (fecha, id_pedido, tipo_caja, postcosecha) DO UPDATE SET
                    cajas = EXCLUDED.cajas, guia_madre = EXCLUDED.guia_madre, guia_hija = EXCLUDED.guia_hija,
                    destinatario = EXCLUDED.destinatario, etiqueta = EXCLUDED.etiqueta
                WHERE special_dispatches.estado = 'PENDIENTE'
                RETURNING (xmax = 0) AS es_insercion
            """), dict(f))
            fila = r.first()
            if fila is not None:
                if fila[0]:
                    insertados += 1
                else:
                    actualizados += 1

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
