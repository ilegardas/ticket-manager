"""Envío de correos vía Resend usando la integración de Replit Connectors.

Las credenciales (api_key y from_email) se obtienen en tiempo de ejecución desde
el proxy de Replit Connectors (connector: "resend"), por lo que no se almacenan
como secretos en el entorno. Esto replica lo que hace el SDK oficial
(@replit/connectors-sdk / replit-connectors), que aquí no está disponible para
Python, mediante una llamada HTTP autenticada con el token de identidad del repl.
"""

import json
import os
import time
import urllib.error
import urllib.request

_CACHE_TTL = 300
_cache = {"settings": None, "fetched_at": 0.0}


class ResendError(Exception):
    """Error al obtener credenciales o al enviar correo con Resend."""


def _identity_token():
    ident = os.environ.get("REPL_IDENTITY")
    if ident:
        return "repl " + ident
    renew = os.environ.get("WEB_REPL_RENEWAL")
    if renew:
        return "depl " + renew
    raise ResendError(
        "No hay token de identidad del repl (REPL_IDENTITY / WEB_REPL_RENEWAL)."
    )


def _get_connection_settings(force_refresh=False):
    now = time.time()
    if (
        not force_refresh
        and _cache["settings"]
        and (now - _cache["fetched_at"]) < _CACHE_TTL
    ):
        return _cache["settings"]

    hostname = os.environ.get("REPLIT_CONNECTORS_HOSTNAME")
    if not hostname:
        raise ResendError("REPLIT_CONNECTORS_HOSTNAME no está configurado.")

    url = (
        f"https://{hostname}/api/v2/connection"
        "?include_secrets=true&connector_names=resend"
    )
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "X_REPLIT_TOKEN": _identity_token()},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "ignore")
        raise ResendError(
            f"No se pudieron obtener las credenciales de Resend ({exc.code}): {detail}"
        )
    except urllib.error.URLError as exc:
        raise ResendError(f"No se pudo contactar el proxy de conectores: {exc.reason}")

    items = data.get("items", [])
    if not items:
        raise ResendError("No hay una conexión de Resend configurada.")

    settings = items[0].get("settings", {}) or {}
    api_key = settings.get("api_key")
    if not api_key:
        raise ResendError("La conexión de Resend no incluye api_key.")

    result = {"api_key": api_key, "from_email": settings.get("from_email")}
    _cache["settings"] = result
    _cache["fetched_at"] = now
    return result


def send_email(to, subject, text, html=None, from_email=None):
    """Envía un correo con Resend. Devuelve la respuesta JSON de la API.

    `to` puede ser un string o una lista de destinatarios.
    Lanza ResendError si falla la obtención de credenciales o el envío.
    """
    settings = _get_connection_settings()
    sender = from_email or settings.get("from_email")
    if not sender:
        raise ResendError("No hay remitente (from_email) configurado en Resend.")

    recipients = list(to) if isinstance(to, (list, tuple)) else [to]
    payload = {"from": sender, "to": recipients, "subject": subject, "text": text}
    if html:
        payload["html"] = html

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + settings["api_key"],
            "Content-Type": "application/json",
            "User-Agent": "SEECH-Tickets/1.0 (+https://seech.gob.mx)",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "ignore")
        raise ResendError(f"Resend respondió {exc.code}: {detail}")
    except urllib.error.URLError as exc:
        raise ResendError(f"No se pudo contactar la API de Resend: {exc.reason}")
