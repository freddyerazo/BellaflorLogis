"""Motor de conciliacion: cruza dartis_ventas (agrupado por id_pedido) vs
manifiesto UPS/FedEx vs estado en vivo vs entregas de agencias locales.

Clonado de REPORTEUPSFEDEX (clase Conciliador). Diferencia principal: no
hay un Excel Dartis propio que subir — dartis_ventas ya provee esa
informacion (ver hallazgo en el plan de la Fase 3), y el resultado se
persiste en la tabla courier_reconciliation (en vez de vivir solo en
memoria) para sobrevivir reinicios/redeploys.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text

from app.database.connection import engine
from app.services import courier_entregas_locales as entregas_locales
from app.services import courier_fedex_client as fedex_client
from app.services import courier_ups_client as ups_client

UTC = timezone.utc

_lock = asyncio.Lock()
_ultimo_error: Optional[str] = None
_ultimo_refresh: Optional[str] = None


def _normalizar_courier(courier_raw: str) -> str:
    c = (courier_raw or "").strip().upper()
    if "UPS" in c:
        return "UPS"
    if "FEDEX" in c or "FDX" in c or "FED EX" in c:
        return "FEDEX"
    return c or "OTRO"


def _obtener_base_dartis() -> list[dict]:
    """dartis_ventas agrupado por id_pedido — reemplaza al Excel Dartis
    del proyecto original (ver hallazgo del plan de la Fase 3).

    Se agrupa SOLO por id_pedido: courier_reconciliation tiene UNIQUE(factura),
    y un mismo id_pedido puede traer especies en filas con algun campo distinto
    (ej. fecha) -- agruparlas tambien por esos campos partia un pedido en dos
    filas con la misma factura, violando el UNIQUE y tumbando el refresco
    completo (y el arranque del servidor, que lo dispara una vez al iniciar)."""
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id_pedido AS factura, MAX(agencia_carga) AS courier_raw, MAX(empresa) AS empresa,
                   MAX(cliente) AS cliente, MAX(destinatario) AS destinatario,
                   MAX(vendedor) AS vendedor_cliente, MAX(fecha) AS fecha_dartis,
                   SUM(total_piezas) AS cajas_dartis
            FROM dartis_ventas
            WHERE agencia_carga IS NOT NULL AND active = true
            GROUP BY id_pedido
        """)).mappings().all()

    base = []
    for r in rows:
        base.append({
            "factura": r["factura"],
            "courier": _normalizar_courier(r["courier_raw"]),
            "courier_raw": (r["courier_raw"] or "").strip(),
            "empresa": r["empresa"],
            "cliente": r["cliente"],
            "destinatario": r["destinatario"],
            "vendedor_cliente": r["vendedor_cliente"],
            "fecha_dartis": r["fecha_dartis"].isoformat() if r["fecha_dartis"] else None,
            "cajas_dartis": round(float(r["cajas_dartis"] or 0)),
        })
    return base


def _obtener_manifiesto_ups() -> dict[int, dict]:
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT factura, tracking, estado, fecha_manifiesto, ship_to, servicio, entrega_programada
            FROM courier_ups_manifest ORDER BY factura, id
        """)).mappings().all()
    return _agrupar_por_factura(rows)


def _obtener_manifiesto_fedex() -> dict[int, dict]:
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT factura, tracking, estado_fedex AS estado, fecha_envio AS fecha_manifiesto,
                   destinatario AS ship_to, fecha_entrega_fedex AS entrega_programada
            FROM courier_fedex_envios WHERE factura IS NOT NULL ORDER BY factura, id
        """)).mappings().all()
    return _agrupar_por_factura(rows)


