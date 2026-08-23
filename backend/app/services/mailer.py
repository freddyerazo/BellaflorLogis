"""Envio de correo por la API de Gmail (HTTPS), no por SMTP.

Se eligio la API sobre SMTP por dos razones concretas:

  1. Render bloquea los puertos SMTP 25, 465 y 587 en el plan gratuito
     (cambio de septiembre de 2025). La API va por HTTPS al puerto 443,
     que no esta bloqueado, asi que esto SI funciona en produccion.
  2. No necesita "contrasena de aplicacion", que exige verificacion en
     dos pasos y que Google no ofrece en todas las cuentas.

Configuracion (backend/.env y variables de entorno en Render):

    GMAIL_CLIENT_ID       del cliente OAuth creado en Google Cloud
    GMAIL_CLIENT_SECRET   idem
    GMAIL_REFRESH_TOKEN   se obtiene UNA sola vez con
                          `python scripts/gmail_autorizar.py`
    GMAIL_USER            direccion que envia (para la cabecera From)
    MAIL_FROM_NAME        nombre visible del remitente (opcional)

El refresh token no caduca por tiempo, pero SI se invalida si se revoca
el acceso, se cambia la contrasena de la cuenta o el proyecto de Google
Cloud sigue en modo "Testing" (ahi Google lo caduca a los 7 dias). Para
uso permanente, publicar la app en Google Cloud Console.

Alcance pedido: gmail.send, que solo permite ENVIAR. No da acceso a leer
el buzon: si el token se filtrara, no expone la correspondencia.
"""

import base64
import os
import re
import time
from email.message import EmailMessage
from email.utils import formataddr

import httpx

TOKEN_URL = "https://oauth2.googleapis.com/token"
ENVIO_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
SCOPE = "https://www.googleapis.com/auth/gmail.send"
TIMEOUT = float(os.getenv("GMAIL_TIMEOUT", "30"))

# Validacion deliberadamente laxa: solo descarta lo que no puede ser un
# correo. Rechazar direcciones validas por una regex estricta es peor que
# dejar pasar una dudosa, que el servidor rebotara igual.
_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Token de acceso cacheado en memoria: dura una hora y se pide uno nuevo
# solo cuando esta por vencer. Igual patron que proveedores_client.py.
_token: dict = {"valor": None, "vence": 0.0}


class CorreoNoConfigurado(RuntimeError):
    """Faltan las credenciales de OAuth de Gmail."""


class CorreoNoEnviado(RuntimeError):
    """Google rechazo el envio. El mensaje trae el motivo que dio."""


def usuario() -> str:
    return os.getenv("GMAIL_USER", "").strip()


def configurado() -> bool:
    return all(
        os.getenv(v, "").strip()
        for v in ("GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN")
    )


def es_valido(correo: str) -> bool:
    return bool(_CORREO.match((correo or "").strip()))


def normalizar(correos) -> list[str]:
    """Limpia, valida y quita repetidos conservando el orden."""
    vistos, salida = set(), []
    for bruto in correos or []:
        c = (bruto or "").strip()
        clave = c.lower()
        if c and clave not in vistos and es_valido(c):
            vistos.add(clave)
            salida.append(c)
    return salida


def _access_token(forzar: bool = False) -> str:
    """Cambia el refresh token por uno de acceso, cacheado hasta que venza."""
    if not forzar and _token["valor"] and time.time() < _token["vence"]:
        return _token["valor"]

    if not configurado():
        raise CorreoNoConfigurado(
            "Faltan GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET y/o GMAIL_REFRESH_TOKEN "
            "en el servidor. Ver backend/.env.example."
        )

    datos = {
        "client_id": os.getenv("GMAIL_CLIENT_ID", "").strip(),
        "client_secret": os.getenv("GMAIL_CLIENT_SECRET", "").strip(),
        "refresh_token": os.getenv("GMAIL_REFRESH_TOKEN", "").strip(),
        "grant_type": "refresh_token",
    }

    with httpx.Client(timeout=TIMEOUT) as cliente:
        r = cliente.post(TOKEN_URL, data=datos)

    if r.status_code >= 400:
        # El caso tipico es invalid_grant: el refresh token fue revocado, o
        # el proyecto sigue en modo Testing y Google lo caduco a los 7 dias.
        raise CorreoNoConfigurado(
            f"Google rechazo las credenciales ({r.status_code}): {r.text[:300]}. "
            "Si dice 'invalid_grant', vuelva a generar el refresh token con "
            "scripts/gmail_autorizar.py."
        )

    cuerpo = r.json()
    _token["valor"] = cuerpo["access_token"]
    # 60 s de margen para no usar un token que vence en el camino.
    _token["vence"] = time.time() + int(cuerpo.get("expires_in", 3600)) - 60
    return _token["valor"]


def _mensaje(destinatarios: list[str], asunto: str, texto: str, html: str | None) -> str:
    mensaje = EmailMessage()
    remitente = usuario()
    if remitente:
        mensaje["From"] = formataddr((os.getenv("MAIL_FROM_NAME", "BLIS"), remitente))
    mensaje["To"] = ", ".join(destinatarios)
    mensaje["Subject"] = asunto
    mensaje.set_content(texto)
    if html:
        mensaje.add_alternative(html, subtype="html")
    return base64.urlsafe_b64encode(mensaje.as_bytes()).decode()


def enviar(destinatarios: list[str], asunto: str, texto: str, html: str | None = None) -> list[str]:
    """Envia el correo y devuelve la lista real de destinatarios.

    Lanza CorreoNoConfigurado si faltan credenciales, ValueError si no
    queda ningun destinatario valido, y CorreoNoEnviado si Google rechaza
    el envio. Aqui no se traga ningun error: un correo que no sale sin
    avisar es peor que un error.
    """
    limpios = normalizar(destinatarios)
    if not limpios:
        raise ValueError("No hay ninguna direccion de correo valida.")

    crudo = _mensaje(limpios, asunto, texto, html)

    def _post(token: str):
        with httpx.Client(timeout=TIMEOUT) as cliente:
            return cliente.post(
                ENVIO_URL,
                headers={"Authorization": f"Bearer {token}"},
                json={"raw": crudo},
            )

    try:
        r = _post(_access_token())
        # Un token cacheado puede haberse invalidado del lado de Google
        # (revocacion, cambio de clave). Se reintenta una vez con uno nuevo.
        if r.status_code == 401:
            r = _post(_access_token(forzar=True))
    except httpx.RequestError as exc:
        raise CorreoNoEnviado(f"No se pudo contactar a Google: {exc}")

    if r.status_code >= 400:
        raise CorreoNoEnviado(f"Gmail rechazo el envio ({r.status_code}): {r.text[:300]}")

    return limpios
