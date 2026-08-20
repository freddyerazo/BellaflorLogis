"""Sube las fotos de respaldo de las auditorias a Google Drive, via una
cuenta de servicio (Drive API v3) — reemplaza DriveApp de Apps Script.

Requiere GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON (el JSON de la cuenta de
servicio, como string) y GOOGLE_DRIVE_FOLDER_ID (carpeta raiz
"Auditoria Etiquetas - Fotos" u otra, compartida con el email de la
cuenta de servicio como Editor). Si no estan configuradas, sube_foto()
devuelve None en vez de lanzar excepcion — la auditoria se guarda igual,
solo sin foto_url (mismo espiritu de resiliencia que los demas conectores).
"""

import json
import os
from datetime import datetime, timezone
from typing import Optional

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]
UTC = timezone.utc

_credentials = None


def _get_credentials():
    global _credentials
    if _credentials is not None:
        return _credentials
    raw = os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON", "")
    if not raw:
        return None
    from google.oauth2 import service_account

    info = json.loads(raw)
    _credentials = service_account.Credentials.from_service_account_info(info, scopes=DRIVE_SCOPES)
    return _credentials


def _access_token() -> Optional[str]:
    creds = _get_credentials()
    if creds is None:
        return None
    from google.auth.transport.requests import Request

    if not creds.valid:
        creds.refresh(Request())
    return creds.token


def _buscar_o_crear_carpeta(token: str, nombre: str, parent_id: str) -> Optional[str]:
    import requests

    q = f"'{parent_id}' in parents and name='{nombre}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    r = requests.get(
        "https://www.googleapis.com/drive/v3/files",
        params={"q": q, "fields": "files(id)"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    r.raise_for_status()
    encontrados = r.json().get("files", [])
    if encontrados:
        return encontrados[0]["id"]

    r = requests.post(
        "https://www.googleapis.com/drive/v3/files",
        json={"name": nombre, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]},
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["id"]


def subir_foto(contenido: bytes, nombre_archivo: str, subcarpeta: Optional[str] = None) -> Optional[str]:
    """Sube una foto a Drive y devuelve su URL publica (o None si Drive
    no esta configurado o falla la subida)."""
    import requests

    token = _access_token()
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
    if not token or not folder_id:
        return None

    try:
        subcarpeta = subcarpeta or datetime.now(UTC).strftime("%Y-%m-%d")
        carpeta_id = _buscar_o_crear_carpeta(token, subcarpeta, folder_id)

        metadata = {"name": nombre_archivo, "parents": [carpeta_id]}
        r = requests.post(
            "https://www.googleapis.com/upload/drive/v3/files",
            params={"uploadType": "multipart", "fields": "id"},
            headers={"Authorization": f"Bearer {token}"},
            files={
                "metadata": (None, json.dumps(metadata), "application/json"),
                "file": (nombre_archivo, contenido, "image/jpeg"),
            },
            timeout=30,
        )
        r.raise_for_status()
        file_id = r.json()["id"]

        requests.post(
            f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions",
            json={"role": "reader", "type": "anyone"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        return f"https://drive.google.com/file/d/{file_id}/view"
    except Exception:
        return None
