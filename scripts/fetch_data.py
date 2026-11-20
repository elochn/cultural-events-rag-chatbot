"""Fetch cultural events from the OpenAgenda API and save the raw data.

Usage (from the project root):
    python scripts/fetch_data.py
"""
#%%
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_URL = "https://api.openagenda.com/v2"
AGENDA_UID = 56500817   # "OpenAgenda en Ile-de-France"
CITY = "Paris"
PAGE_SIZE = 100
MAX_PAGES = 50         # safety limit: 50 x 100 = 5000 events max
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = PROJECT_ROOT / "data" / "raw" / "events.json"


def fetch_events(api_key, agenda_uid=AGENDA_UID, city=CITY, days_back=365):
    """Return all events of an agenda, filtered by city and date."""
    since = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    params = {"size": PAGE_SIZE, "city[]": city, "timings[gte]": since, "detailed":1}

    all_events = []
    after = None
    for page in range(1, MAX_PAGES + 1):
        if after:
            params["after[]"] = after

        resp = requests.get(
            f"{BASE_URL}/agendas/{agenda_uid}/events",
            headers={"key": api_key},
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        events = data.get("events", [])
        print(f"Page {page}: {len(events)} events")
        if not events:
            break
        all_events.extend(events)

        after = data.get("after")
        if not after:
            break
        time.sleep(0.2)

    return all_events


def save_events(events, path=OUTPUT_PATH):
    """Save the raw events to a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)


def main():
    load_dotenv()
    api_key = os.getenv("OPENAGENDA_API_KEY")
    if not api_key:
        raise SystemExit("OPENAGENDA_API_KEY is missing. Add it to your .env file.")

    events = fetch_events(api_key)

    uids = [event["uid"] for event in events]
    print(f"\nCollected {len(events)} events ({len(set(uids))} unique)")

    save_events(events)
    print(f"Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
# %%