def _agrupar_por_factura(rows) -> dict[int, dict]:
    out: dict[int, dict] = {}
    for r in rows:
        f = r["factura"]
        bulto = {"tracking": r["tracking"], "estado": r["estado"], "entrega_programada": r["entrega_programada"]}
        if f in out:
            out[f]["bultos"] += 1
            out[f]["trackings_extra"] += 1
            out[f]["trackings"].append(r["tracking"])
            out[f]["detalle"].append(bulto)
        else:
            out[f] = {
                "bultos": 1, "trackings_extra": 0,
                "tracking": r["tracking"], "trackings": [r["tracking"]], "detalle": [bulto],
                "estado": r["estado"], "fecha_manifiesto": r["fecha_manifiesto"],
                "ship_to": r["ship_to"], "servicio": r.get("servicio"),
                "entrega_programada": r["entrega_programada"],
            }
    return out


def _evaluar(courier: str, dartis_total, bultos_csv, manif_api) -> str:
    if courier == "UPS":
        if bultos_csv is None:
            return "SIN MANIFIESTO"
        if dartis_total != bultos_csv:
            return "DISCREPANCIA"
        if manif_api is not None and manif_api != dartis_total:
            return "DISCREPANCIA"
        return "OK"
    if manif_api is None:
        return "PENDIENTE"
    return "OK" if dartis_total == manif_api else "DISCREPANCIA"


def _armar_fila(r: dict, csv_m: Optional[dict], live: dict, con_vivo: bool) -> dict:
    bultos_csv = csv_m["bultos"] if csv_m else None
    manif_api = live.get("cajas_manifiesto")
    return {
        **r,
        "tracking": csv_m["tracking"] if csv_m else "",
        "trackings": csv_m["trackings"] if csv_m else [],
        "detalle_bultos": csv_m["detalle"] if csv_m else [],
        "trackings_extra": csv_m["trackings_extra"] if csv_m else 0,
        "bultos_csv": bultos_csv,
        "estado_csv": csv_m["estado"] if csv_m else None,
        "fecha_manifiesto": csv_m["fecha_manifiesto"] if csv_m else None,
        "servicio": csv_m["servicio"] if csv_m else None,
        "entrega_programada": csv_m["entrega_programada"] if csv_m else None,
        "cajas_manifiesto": manif_api,
        "estado_vivo": live.get("estado", "PENDIENTE") if con_vivo else "SIN COBERTURA",
        "entrega_estimada": live.get("entrega_estimada", ""),
        "ubicacion": live.get("ultimo_evento", ""),
        "conciliacion": _evaluar(r["courier"], r["cajas_dartis"], bultos_csv, manif_api),
        "diferencia": (r["cajas_dartis"] - bultos_csv) if bultos_csv is not None
                      else ((r["cajas_dartis"] - manif_api) if manif_api is not None else None),
        "fecha_entrega_real": None, "foto_url": None, "cliente_confirmado_ocr": False,
    }


def _armar_fila_otro(r: dict, match: Optional[dict]) -> dict:
    base = {
        **r,
        "tracking": "", "trackings": [], "detalle_bultos": [], "trackings_extra": 0,
        "bultos_csv": None, "fecha_manifiesto": None, "servicio": None,
        "cajas_manifiesto": None, "ubicacion": "", "fecha_entrega_real": None,
        "foto_url": None, "cliente_confirmado_ocr": False,
    }
    if not match:
        return {**base, "estado_csv": None, "entrega_programada": None,
                "estado_vivo": "PENDIENTE", "entrega_estimada": "",
                "conciliacion": "PENDIENTE", "diferencia": None}
    fecha_entrega = match["fecha_documento"].isoformat() if match["fecha_documento"] else None
    return {
        **base,
        "estado_csv": "Entregado", "entrega_programada": fecha_entrega,
        "cajas_manifiesto": r["cajas_dartis"],
        "estado_vivo": "Entregado", "entrega_estimada": fecha_entrega,
        "fecha_entrega_real": fecha_entrega,
        "foto_url": match.get("foto_url"),
        "cliente_confirmado_ocr": bool(match.get("cliente_confirmado_ocr")),
        "conciliacion": "OK", "diferencia": 0,
    }


