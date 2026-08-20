"""Cliente OAuth2 + Track API de UPS.

Clonado de REPORTEUPSFEDEX (clase UPSConnector). El token se cachea en
memoria a nivel de modulo (expira en ~1h, se re-obtiene solo) — no hace
falta persistirlo en Postgres.
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
    return os.getenv("UPS_BASE_URL", "https://onlinetools.ups.com")


async def _get_token(client: httpx.AsyncClient) -> str:
    global _token, _token_exp
    if _token and datetime.now(UTC) < _token_exp:
        return _token
    r = await client.post(
        f"{_base_url()}/security/v1/oauth/token",
        data={"grant_type": "client_credentials"},
        auth=(os.getenv("UPS_CLIENT_ID", ""), os.getenv("UPS_CLIENT_SECRET", "")),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    r.raise_for_status()
    j = r.json()
    _token = j["access_token"]
    _token_exp = datetime.now(UTC) + timedelta(seconds=int(j.get("expires_in", 3600)) - 60)
    return _token


def _demo(trackings: list[str]) -> dict[str, dict]:
    estados = ["EN TRANSITO", "ENTREGADO", "EN ADUANA", "RECIBIDO EN ORIGEN", "EN REPARTO"]
    out = {}
    for t in trackings:
        rnd = random.Random(t)
        out[t] = {
            "estado": rnd.choice(estados),
            "cajas_manifiesto": None,
            "ultimo_evento": rnd.choice(["Louisville, KY", "Miami, FL", "Quito, EC", "Bogota, CO"]),
            "ts": datetime.now(UTC).isoformat(),
        }
    return out


async def track(trackings: list[str]) -> dict[str, dict]:
    if DEMO_MODE:
        return _demo(trackings)
    out: dict[str, dict] = {}
    async with httpx.AsyncClient(timeout=30) as client:
        token = await _get_token(client)
        for t in trackings:
            try:
                r = await client.get(
                    f"{_base_url()}/api/track/v1/details/{t}",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "transId": f"sys-{int(datetime.now(UTC).timestamp())}",
                        "transactionSrc": "blis-torre-control",
                    },
                )
                r.raise_for_status()
                shp = r.json()["trackResponse"]["shipment"][0]
                pkg = shp.get("package", [])
                act = (pkg[0].get("activity") or [{}])[0] if pkg else {}
                out[t] = {
                    "estado": (act.get("status") or {}).get("description", "SIN DATOS"),
                    "cajas_manifiesto": len(pkg) or None,
                    "ultimo_evento": (act.get("location") or {}).get("address", {}).get("city", ""),
                    "ts": datetime.now(UTC).isoformat(),
                }
            except Exception as e:
                out[t] = {
                    "estado": f"ERROR: {e.__class__.__name__}",
                    "cajas_manifiesto": None, "ultimo_evento": "",
                    "ts": datetime.now(UTC).isoformat(),
                }
    return out
