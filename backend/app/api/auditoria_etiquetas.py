"""API del modulo Auditoria de Etiquetas Especiales: clon de
Auditoria_LEsp. La carga de datos ocurre via el bot de Telegram (igual
que el original); este router expone el webhook y un dashboard de
solo lectura para supervision.
"""

import logging
import os
from datetime import date as date_type
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy import text

from app.database.connection import engine
from app.services import special_dispatches
from app.services import telegram_bot

router = APIRouter(prefix="/auditoria-etiquetas", tags=["Auditoria de Etiquetas"])
logger = logging.getLogger(__name__)


@router.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(default=None),
):
    secreto = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    if secreto and x_telegram_bot_api_secret_token != secreto:
        raise HTTPException(status_code=401, detail="secret_token invalido")

    update = await request.json()
    try:
        await telegram_bot.procesar_update(update)
    except Exception:
        # Telegram reintenta si no responde 200; nunca dejar que un error rompa el webhook,
        # pero sí queda logueado para poder diagnosticar fallas del bot en produccion.
        logger.exception("Error procesando update de Telegram: %s", update)
    return {"ok": True}


@router.post("/despachos/generar")
def generar_despachos(fecha: Optional[date_type] = None):
    return special_dispatches.generar_despachos_del_dia(fecha)


@router.get("/despachos")
def listar_despachos(desde: Optional[date_type] = None, hasta: Optional[date_type] = None):
    # El rango es de solo lectura para consulta -- ver fechas pasadas es valido
    # (historial), lo unico restringido a "hoy en adelante" es la accion de
    # generar despachos (endpoint /despachos/generar, que siempre usa hoy).
    desde = desde or date_type.today()
    hasta = max(hasta, desde) if hasta else desde
    with engine.connect() as conn:
        rows = conn.execute(text("""
            -- La especie no vive en special_dispatches: se cruza contra
            -- dartis_ventas por id_pedido, usando id_pedidos (jsonb, despachos
            -- consolidados desde 2026-09-14) o cayendo al id_pedido singular
            -- de las filas AUDITADO viejas que no se tocaron en esa migracion.
            -- Hecho como CTE + JOIN en bloque (no una subconsulta LATERAL por
            -- fila, que con un rango de meses tardaba 11s para ~2800 despachos
            -- contra 1.5s de esta version -- medido, no solo intuido).
            WITH pedidos AS (
                SELECT sd.id AS dispatch_id, pedido.pedido_id
                FROM special_dispatches sd
                CROSS JOIN LATERAL (
                    SELECT (jsonb_array_elements_text(sd.id_pedidos))::int AS pedido_id
                    WHERE sd.id_pedidos IS NOT NULL AND jsonb_array_length(sd.id_pedidos) > 0
                    UNION ALL
                    SELECT sd.id_pedido
                    WHERE sd.id_pedidos IS NULL OR jsonb_array_length(sd.id_pedidos) = 0
                ) pedido
                WHERE sd.fecha BETWEEN :desde AND :hasta AND sd.estado != 'OBSOLETO'
            ),
            especies AS (
                SELECT p.dispatch_id, string_agg(DISTINCT dv.especie, ', ' ORDER BY dv.especie) AS especies
                FROM pedidos p
                JOIN dartis_ventas dv ON dv.id_pedido = p.pedido_id
                GROUP BY p.dispatch_id
            )
            SELECT sd.*, COALESCE(e.especies, '') AS especies
            FROM special_dispatches sd
            LEFT JOIN especies e ON e.dispatch_id = sd.id
            WHERE sd.fecha BETWEEN :desde AND :hasta AND sd.estado != 'OBSOLETO'
            ORDER BY sd.fecha, sd.postcosecha, sd.cliente
        """), {"desde": desde, "hasta": hasta}).mappings().all()
    return rows


@router.get("/auditorias")
def listar_auditorias(desde: Optional[date_type] = None, hasta: Optional[date_type] = None):
    desde = desde or date_type.today()
    hasta = max(hasta, desde) if hasta else desde
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT a.*, d.cliente, d.postcosecha, d.guia_madre, d.guia_hija, d.tipo_caja
            FROM special_dispatch_audits a
            JOIN special_dispatches d ON d.id = a.dispatch_id
            WHERE d.fecha BETWEEN :desde AND :hasta ORDER BY a.fecha_hora DESC
        """), {"desde": desde, "hasta": hasta}).mappings().all()
    return rows
