"""Cliente OAuth2 + Track API de FedEx.

Clonado de REPORTEUPSFEDEX (clase FedExConnector + _consultar_estado_real_fedex).
Token cacheado en memoria a nivel de modulo, igual que el UPS client.
"""

import os
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

UTC = timezone.utc
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"

_token: Optional[str] = None
_token_exp: datetime = datetime.min.replace(tzinfo=UTC)


def _base_url() -> str:
    return os.getenv("FEDEX_BASE_URL", "https://apis.fedex.com")


async def _get_token(client: httpx.AsyncClient) -> str:
    global _token, _token_exp
    if _token and datetime.now(UTC) < _token_exp:
        return _token
    r = await client.post(
        f"{_base_url()}/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": os.getenv("FEDEX_CLIENT_ID", ""),
            "client_secret": os.getenv("FEDEX_CLIENT_SECRET", ""),
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    r.raise_for_status()
    j = r.json()
    _token = j["access_token"]
    _token_exp = datetime.now(UTC) + timedelta(seconds=int(j.get("expires_in", 3600)) - 60)
    return _token


def _demo(trackings: list[str]) -> dict[str, dict]:
    estados = ["IN TRANSIT", "DELIVERED", "AT CUSTOMS", "PICKED UP", "OUT FOR DELIVERY"]
    out = {}
    for t in trackings:
        rnd = random.Random(t + "fx")
        out[t] = {
            "estado": rnd.choice(estados),
            "cajas_manifiesto": None,
            "ultimo_evento": rnd.choice(["Memphis, TN", "Miami, FL", "Quito, EC"]),
            "ts": datetime.now(UTC).isoformat(),
        }
    return out


async def track(trackings: list[str]) -> dict[str, dict]:
    if DEMO_MODE:
        return _demo(trackings)
    out: dict[str, dict] = {}
    async with httpx.AsyncClient(timeout=30) as client:
        token = await _get_token(client)
        for i in range(0, len(trackings), 30):  # FedEx: max 30 guias por llamada
            lote = trackings[i:i + 30]
            try:
                r = await client.post(
                    f"{_base_url()}/track/v1/trackingnumbers",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json={"includeDetailedScans": True,
                          "trackingInfo": [{"trackingNumberInfo": {"trackingNumber": t}} for t in lote]},
                )
                r.raise_for_status()
                for res in r.json()["output"]["completeTrackResults"]:
                    t = res["trackingNumber"]
                    tr = (res.get("trackResults") or [{}])[0]
                    latest = tr.get("latestStatusDetail", {}) or {}
                    pkg = tr.get("packageDetails", {}) or {}
                    cnt = pkg.get("count") or (pkg.get("packagingDescription") or {}).get("count")
                    ends_raw = (tr.get("standardTransitTimeWindow") or {}).get("window", {}).get("ends", "")
                    entrega_est = ends_raw[:10] if ends_raw else ""
                    out[t] = {
                        "estado": latest.get("description", "SIN DATOS"),
                        "entrega_estimada": entrega_est,
                        "cajas_manifiesto": int(cnt) if cnt else None,
                        "ultimo_evento": (latest.get("scanLocation") or {}).get("city", ""),
                        "ts": datetime.now(UTC).isoformat(),
                    }
            except Exception as e:
                for t in lote:
                    out.setdefault(t, {
                        "estado": f"ERROR: {e.__class__.__name__}",
                        "cajas_manifiesto": None, "ultimo_evento": "",
                        "ts": datetime.now(UTC).isoformat(),
                    })
    return out


async def consultar_estado_real(trackings: list[str]) -> dict[str, dict]:
    """Consulta SIEMPRE la API real de FedEx (sin importar DEMO_MODE) —
    usada tras subir un manifiesto PDF para refrescar estado/fecha de
    entrega de los envios acumulados en courier_fedex_envios."""
    if not trackings:
        return {}
    client_id = os.getenv("FEDEX_CLIENT_ID", "")
    client_secret = os.getenv("FEDEX_CLIENT_SECRET", "")
    if not (client_id and client_secret):
        return {}
    base = _base_url()
    out: dict[str, dict] = {}
    async with httpx.AsyncClient(timeout=30) as client:
        token_r = await client.post(
            f"{base}/oauth/token",
            data={"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token_r.raise_for_status()
        token = token_r.json()["access_token"]

        for i in range(0, len(trackings), 30):
            lote = trackings[i:i + 30]
            try:
                r = await client.post(
                    f"{base}/track/v1/trackingnumbers",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json={"includeDetailedScans": False,
                          "trackingInfo": [{"trackingNumberInfo": {"trackingNumber": t}} for t in lote]},
                )
                r.raise_for_status()
                for res in r.json().get("output", {}).get("completeTrackResults", []):
                    t = res.get("trackingNumber", "")
                    tr = (res.get("trackResults") or [{}])[0]
                    latest = tr.get("latestStatusDetail", {}) or {}
                    fecha_entrega = next(
                        (dt.get("dateTime", "")[:10] for dt in tr.get("dateAndTimes", [])
                         if dt.get("type") == "ACTUAL_DELIVERY"), "")
                    if not fecha_entrega:
                        fecha_entrega = (
                            (tr.get("estimatedDeliveryTimeWindow") or {}).get("window", {}).get("ends", "")[:10]
                            or (tr.get("standardTransitTimeWindow") or {}).get("window", {}).get("ends", "")[:10]
                        )
                    out[t] = {
                        "estado_fedex": latest.get("description", ""),
                        "fecha_entrega_fedex": fecha_entrega,
                    }
            except Exception:
                continue
    return out
