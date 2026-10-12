"""Getir login, so the spider sees one warehouse's real stock and prices.

Without a login Getir only serves its public catalog, where every product is "in stock"
and products no warehouse sells any more keep their old price. Logging in needs a code
Getir sends by SMS, so it is done once by hand with getir_login.py; after that the saved
refresh token renews the session without another SMS.

The flow is the one getir.com's own JavaScript uses (OIDC, found in its bundle).
"""

import json
import uuid
from pathlib import Path

from curl_cffi import requests

SITE = "https://getir.com"
AUTH_GATEWAY = "https://getir-auth-api-gateway.getirapi.com"
CLIENT_ID = "getir-web-app"
# in logs/ because that folder is gitignored and mounted into the scraper container
SESSION_FILE = Path(__file__).resolve().parent.parent / "logs" / "getir_session.json"


class GetirLoginRequired(Exception):
    """The saved session is missing or Getir no longer accepts it: run getir_login.py."""


def device_headers(device_id):
    # getir.com sends these with every token request
    return {
        "device-id": device_id,
        "device-os": "web",
        "device-model": "Web",
        "device-name": "Web",
        "device-manufacturer": "Web",
        "device-version": "1.0",
        "language": "tr",
    }


def new_session():
    session = requests.Session(impersonate="chrome")
    session.headers.update({"Origin": SITE, "Referer": SITE + "/"})
    return session


def post_json(session, url, body):
    response = session.post(url, json=body)
    data = response.json() if response.content else {}
    if not response.ok:
        raise RuntimeError(f"{url} answered {response.status_code}: {data}")
    return data


def send_code(session, gsm):
    """Getir texts a login code to the number (Turkish mobile, without the leading 0)."""
    return post_json(session, f"{SITE}/api/auth/start/", {"gsm_country_code": "90", "gsm": gsm})


def verify_code(session, gsm, otp):
    """Trades the SMS code for an authorization code, which exchange_code() turns into tokens."""
    data = post_json(
        session, f"{SITE}/api/auth/verify/", {"gsm_country_code": "90", "gsm": gsm, "otp": otp}
    )
    if data.get("registration_required"):
        raise RuntimeError("This number has no Getir account; register it in the Getir app first.")
    return data


def exchange_code(session, verified, device_id):
    response = session.post(
        verified["token_endpoint"],
        data={
            "grant_type": "authorization_code",
            "code": verified["code"],
            "redirect_uri": verified["redirect_uri"],
            "client_id": verified["client_id"],
            "code_verifier": verified["code_verifier"],
        },
        headers=device_headers(device_id),
    )
    if not response.ok:
        raise RuntimeError(f"Token exchange answered {response.status_code}: {response.text[:300]}")
    return response.json()


def refresh(session, device_id):
    """Renews the tokens with the refresh token cookie; no SMS needed."""
    response = session.post(
        f"{AUTH_GATEWAY}/v1/token",
        data={"grant_type": "refresh_token", "client_id": CLIENT_ID},
        headers=device_headers(device_id),
    )
    if 400 <= response.status_code < 500 and response.status_code not in (408, 425, 429):
        raise GetirLoginRequired(f"Getir refused the refresh token ({response.status_code})")
    response.raise_for_status()
    return response.json()


def save(session, device_id, tokens):
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    cookies = [
        {"name": c.name, "value": c.value, "domain": c.domain, "path": c.path}
        for c in session.cookies.jar
    ]
    SESSION_FILE.write_text(
        json.dumps({"device_id": device_id, "cookies": cookies, "tokens": tokens}, indent=2),
        encoding="utf-8",
    )


def load():
    """The saved session and its device id, refreshed so it is good for this run."""
    if not SESSION_FILE.exists():
        raise GetirLoginRequired(f"{SESSION_FILE} is missing")
    saved = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    session = new_session()
    for c in saved["cookies"]:
        session.cookies.set(c["name"], c["value"], domain=c["domain"], path=c["path"])
    tokens = refresh(session, saved["device_id"])
    save(session, saved["device_id"], tokens)
    return session, saved["device_id"], tokens


def new_device_id():
    return str(uuid.uuid4())
