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
def listar_despachos(fecha: Optional[date_type] = None):
    with engine.connect() as conn:
        if fecha:
            rows = conn.execute(text(
                "SELECT * FROM special_dispatches WHERE fecha = :f ORDER BY postcosecha, cliente"
            ), {"f": fecha}).mappings().all()
        else:
            rows = conn.execute(text(
                "SELECT * FROM special_dispatches WHERE fecha = CURRENT_DATE ORDER BY postcosecha, cliente"
            )).mappings().all()
    return rows


@router.get("/auditorias")
def listar_auditorias(fecha: Optional[date_type] = None):
    with engine.connect() as conn:
        if fecha:
            rows = conn.execute(text("""
                SELECT a.*, d.cliente, d.postcosecha, d.guia_madre, d.guia_hija, d.tipo_caja
                FROM special_dispatch_audits a
                JOIN special_dispatches d ON d.id = a.dispatch_id
                WHERE d.fecha = :f ORDER BY a.fecha_hora DESC
            """), {"f": fecha}).mappings().all()
        else:
            rows = conn.execute(text("""
                SELECT a.*, d.cliente, d.postcosecha, d.guia_madre, d.guia_hija, d.tipo_caja
                FROM special_dispatch_audits a
                JOIN special_dispatches d ON d.id = a.dispatch_id
                WHERE d.fecha = CURRENT_DATE ORDER BY a.fecha_hora DESC
            """)).mappings().all()
    return rows