def _resumen(cajas: list[dict]) -> dict:
    def agg(filtro=None):
        rows = [c for c in cajas if filtro is None or filtro(c)]
        return {
            "guias": len(rows),
            "vendidas": sum(c["cajas_dartis"] for c in rows),
            "manifiesto": sum(c["cajas_manifiesto"] or 0 for c in rows),
            "ok": sum(1 for c in rows if c["conciliacion"] == "OK"),
            "discrepancias": sum(1 for c in rows if c["conciliacion"] == "DISCREPANCIA"),
            "pendientes": sum(1 for c in rows if c["conciliacion"] == "PENDIENTE"),
            "sin_manifiesto": sum(1 for c in rows if c["conciliacion"] == "SIN MANIFIESTO"),
            "no_en_dartis": sum(1 for c in rows if c["conciliacion"] == "NO EN DARTIS"),
        }
    return {
        "total": agg(),
        "UPS": agg(lambda c: c["courier"] == "UPS"),
        "FEDEX": agg(lambda c: c["courier"] == "FEDEX"),
        "OTRO": agg(lambda c: c["courier"] not in ("UPS", "FEDEX")),
    }


def obtener_snapshot() -> dict:
    """Lee el snapshot persistido (courier_reconciliation) — no dispara
    ninguna llamada en vivo, solo lo que dejo el ultimo refrescar()."""
    with engine.connect() as conn:
        cajas = [dict(r) for r in conn.execute(text(
            "SELECT * FROM courier_reconciliation ORDER BY (conciliacion != 'DISCREPANCIA'), factura"
        )).mappings().all()]
    return {
        "cajas": cajas,
        "resumen": _resumen(cajas) if cajas else {},
        "actualizado": _ultimo_refresh,
        "error": _ultimo_error,
    }


def obtener_discrepancias() -> list[dict]:
    with engine.connect() as conn:
        return [dict(r) for r in conn.execute(text("""
            SELECT * FROM courier_reconciliation
            WHERE conciliacion IN ('DISCREPANCIA', 'SIN MANIFIESTO', 'NO EN DARTIS')
            ORDER BY factura
        """)).mappings().all()]


async def refrescar() -> dict:
    global _ultimo_error, _ultimo_refresh
    async with _lock:
        error = None
        try:
            base = await asyncio.to_thread(_obtener_base_dartis)
        except Exception as e:
            base, error = [], str(e)

        try:
            manif_ups = await asyncio.to_thread(_obtener_manifiesto_ups)
        except Exception as e:
            manif_ups, error = {}, (error + " | " if error else "") + f"Manifiesto UPS: {e}"

        try:
            manif_fdx = await asyncio.to_thread(_obtener_manifiesto_fedex)
        except Exception as e:
            manif_fdx, error = {}, (error + " | " if error else "") + f"Manifiesto FedEx: {e}"

        facturas_dartis = {r["factura"] for r in base}
        extras_ups = [f for f in manif_ups if f not in facturas_dartis]
        extras_fdx = [f for f in manif_fdx if f not in facturas_dartis and f not in manif_ups]

        guias_ups = [manif_ups[r["factura"]]["tracking"] for r in base
                     if r["courier"] == "UPS" and r["factura"] in manif_ups]
        guias_ups += [manif_ups[f]["tracking"] for f in extras_ups]
        guias_fdx = [manif_fdx[r["factura"]]["tracking"] for r in base
                     if r["courier"] == "FEDEX" and r["factura"] in manif_fdx]
        guias_fdx += [manif_fdx[f]["tracking"] for f in extras_fdx]

        try:
            vivo_ups, vivo_fdx, entregas = await asyncio.gather(
                ups_client.track(guias_ups), fedex_client.track(guias_fdx), entregas_locales.fetch()
            )
        except Exception as e:
            vivo_ups, vivo_fdx, entregas = {}, {}, []
            error = (error + " | " if error else "") + f"Track API: {e}"
        vivo = {**vivo_ups, **vivo_fdx}
        entregas_por_agencia = entregas_locales.indexar_entregas_por_agencia(entregas)

        cajas = []
        for r in base:
            if r["courier"] not in ("UPS", "FEDEX"):
                match = entregas_locales.emparejar_entrega_local(r, entregas_por_agencia)
                cajas.append(_armar_fila_otro(r, match))
                continue
            m = manif_fdx.get(r["factura"]) if r["courier"] == "FEDEX" else manif_ups.get(r["factura"])
            t = m["tracking"] if m else ""
            cajas.append(_armar_fila(r, m, vivo.get(t, {}), t in vivo))

        for f in extras_ups:
            m = manif_ups[f]
            t = m["tracking"]
            r = {"factura": f, "courier": "UPS", "courier_raw": "UPS", "empresa": "",
                 "cliente": m.get("ship_to", ""), "destinatario": m.get("ship_to", ""),
                 "vendedor_cliente": None, "cajas_dartis": 0, "fecha_dartis": None}
            fila = _armar_fila(r, m, vivo.get(t, {}), t in vivo)
            fila["conciliacion"] = "NO EN DARTIS"
            cajas.append(fila)

        for f in extras_fdx:
            m = manif_fdx[f]
            t = m["tracking"]
            r = {"factura": f, "courier": "FEDEX", "courier_raw": "FEDEX", "empresa": "",
                 "cliente": m.get("ship_to", ""), "destinatario": m.get("ship_to", ""),
                 "vendedor_cliente": None, "cajas_dartis": 0, "fecha_dartis": None}
            fila = _armar_fila(r, m, vivo.get(t, {}), t in vivo)
            fila["conciliacion"] = "NO EN DARTIS"
            cajas.append(fila)

        await asyncio.to_thread(_persistir, cajas)
        _ultimo_error = error
        _ultimo_refresh = datetime.now(UTC).isoformat()

        return {
            "resumen": _resumen(cajas),
            "actualizado": _ultimo_refresh,
            "error": _ultimo_error,
            "total_facturas": len(cajas),
        }


