"""Envio de correo por SMTP de Gmail, con contrasena de aplicacion.

Configuracion (backend/.env y variables de entorno en Render):

    GMAIL_USER          cuenta que envia, ej. despachos@gmail.com
    GMAIL_APP_PASSWORD  contrasena de aplicacion de 16 caracteres.
                        NO es la clave de la cuenta: se genera en
                        https://myaccount.google.com/apppasswords y exige
                        tener activa la verificacion en dos pasos.
    MAIL_FROM_NAME      nombre visible del remitente (opcional)
    SMTP_HOST/SMTP_PORT solo para pruebas contra otro servidor

OJO CON RENDER: desde septiembre de 2025 el plan gratuito bloquea el
trafico saliente a los puertos SMTP 25, 465 y 587, asi que este modulo
funciona en local pero NO en produccion mientras BLIS siga en plan free.
El puerto 25 esta bloqueado en todos los planes. Las salidas son subir a
un plan pago, o cambiar el transporte por uno sobre HTTPS (la API de
Gmail, o un proveedor tipo Resend/SendGrid). Todo el resto del modulo es
independiente de esto: solo habria que reemplazar `enviar()`.
"""

import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_TIMEOUT = float(os.getenv("SMTP_TIMEOUT", "30"))

# Validacion deliberadamente laxa: solo descarta lo que no puede ser un
# correo. Rechazar direcciones validas por una regex estricta es peor que
# dejar pasar una dudosa, que el servidor rebotara igual.
_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class CorreoNoConfigurado(RuntimeError):
    """Faltan GMAIL_USER o GMAIL_APP_PASSWORD."""


def usuario() -> str:
    return os.getenv("GMAIL_USER", "").strip()


def configurado() -> bool:
    return bool(usuario() and os.getenv("GMAIL_APP_PASSWORD", "").strip())


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


def enviar(destinatarios: list[str], asunto: str, texto: str, html: str | None = None) -> list[str]:
    """Envia el correo y devuelve la lista real de destinatarios.

    Lanza CorreoNoConfigurado si faltan credenciales, ValueError si no
    queda ningun destinatario valido, y smtplib.SMTPException si el envio
    falla. El llamador decide como reportarlo: aqui no se traga ningun
    error, porque un correo que no sale sin avisar es peor que un error.
    """
    if not configurado():
        raise CorreoNoConfigurado(
            "Faltan GMAIL_USER y/o GMAIL_APP_PASSWORD en el servidor."
        )

    limpios = normalizar(destinatarios)
    if not limpios:
        raise ValueError("No hay ninguna direccion de correo valida.")

    remitente = usuario()
    mensaje = EmailMessage()
    mensaje["From"] = formataddr((os.getenv("MAIL_FROM_NAME", "BLIS"), remitente))
    mensaje["To"] = ", ".join(limpios)
    mensaje["Subject"] = asunto
    mensaje.set_content(texto)
    if html:
        mensaje.add_alternative(html, subtype="html")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT) as servidor:
        servidor.starttls(context=ssl.create_default_context())
        servidor.login(remitente, os.getenv("GMAIL_APP_PASSWORD", ""))
        servidor.send_message(mensaje)

    return limpios
