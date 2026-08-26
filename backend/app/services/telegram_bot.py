"""Bot de Telegram para el auditor de poscosecha — port del state machine
de Code.gs (Auditoria_LEsp), simplificado: /lista -> elegir poscosecha (si
hay mas de una) -> elegir despacho -> resumen unico del despacho con
botones Confirmado/No confirmado -> observaciones -> una o mas fotos
(/listo para terminar) -> se guarda en special_dispatch_audits y se marca
el despacho AUDITADO. El nombre del auditor ya no se pregunta, se toma
del perfil de Telegram de quien confirma.

El estado de la conversacion vive en telegram_conversation_state
(Postgres) en vez de CacheService de Apps Script, para sobrevivir un
redeploy de Render a media auditoria.
"""

import json
import os
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import text

from app.database.connection import engine
from app.services import google_drive, special_dispatches

UTC = timezone.utc
ECUADOR = timezone(timedelta(hours=-5))  # sin horario de verano, offset fijo todo el ano


def _token() -> str:
    return os.getenv("TELEGRAM_BOT_TOKEN", "")


def _api_url(metodo: str) -> str:
    return f"https://api.telegram.org/bot{_token()}/{metodo}"


async def _enviar(chat_id: str, texto: str) -> None:
    async with httpx.AsyncClient(timeout=15) as client:
        await client.post(_api_url("sendMessage"), json={
            "chat_id": chat_id, "text": texto, "parse_mode": "HTML",
            "reply_markup": {"remove_keyboard": True},
        })


async def _enviar_botones(chat_id: str, texto: str, filas: list) -> None:
    """filas: lista de filas, cada fila lista de {"texto":..., "datos":...}"""
    teclado = [[{"text": b["texto"], "callback_data": b["datos"]} for b in fila] for fila in filas]
    async with httpx.AsyncClient(timeout=15) as client:
        await client.post(_api_url("sendMessage"), json={
            "chat_id": chat_id, "text": texto, "parse_mode": "HTML",
            "reply_markup": {"inline_keyboard": teclado},
        })


async def _responder_callback(callback_id: str) -> None:
    async with httpx.AsyncClient(timeout=15) as client:
        await client.post(_api_url("answerCallbackQuery"), json={"callback_query_id": callback_id})


# ---------- Estado de conversacion (Postgres) ----------

def _obtener_estado(chat_id: str) -> dict:
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT paso, estado FROM telegram_conversation_state WHERE chat_id = :c"
        ), {"c": chat_id}).mappings().first()
    if not row:
        return {"paso": None}
    data = dict(row["estado"] or {})
    data["paso"] = row["paso"]
    return data