_PERSISTIR_COLUMNAS = [
    "factura", "courier", "courier_raw", "empresa", "cliente", "destinatario", "vendedor_cliente",
    "cajas_dartis", "fecha_dartis", "tracking", "trackings", "detalle_bultos", "trackings_extra",
    "bultos_csv", "estado_csv", "fecha_manifiesto", "servicio", "entrega_programada",
    "cajas_manifiesto", "estado_vivo", "entrega_estimada", "ubicacion", "conciliacion", "diferencia",
    "fecha_entrega_real", "foto_url", "cliente_confirmado_ocr",
]


def _persistir(cajas: list[dict]) -> None:
    """Reemplaza el snapshot completo (igual semantica que el original:
    siempre refleja el ultimo refresco, no un merge incremental).

    Insercion masiva via execute_values (mismo patron que dartis_import.py):
    con miles de facturas, insertar fila por fila tarda minutos por la
    latencia de red hacia Supabase (~200ms/round-trip medido); en batch es
    una sola ida y vuelta por lote."""
    from psycopg2.extras import execute_values

    tuples = [
        (
            c["factura"], c["courier"], c["courier_raw"], c["empresa"], c["cliente"], c["destinatario"],
            c["vendedor_cliente"], c["cajas_dartis"], c["fecha_dartis"], c["tracking"],
            json.dumps(c["trackings"]), json.dumps(c["detalle_bultos"]), c["trackings_extra"],
            c["bultos_csv"], c["estado_csv"], c["fecha_manifiesto"], c["servicio"], c["entrega_programada"],
            c["cajas_manifiesto"], c["estado_vivo"], c["entrega_estimada"], c["ubicacion"],
            c["conciliacion"], c["diferencia"], c["fecha_entrega_real"], c["foto_url"],
            c["cliente_confirmado_ocr"],
        )
        for c in cajas
    ]

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE courier_reconciliation"))
        if not tuples:
            return
        raw = conn.connection.cursor()
        execute_values(raw, f"""
            INSERT INTO courier_reconciliation ({", ".join(_PERSISTIR_COLUMNAS)}) VALUES %s
        """, tuples, page_size=1000)
