"""Bot de Telegram para el auditor de poscosecha — port del state machine
de Code.gs (Auditoria_LEsp). Mismo flujo: /lista -> elegir poscosecha (si
hay mas de una) -> elegir despacho -> auditor -> cajas -> piezas -> tipo
de caja OK? -> especie OK? -> etiqueta OK? -> observaciones -> foto ->
se guarda en special_dispatch_audits y se marca el despacho AUDITADO.

El estado de la conversacion vive en telegram_conversation_state
(Postgres) en vez de CacheService de Apps Script, para sobrevivir un
redeploy de Render a media auditoria.
"""

import json
import os
from datetime import datetime, timezone

import httpx
from sqlalchemy import text

from app.database.connection import engine
from app.services import google_drive, special_dispatches

UTC = timezone.utc


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
        estado = {"paso": "auditor", "despacho": despacho}
        _guardar_estado(chat_id, estado)
        d = despacho
        texto_msg = (
            f"\U0001F4E6 <b>{d['cliente']}</b>\n\U0001F3ED Poscosecha: {d['postcosecha']}\n"
            f"\U0001F4C4 Guia hija: {d['guia_hija']}\n\U0001F4E6 Cajas segun venta: {d['cajas']}"
        )
        if d.get("tipo_caja"):
            texto_msg += f"\n\U0001F4E6 Tipo de caja segun venta: <b>{d['tipo_caja']}</b>"
        texto_msg += f"\n\U0001F3F7️ Etiqueta: {d.get('etiqueta') or ''}"
        if d.get("instrucciones"):
            texto_msg += f"\n\U0001F4CB Instrucciones: {d['instrucciones']}"
        texto_msg += "\n\n\U0001F464 <b>Nombre del auditor?</b>"
        await _enviar(chat_id, texto_msg)
        return

    if paso == "auditor":
        estado["auditor"] = texto
        estado["paso"] = "cajas"
        _guardar_estado(chat_id, estado)
        await _enviar(chat_id, f"\U0001F4E6 Cuantas <b>cajas</b> se estan despachando? (segun venta: {estado['despacho']['cajas']})")
        return

    if paso == "cajas":
        try:
            cajas = float(texto.replace(",", "."))
        except ValueError:
            await _enviar(chat_id, "⚠️ Escribe solo el numero de cajas.")
            return
        estado["cajas"] = cajas
        estado["paso"] = "piezas"
        _guardar_estado(chat_id, estado)
        await _enviar(chat_id, "\U0001F339 Cuantas <b>piezas</b> (tallos) se estan despachando?")
        return

    if paso == "piezas":
        try:
            piezas = float(texto.replace(",", "."))
        except ValueError:
            await _enviar(chat_id, "⚠️ Escribe solo el numero de piezas.")
            return
        estado["piezas"] = piezas
        estado["paso"] = "tipoCaja"
        _guardar_estado(chat_id, estado)
        tipo_esperado = estado["despacho"].get("tipo_caja")
        pregunta = "\U0001F4E6 El <b>tipo de caja</b> revisado esta correcto"
        pregunta += f" (segun venta: <b>{tipo_esperado}</b>)?" if tipo_esperado else " (HB, QB, EB)?"
        await _enviar_botones(chat_id, pregunta, [[{"texto": "✅ Si", "datos": "SI"}, {"texto": "❌ No", "datos": "NO"}]])
        return

    if paso == "observaciones":
        estado["observaciones"] = "" if texto == "-" else texto
        estado["paso"] = "foto"
        _guardar_estado(chat_id, estado)
        await _enviar(chat_id, "\U0001F4F8 Envia ahora la <b>foto de respaldo</b> del despacho de las cajas.")
        return

    if paso == "foto":
        fotos = msg.get("photo")
        if not fotos:
            await _enviar(chat_id, "⚠️ Necesito una foto. Envia la imagen del despacho.")
            return
        url_foto = await _guardar_foto(fotos, estado)
        await _registrar_auditoria(chat_id, estado, url_foto)
        _borrar_estado(chat_id)
        await _enviar(
            chat_id,
            f"✅ <b>Auditoria registrada</b>\n\U0001F4E6 {estado['despacho']['cliente']}\n"
            f"\U0001F4E6 Cajas: {estado['cajas']}\n\U0001F339 Piezas: {estado['piezas']}\n"
            f"\U0001F4F7 Foto {'guardada' if url_foto else 'NO se pudo guardar (revisar configuracion de Drive)'}.\n\n"
            "Escribe /lista para auditar otro despacho.",
        )
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

    if paso == "tipoCaja" and texto in ("SI", "NO"):
        estado["tipoCajaOK"] = texto == "SI"
        estado["paso"] = "especie"
        _guardar_estado(chat_id, estado)
        await _enviar_botones(chat_id, "\U0001F9EC La <b>especie</b> esta igual en la etiqueta especial y en la etiqueta de caja?",
                               [[{"texto": "✅ Si", "datos": "SI"}, {"texto": "❌ No", "datos": "NO"}]])
        return

    if paso == "especie" and texto in ("SI", "NO"):
        estado["especieOK"] = texto == "SI"
        estado["paso"] = "etiqueta"
        _guardar_estado(chat_id, estado)
        await _enviar_botones(chat_id, "\U0001F3F7️ La <b>etiqueta especial</b> esta correctamente aplicada?",
                               [[{"texto": "✅ Si", "datos": "SI"}, {"texto": "❌ No", "datos": "NO"}]])
        return

    if paso == "etiqueta" and texto in ("SI", "NO"):
        estado["etiquetaOK"] = texto == "SI"
        estado["paso"] = "observaciones"
        _guardar_estado(chat_id, estado)
        await _enviar(chat_id, "\U0001F4DD Escribe las <b>observaciones</b> (o envia \"-\" si no hay).")
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
        texto += f"{i}. <b>{d['cliente']}</b> - {d['cajas']} cajas"
        if d.get("tipo_caja"):
            texto += f" ({d['tipo_caja']})"
        texto += f" - Guia {d['guia_hija']}\n"
    texto += "\n➡️ Responde con el <b>numero</b> del despacho que vas a auditar."
    _guardar_estado(chat_id, {"paso": "eligiendo", "pendientes": filtrados})
    await _enviar(chat_id, texto)


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

