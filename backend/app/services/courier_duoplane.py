"""Sincronizacion con Duoplane: completa shipments de Purchase Orders
abiertas usando los trackings ya capturados en courier_ups_manifest /
courier_fedex_envios.

Clonado de REPORTEUPSFEDEX (_trackings_por_po_duoplane +
_sincronizar_duoplane), leyendo de Postgres en vez de CSVs. A diferencia
del original, "shipper_name" ahora refleja el courier real de cada
tracking (UPS o FedEx) en vez de quedar hardcodeado a "UPS".
"""

import os
import re

import httpx
from sqlalchemy import text

from app.database.connection import engine

DUOPLANE_API_KEY = os.getenv("DUOPLANE_API_KEY", "")
DUOPLANE_API_PASSWORD = os.getenv("DUOPLANE_API_PASSWORD", "")
DUOPLANE_BASE_URL = os.getenv("DUOPLANE_BASE_URL", "https://app.duoplane.com")

# Token <numero>-<numero> embebido en la referencia de UPS/FedEx que
# coincide con el "purchase_order_public_reference" de Duoplane.
DUOPLANE_PO_RE = re.compile(r"\b(\d{3,6}-\d{1,2})\b")


def _trackings_por_po_duoplane() -> dict[str, list[tuple[str, str]]]:
    """Devuelve {PO_duoplane: [(tracking, courier), ...]} buscando el token
    tanto en courier_ups_manifest.referencia como en
    courier_fedex_envios.referencia."""
    out: dict[str, list[tuple[str, str]]] = {}
    with engine.connect() as conn:
        for tracking, referencia in conn.execute(text(
            "SELECT tracking, referencia FROM courier_ups_manifest WHERE referencia IS NOT NULL"
        )):
            m = DUOPLANE_PO_RE.search(referencia or "")
            if m and tracking:
                out.setdefault(m.group(1), []).append((tracking, "UPS"))

        for tracking, referencia in conn.execute(text(
            "SELECT tracking, referencia FROM courier_fedex_envios WHERE referencia IS NOT NULL"
        )):
            m = DUOPLANE_PO_RE.search(referencia or "")
            if m and tracking:
                out.setdefault(m.group(1), []).append((tracking, "FEDEX"))
    return out


async def sincronizar() -> dict:
    if not (DUOPLANE_API_KEY and DUOPLANE_API_PASSWORD):
        return {"ok": False, "error": "DUOPLANE_API_KEY / DUOPLANE_API_PASSWORD no configurados."}

    trackings_por_po = _trackings_por_po_duoplane()
    creados, pendientes, errores = [], [], []

    async with httpx.AsyncClient(auth=(DUOPLANE_API_KEY, DUOPLANE_API_PASSWORD), timeout=30) as client:
        try:
            r = await client.get(
                f"{DUOPLANE_BASE_URL}/purchase_orders.json",
                params={"search[fulfilled]": "false", "per_page": 250},
            )
            r.raise_for_status()
        except Exception as e:
            return {"ok": False, "error": f"No se pudo consultar Duoplane: {e}"}
        pos_abiertas = r.json()

        for po in pos_abiertas:
            ref = po.get("public_reference", "")
            pares = trackings_por_po.get(ref)
            items = po.get("order_items") or []
            if not pares or not items:
                pendientes.append(ref)
                continue
            # shipper_name: courier real del primer tracking del grupo (en
            # vez de hardcodear "UPS" como el original).
            shipper = pares[0][1]
            trackings = [t for t, _ in pares]
            payload = {
                "shipment": {
                    "shipper_name": shipper,
                    "shipment_items_attributes": [
                        {"order_item_id": it["id"], "quantity": it.get("quantity_open") or it["quantity"]}
                        for it in items
                    ],
                    "shipment_trackings_attributes": [{"tracking": t} for t in trackings],
                }
            }
            try:
                resp = await client.post(
                    f"{DUOPLANE_BASE_URL}/purchase_orders/{po['id']}/shipments.json", json=payload,
                )
                if resp.status_code == 200:
                    creados.append({"po": ref, "trackings": trackings, "shipper": shipper})
                else:
                    errores.append({"po": ref, "error": resp.text[:200]})
            except Exception as e:
                errores.append({"po": ref, "error": str(e)})

    return {
        "ok": True,
        "revisadas": len(pos_abiertas),
        "creados": creados,
        "pendientes": pendientes,
        "errores": errores,
    }
