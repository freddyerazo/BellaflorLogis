"""Sube las fotos de respaldo de las auditorias a Google Drive, via un
Apps Script propio desplegado como Web App -- reemplaza DriveApp de
Apps Script del proyecto original, pero conservando su misma ventaja:
corre con la identidad de una cuenta real (no una cuenta de servicio
de Google Cloud, que no tiene cuota de almacenamiento propia y no
puede subir archivos nuevos salvo con delegacion de dominio).

Requiere GOOGLE_DRIVE_UPLOAD_URL (la URL /exec del Apps Script) y
GOOGLE_DRIVE_UPLOAD_SECRET (clave compartida que valida el propio
Apps Script). Si no estan configuradas, sube_foto() devuelve None en
vez de lanzar excepcion -- la auditoria se guarda igual, solo sin
foto_url (mismo espiritu de resiliencia que los demas conectores).
"""

import base64
import os
from typing import Optional

import httpx


def subir_foto(contenido: bytes, nombre_archivo: str, subcarpeta: Optional[str] = None) -> Optional[str]:
    """Sube una foto al Apps Script de BLIS y devuelve su URL publica
    (o None si el endpoint no esta configurado o falla la subida)."""
    url = os.getenv("GOOGLE_DRIVE_UPLOAD_URL", "")
    clave = os.getenv("GOOGLE_DRIVE_UPLOAD_SECRET", "")
    if not url or not clave:
        return None

    try:
        payload = {
            "clave": clave,
            "nombre_archivo": nombre_archivo,
            "subcarpeta": subcarpeta,
            "contenido_base64": base64.b64encode(contenido).decode("ascii"),
        }
        # follow_redirects=True es obligatorio: Apps Script siempre responde
        # con un 302 antes de entregar el contenido, y httpx no lo sigue por
        # defecto -- sin esto, r.json() falla contra el cuerpo del redirect.
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            r = client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
        return data.get("url") if data.get("ok") else None
    except Exception:
        return None