def _guardar_estado(chat_id: str, estado: dict) -> None:
    paso = estado.get("paso")
    resto = {k: v for k, v in estado.items() if k != "paso"}
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO telegram_conversation_state (chat_id, paso, estado, updated_at)
            VALUES (:chat_id, :paso, :estado, now())
            ON CONFLICT (chat_id) DO UPDATE SET paso = :paso, estado = :estado, updated_at = now()
        """), {"chat_id": chat_id, "paso": paso, "estado": json.dumps(resto, default=str)})


def _borrar_estado(chat_id: str) -> None:
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM telegram_conversation_state WHERE chat_id = :c"), {"c": chat_id})


# ---------- Flujo principal ----------

async def procesar_update(update: dict) -> None:
    if "callback_query" in update:
        await _manejar_callback(update["callback_query"])
        return
    msg = update.get("message")
    if not msg:
        return
    chat_id = str(msg["chat"]["id"])
    texto = (msg.get("text") or "").strip()
    estado = _obtener_estado(chat_id)

    if texto in ("/start", "/lista"):
        await _enviar_lista_pendientes(chat_id)
        return
    if texto == "/cancelar":
        _borrar_estado(chat_id)
        await _enviar(chat_id, "❌ Auditoria cancelada. Escribe /lista para empezar de nuevo.")
        return
    if texto == "/resumen":
        await _enviar_resumen(chat_id)
        return

    paso = estado.get("paso")

    if paso == "eligiendo_poscosecha":
        poscosechas = estado.get("poscosechas", [])
        elegida = next((p for p in poscosechas if p.upper() == texto.upper()), None)
        if not elegida:
            await _enviar(chat_id, "⚠️ Elige una de las poscosechas del teclado, o /cancelar.")
            return
        await _mostrar_lista_por_poscosecha(chat_id, elegida)
        return

    if paso == "eligiendo":
        pendientes = estado.get("pendientes", [])
        try:
            n = int(texto)
        except ValueError:
            n = None
        if not n or n < 1 or n > len(pendientes):
            await _enviar(chat_id, f"⚠️ Responde con el numero del despacho (1-{len(pendientes)}) o /cancelar.")
            return
        despacho = pendientes[n - 1]
        estado = {"paso": "confirmando", "despacho": despacho}
        _guardar_estado(chat_id, estado)
        await _enviar_botones(chat_id, _texto_resumen(despacho), [[
            {"texto": "✅ Confirmado", "datos": "CONFIRMADO"},
            {"texto": "❌ No confirmado", "datos": "NO_CONFIRMADO"},
        ]])
        return

    if paso == "observaciones":
        estado["observaciones"] = "" if texto == "-" else texto
        estado["paso"] = "foto"
        estado["fotos"] = []
        _guardar_estado(chat_id, estado)
        await _enviar(chat_id, "\U0001F4F8 Envia una o mas <b>fotos</b> de respaldo del despacho. Cuando termines, escribe /listo.")
        return

    if paso == "foto":
        if texto == "/listo":
            fotos = estado.get("fotos") or []
            if not fotos:
                await _enviar(chat_id, "⚠️ Necesito al menos una foto antes de terminar.")
                return
            guardado = await _registrar_auditoria(chat_id, msg.get("from") or {}, estado)
            _borrar_estado(chat_id)
            if not guardado:
                await _enviar(
                    chat_id,
                    "⚠️ Este despacho ya fue auditado por otra persona mientras llenabas el formulario. "
                    "Tus respuestas no se guardaron.\n\nEscribe /lista para elegir otro despacho.",
                )
                return
            confirmado = estado.get("confirmado")
            await _enviar(
                chat_id,
                f"✅ <b>Auditoria registrada</b>\n\U0001F4E6 {estado['despacho']['cliente']}\n"
                f"{'✅ Confirmado' if confirmado else '❌ No confirmado'}\n"
                f"\U0001F4F7 {len(fotos)} foto(s) guardada(s).\n\n"
                "Escribe /lista para auditar otro despacho.",
            )
            return

        fotos_msg = msg.get("photo")
        if not fotos_msg:
            await _enviar(chat_id, "⚠️ Envia una foto, o escribe /listo si ya terminaste.")
            return
        url_foto = await _guardar_foto(fotos_msg, estado, len(estado.get("fotos") or []) + 1)
        if url_foto:
            estado.setdefault("fotos", []).append(url_foto)
            _guardar_estado(chat_id, estado)
            await _enviar(chat_id, f"\U0001F4F8 Foto {len(estado['fotos'])} guardada. Envia otra, o escribe /listo para terminar.")
        else:
            await _enviar(chat_id, "⚠️ No se pudo guardar esa foto (revisar configuracion de Drive). Intenta de nuevo.")
        return

    await _enviar(
        chat_id,
        "\U0001F44B Hola, soy el bot de auditoria de etiquetas Bellaflor.\n\n"
        "/lista - ver despachos pendientes de hoy\n/resumen - avance del dia\n/cancelar - cancelar auditoria en curso",
    )


async def _manejar_callback(cb: dict) -> None:
    chat_id = str(cb["message"]["chat"]["id"])
    texto = cb.get("data", "")
    await _responder_callback(cb["id"])
    estado = _obtener_estado(chat_id)
    paso = estado.get("paso")

    if paso == "eligiendo_poscosecha":
        poscosechas = estado.get("poscosechas", [])
        if texto not in poscosechas:
            await _enviar(chat_id, "⚠️ Esa opcion ya no es valida. Escribe /lista de nuevo.")
            return
        await _mostrar_lista_por_poscosecha(chat_id, texto)
        return

    if paso == "confirmando" and texto in ("CONFIRMADO", "NO_CONFIRMADO"):
        estado["confirmado"] = texto == "CONFIRMADO"
        estado["auditor"] = _nombre_desde_perfil(cb.get("from") or {})
        estado["paso"] = "observaciones"
        _guardar_estado(chat_id, estado)
        if estado["confirmado"]:
            await _enviar(chat_id, "\U0001F4DD Observaciones adicionales (opcional, escribe \"-\" si no hay).")
        else:
            await _enviar(chat_id, "\U0001F4DD Explica que <b>fallo</b>:")
        return


# ---------- Listas / resumen ----------

async def _enviar_lista_pendientes(chat_id: str) -> None:
    special_dispatches.generar_despachos_del_dia()
    pendientes = special_dispatches.despachos_pendientes()
    if not pendientes:
        await _enviar(chat_id, "\U0001F389 No hay despachos pendientes de auditoria hoy.")
        return

    poscosechas = []
    for d in pendientes:
        if d["postcosecha"] not in poscosechas:
            poscosechas.append(d["postcosecha"])

    if len(poscosechas) == 1:
        await _mostrar_lista_por_poscosecha(chat_id, poscosechas[0], pendientes)
        return

    _guardar_estado(chat_id, {"paso": "eligiendo_poscosecha", "poscosechas": poscosechas})
    botones = [[{"texto": p, "datos": p}] for p in poscosechas]
    await _enviar_botones(chat_id, "\U0001F3ED <b>A que poscosecha perteneces?</b>", botones)


async def _mostrar_lista_por_poscosecha(chat_id: str, poscosecha: str, pendientes: list = None) -> None:
    if pendientes is None:
        pendientes = special_dispatches.despachos_pendientes()
    filtrados = [d for d in pendientes if d["postcosecha"] == poscosecha]
    if not filtrados:
        await _enviar(chat_id, f"\U0001F389 No hay despachos pendientes para {poscosecha}.")
        return

    texto = f"\U0001F4CB <b>Despachos pendientes - {poscosecha}</b>\n\n"
    for i, d in enumerate(filtrados, start=1):
        texto += f"{i}. <b>{d['cliente']}</b> - {_entero(d['cajas'])} cajas"
        if d.get("tipo_caja"):
            texto += f" ({d['tipo_caja']})"
        texto += f" - Guia {d.get('guia_hija') or '-'}\n"
    texto += "\n➡️ Responde con el <b>numero</b> del despacho que vas a auditar."
    _guardar_estado(chat_id, {"paso": "eligiendo", "pendientes": filtrados})
    await _enviar(chat_id, texto)


def _entero(valor) -> int:
    try:
        return int(round(float(valor)))
    except (TypeError, ValueError):
        return 0


def _nombre_desde_perfil(perfil: dict) -> str:
    """Nombre + @usuario de Telegram cuando estan disponibles: el nombre
    puede repetirse entre auditores, pero el @usuario es unico y estable,
    asi que se incluye siempre que exista (no solo como respaldo)."""
    nombre = " ".join(p for p in [perfil.get("first_name"), perfil.get("last_name")] if p).strip()
    usuario = perfil.get("username")
    if nombre and usuario:
        return f"{nombre} (@{usuario})"
    if nombre:
        return nombre
    if usuario:
        return f"@{usuario}"
    return str(perfil.get("id") or "desconocido")


def _texto_resumen(d: dict) -> str:
    return (
        f"\U0001F4E6 <b>{d['cliente']}</b>\n"
        f"Destinatario: {d.get('destinatario') or '-'}\n"
        f"\U0001F3ED Poscosecha: {d['postcosecha']}\n"
        f"\U0001F4C4 Guia hija: {d.get('guia_hija') or '-'}\n"
        f"\U0001F4E6 Cajas segun venta: <b>{_entero(d['cajas'])}</b>\n"
        f"\U0001F4E6 Tipo de caja segun venta: <b>{d.get('tipo_caja') or '-'}</b>"
    )


async def _enviar_resumen(chat_id: str) -> None:
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT postcosecha, estado FROM special_dispatches WHERE fecha = CURRENT_DATE
        """)).all()
    if not rows:
        await _enviar(chat_id, "Aun no hay datos de hoy.")
        return
    total = len(rows)
    auditados = sum(1 for _, e in rows if e == "AUDITADO")
    por_pos: dict[str, dict[str, int]] = {}
    for pos, e in rows:
        por_pos.setdefault(pos, {"t": 0, "a": 0})
        por_pos[pos]["t"] += 1
        if e == "AUDITADO":
            por_pos[pos]["a"] += 1
    texto = f"\U0001F4CA <b>Resumen de hoy</b>\n\nAuditados: {auditados} / {total}\n\n"
    for pos in sorted(por_pos):
        texto += f"\U0001F3ED {pos}: {por_pos[pos]['a']}/{por_pos[pos]['t']}\n"
    await _enviar(chat_id, texto)


