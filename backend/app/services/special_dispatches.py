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
    filas (UNIQUE en fecha+guia_madre+guia_hija+tipo_caja) ni pisar
    despachos que ya estan en curso o auditados."""
    with engine.begin() as conn:
        filtro_fecha = "dv.fecha = :fecha" if fecha else "dv.fecha = CURRENT_DATE"
        params = {"fecha": fecha} if fecha else {}

        filas = conn.execute(text(f"""
            SELECT dv.fecha, dv.postcosecha, c.id AS customer_id, dv.cliente, dv.destinatario,
                   dv.guia_madre, dv.guia_hija, dv.tipo_caja, c.customer_name AS etiqueta,
                   SUM(dv.total_piezas) AS cajas
            FROM dartis_ventas dv
            JOIN customers c ON LOWER(TRIM(c.dartis_name)) = LOWER(TRIM(dv.cliente))
            WHERE c.es_cliente_especial = true AND {filtro_fecha}
            GROUP BY dv.fecha, dv.postcosecha, c.id, dv.cliente, dv.destinatario,
                     dv.guia_madre, dv.guia_hija, dv.tipo_caja, c.customer_name
        """), params).mappings().all()

        insertados = 0
        for f in filas:
            r = conn.execute(text("""
                INSERT INTO special_dispatches
                    (fecha, postcosecha, customer_id, cliente, destinatario, guia_madre, guia_hija,
                     cajas, tipo_caja, etiqueta)
                VALUES (:fecha, :postcosecha, :customer_id, :cliente, :destinatario, :guia_madre, :guia_hija,
                        :cajas, :tipo_caja, :etiqueta)
                ON CONFLICT (fecha, guia_madre, guia_hija, tipo_caja) DO NOTHING
            """), dict(f))
            insertados += r.rowcount

    return {"encontrados": len(filas), "insertados": insertados}


def despachos_pendientes(poscosecha: Optional[str] = None) -> list[dict]:
    with engine.connect() as conn:
        filtro = "AND postcosecha = :pos" if poscosecha else ""
        params = {"pos": poscosecha} if poscosecha else {}
        rows = conn.execute(text(f"""
            SELECT * FROM special_dispatches
            WHERE estado = 'PENDIENTE' AND fecha >= CURRENT_DATE {filtro}
            ORDER BY postcosecha, cliente
        """), params).mappings().all()
    return [dict(r) for r in rows]


def poscosechas_pendientes() -> list[str]:
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT DISTINCT postcosecha FROM special_dispatches
            WHERE estado = 'PENDIENTE' AND fecha >= CURRENT_DATE
            ORDER BY postcosecha
        """)).all()
    return [r[0] for r in rows if r[0]]
