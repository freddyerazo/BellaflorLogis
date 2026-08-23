"""Obtiene el GMAIL_REFRESH_TOKEN para el envio de correos de BLIS.

Se corre UNA sola vez, en una maquina con navegador:

    cd backend
    python scripts/gmail_autorizar.py

Antes hay que crear el cliente OAuth en Google Cloud Console:

  1. console.cloud.google.com -> crear (o elegir) un proyecto
  2. "APIs y servicios" -> "Biblioteca" -> habilitar **Gmail API**
  3. "Pantalla de consentimiento de OAuth":
       - Tipo "Externo" si la cuenta es @gmail.com; "Interno" si es de
         Google Workspace del dominio
       - Agregar la cuenta que va a enviar como "Usuario de prueba"
       - IMPORTANTE: mientras la app siga en modo "Testing", Google caduca
         el refresh token a los 7 dias. Para uso permanente hay que
         PUBLICAR la app (boton "Publicar aplicacion")
  4. "Credenciales" -> "Crear credenciales" -> "ID de cliente de OAuth"
       - Tipo de aplicacion: **Aplicacion de escritorio**
  5. Copiar el ID de cliente y el secreto

El script abre el navegador, pide autorizacion y escupe las tres lineas
que van en backend/.env. El unico permiso que solicita es gmail.send:
permite enviar, NO leer el buzon.
"""

import http.server
import os
import secrets
import socket
import sys
import threading
import urllib.parse
import webbrowser

import httpx

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/gmail.send"

_recibido: dict = {}


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        _recibido.update({k: v[0] for k, v in params.items()})

        ok = "code" in _recibido
        cuerpo = (
            "<h2>Listo.</h2><p>Ya puede cerrar esta pestana y volver a la terminal.</p>"
            if ok else
            f"<h2>No se autorizo</h2><p>{_recibido.get('error', 'sin detalle')}</p>"
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(f"<html><body style='font-family:sans-serif'>{cuerpo}</body></html>".encode())

    def log_message(self, *args):
        pass  # sin ruido en la terminal


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> int:
    client_id = (os.getenv("GMAIL_CLIENT_ID") or input("GMAIL_CLIENT_ID: ")).strip()
    client_secret = (os.getenv("GMAIL_CLIENT_SECRET") or input("GMAIL_CLIENT_SECRET: ")).strip()
    if not client_id or not client_secret:
        print("Faltan el ID de cliente y/o el secreto.")
        return 1

    puerto = _puerto_libre()
    redirect_uri = f"http://localhost:{puerto}"
    estado = secrets.token_urlsafe(16)

    servidor = http.server.HTTPServer(("127.0.0.1", puerto), _Handler)
    threading.Thread(target=servidor.handle_request, daemon=True).start()

    url = AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPE,
        # offline + consent son lo que hace que Google devuelva un
        # refresh token; sin ellos solo manda uno de acceso de 1 hora.
        "access_type": "offline",
        "prompt": "consent",
        "state": estado,
    })

    print("\nSe abrira el navegador para autorizar el envio de correos.")
    print("Si no se abre, pegue esta direccion:\n")
    print(url + "\n")
    webbrowser.open(url)

    print("Esperando la autorizacion...")
    for _ in range(600):  # hasta 5 minutos
        if _recibido:
            break
        threading.Event().wait(0.5)

    if "code" not in _recibido:
        print("\nNo se recibio la autorizacion:", _recibido.get("error", "tiempo agotado"))
        return 1
    if _recibido.get("state") != estado:
        print("\nEl parametro 'state' no coincide: se aborta por seguridad.")
        return 1

    r = httpx.post(TOKEN_URL, timeout=30, data={
        "code": _recibido["code"],
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    })

    if r.status_code >= 400:
        print(f"\nGoogle rechazo el intercambio ({r.status_code}): {r.text[:400]}")
        return 1

    refresh = r.json().get("refresh_token")
    if not refresh:
        print("\nGoogle no devolvio refresh_token. Suele pasar si la cuenta ya habia "
              "autorizado esta app: revoque el acceso en "
              "myaccount.google.com/permissions y vuelva a correr el script.")
        return 1

    print("\n" + "=" * 68)
    print("Agregue estas lineas a backend/.env (y a las variables de Render):")
    print("=" * 68)
    print(f"GMAIL_CLIENT_ID={client_id}")
    print(f"GMAIL_CLIENT_SECRET={client_secret}")
    print(f"GMAIL_REFRESH_TOKEN={refresh}")
    print("GMAIL_USER=<la direccion que acaba de autorizar>")
    print("=" * 68)
    print("\nNo comparta estos valores ni los suba al repositorio.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