async def _guardar_foto(fotos: list, estado: dict) -> str:
    file_id = fotos[-1]["file_id"]  # mayor resolucion
    async with httpx.AsyncClient(timeout=20) as client:
        info = (await client.get(_api_url("getFile"), params={"file_id": file_id})).json()
        file_path = info["result"]["file_path"]
        contenido = (await client.get(f"https://api.telegram.org/file/bot{_token()}/{file_path}")).content

    d = estado["despacho"]
    hoy = datetime.now(UTC).strftime("%Y-%m-%d")
    cliente_slug = "".join(c if c.isalnum() else "_" for c in d["cliente"])
    nombre = f"{hoy}_{d['postcosecha']}_{cliente_slug}_{d['guia_hija']}.jpg"
    return google_drive.subir_foto(contenido, nombre, subcarpeta=hoy)


async def _registrar_auditoria(chat_id: str, estado: dict, url_foto: str) -> None:
    d = estado["despacho"]
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO special_dispatch_audits
                (dispatch_id, auditor, cajas_despachadas, piezas_despachadas,
                 tipo_caja_ok, especie_ok, etiqueta_ok, observaciones, foto_url, chat_id)
            VALUES (:dispatch_id, :auditor, :cajas, :piezas, :tipo_caja_ok, :especie_ok, :etiqueta_ok,
                    :observaciones, :foto_url, :chat_id)
        """), {
            "dispatch_id": d["id"], "auditor": estado.get("auditor"),
            "cajas": estado.get("cajas"), "piezas": estado.get("piezas"),
            "tipo_caja_ok": estado.get("tipoCajaOK"), "especie_ok": estado.get("especieOK"),
            "etiqueta_ok": estado.get("etiquetaOK"), "observaciones": estado.get("observaciones"),
            "foto_url": url_foto, "chat_id": chat_id,
        })
        conn.execute(text("""
            UPDATE special_dispatches
            SET estado = 'AUDITADO', auditado_por = :auditor, fecha_auditoria = now()
            WHERE id = :id
        """), {"auditor": estado.get("auditor"), "id": d["id"]})