# ---------- Foto + registro final ----------

async def _guardar_foto(fotos: list, estado: dict, indice: int) -> str:
    file_id = fotos[-1]["file_id"]  # mayor resolucion
    async with httpx.AsyncClient(timeout=20) as client:
        info = (await client.get(_api_url("getFile"), params={"file_id": file_id})).json()
        file_path = info["result"]["file_path"]
        contenido = (await client.get(f"https://api.telegram.org/file/bot{_token()}/{file_path}")).content

    d = estado["despacho"]
    hoy = datetime.now(ECUADOR).strftime("%Y-%m-%d")
    cliente_slug = "".join(c if c.isalnum() else "_" for c in d["cliente"])
    guia_slug = d.get("guia_hija") or "singuia"
    nombre = f"{hoy}_{d['postcosecha']}_{cliente_slug}_{guia_slug}_{indice}.jpg"
    return google_drive.subir_foto(contenido, nombre, subcarpeta=hoy)


async def _registrar_auditoria(chat_id: str, perfil: dict, estado: dict) -> bool:
    """Devuelve False si el despacho ya no estaba PENDIENTE (otro auditor lo
    tomo mientras este formulario estaba en curso) — evita que dos personas
    terminen auditando el mismo despacho por una carrera entre /lista y foto."""
    d = estado["despacho"]
    auditor = estado.get("auditor") or _nombre_desde_perfil(perfil)
    with engine.begin() as conn:
        tomado = conn.execute(text("""
            UPDATE special_dispatches
            SET estado = 'AUDITADO', auditado_por = :auditor, fecha_auditoria = now()
            WHERE id = :id AND estado = 'PENDIENTE'
            RETURNING id
        """), {"auditor": auditor, "id": d["id"]}).first()
        if not tomado:
            return False

        conn.execute(text("""
            INSERT INTO special_dispatch_audits
                (dispatch_id, auditor, cajas_despachadas, confirmado, observaciones, foto_urls, chat_id)
            VALUES (:dispatch_id, :auditor, :cajas, :confirmado, :observaciones, :foto_urls, :chat_id)
        """), {
            "dispatch_id": d["id"], "auditor": auditor,
            "cajas": _entero(d["cajas"]), "confirmado": estado.get("confirmado", False),
            "observaciones": estado.get("observaciones") or "",
            "foto_urls": estado.get("fotos") or [], "chat_id": chat_id,
        })
    return True
