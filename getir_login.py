"""Log in to Getir once by hand; the Getir spider then keeps the session alive.

Needs GETIR_GSM in .env (your Getir account's mobile number, without the leading 0,
e.g. 5321234567) and GETIR_LAT and GETIR_LON of the delivery address whose stock and
prices should be scraped.

    venv\\Scripts\\python getir_login.py

Getir texts you a code; type it in. The session is saved to logs/getir_session.json.
Run it again only when the spider says the login has expired.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from marketScraper import getir_auth

ROOT = Path(__file__).resolve().parent
API = "https://getirx-client-api-gateway.getirapi.com"


def check_location(session, lat, lon):
    """Connects to the warehouse delivering to lat/lon, as the spider does."""
    response = session.get(
        f"{API}/main/parameters?countryCode=TR&lat={lat}&lon={lon}",
        headers={"Accept": "application/json", "x-language": "tr"},
    )
    data = response.json()
    if data["result"]["code"] == 0 and data["data"].get("isPublic") is False:
        print("Connected to the warehouse for GETIR_LAT/GETIR_LON; the spider will scrape its catalog.")
    else:
        print(f"Could not connect to a warehouse there: {data['result']}")


def main():
    load_dotenv(ROOT / ".env")
    gsm = (os.getenv("GETIR_GSM") or "").strip().lstrip("0")
    if not gsm:
        sys.exit("Set GETIR_GSM in .env first, e.g. GETIR_GSM=5321234567")

    session = getir_auth.new_session()
    session.get(getir_auth.SITE + "/")  # the cookies a browser has before logging in
    device_id = getir_auth.new_device_id()

    getir_auth.send_code(session, gsm)
    otp = input(f"Code Getir sent to {gsm[:3]}***{gsm[-2:]}: ").strip()
    verified = getir_auth.verify_code(session, gsm, otp)
    tokens = getir_auth.exchange_code(session, verified, device_id)
    getir_auth.save(session, device_id, tokens)

    print(f"Logged in, session saved to {getir_auth.SESSION_FILE}")
    print("token response fields:", sorted(tokens))
    print("cookies:", sorted({(c.name, c.domain) for c in session.cookies.jar}))

    # renew right away, so a broken refresh shows up now instead of in tonight's run
    tokens = getir_auth.refresh(session, device_id)
    getir_auth.save(session, device_id, tokens)
    print("Refresh works.")

    lat, lon = os.getenv("GETIR_LAT"), os.getenv("GETIR_LON")
    if lat and lon:
        check_location(session, lat, lon)
    else:
        print("Set GETIR_LAT and GETIR_LON in .env; the spider needs them.")


if __name__ == "__main__":
    main()
