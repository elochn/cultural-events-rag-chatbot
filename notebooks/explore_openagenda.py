"""Exploration of the OpenAgenda API (draft). 
The clean code is in scripts/."""

# %% 1. Load the API key from .env
import json
import os

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAGENDA_API_KEY")

BASE_URL = "https://api.openagenda.com/v2"

print("API key loaded:", api_key is not None)

# %% 2. First call: search agendas, look at the raw response
resp = requests.get(
    f"{BASE_URL}/agendas",
    params={"key": api_key, "search": "Paris", "size": 5},
)
data = resp.json()

print("HTTP status :", resp.status_code)
print("Type        :", type(data))
print("Top-level keys:", list(data.keys()))

# %% 3. List the agendas found
agendas = data.get("agendas", [])
print("Number of agendas returned:", len(agendas))
print()

for agenda in agendas:
    print(agenda.get("uid"), "|", agenda.get("title"))

# %% 4. Fetch ONE event from the chosen agenda and inspect it
AGENDA_UID = 56500817  # <- we can replace with any UID
one_year_ago = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

resp = requests.get(
    f"{BASE_URL}/agendas/{AGENDA_UID}/events",
    params={"key": api_key, "size": 3, "timings[gte]": one_year_ago, "city[]": "Paris"},
)
data = resp.json()

print("HTTP status   :", resp.status_code)
print("Top-level keys:", list(data.keys()))
print("Total events in this agenda:", data.get("total"))
print()

event = data["events"][0]
print("Fields of one event:", list(event.keys()))
print()
print(json.dumps(event, indent=2, ensure_ascii=False)[:2000])

# %% 4 Bis. Total Number of events 
AGENDA_UID = 56500817  # <- replace with any UID
one_year_ago = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

resp = requests.get(
    f"{BASE_URL}/agendas/{AGENDA_UID}/events",
    params={"key": api_key, "size": 10, "timings[gte]": one_year_ago, "city[]": "Paris"},
)
data = resp.json()

list(data.keys())

data['total']
data['after']
data['sort']

df = pd.DataFrame(data.get("AGENDA_UID", []))

# %% 5. Fetch one page of events into a DataFrame
resp = requests.get(
    f"{BASE_URL}/agendas/{AGENDA_UID}/events",
    params={"key": api_key, "size": 20},
)
data = resp.json()

df = pd.DataFrame(data.get("events", []))

print("Shape (rows, columns):", df.shape)
print("Columns:", list(df.columns))
print("Pagination token 'after':", data.get("after"))
df.head()

# %% Step 1 - Find the official agendas for each candidate
CANDIDATES = ["Ville de Paris", "Seine-Saint-Denis", "Ile-de-France"]

for ville in CANDIDATES:
    resp = requests.get(
        f"{BASE_URL}/agendas",                           # search AGENDAS
        headers={"key": api_key},
        params={"size": 10, "official": 1, "search": ville},
    )
    data = resp.json()

    print(f"=== {ville} (status {resp.status_code}) ===")
    for agenda in data.get("agendas", []):
        print(f"   {agenda.get('uid')} | {agenda.get('title')}")
    print()

# %% Step 2 - Compare the volume of candidate agendas
CANDIDATES = {
    "OpenAgenda en IDF": 56500817,
    "Theatre de la Ville": 52278336,
    "DRAC IDF musique": 73237661,
    "MAAD 93": 54046098,
}

for name, uid in CANDIDATES.items():
    resp = requests.get(
        f"{BASE_URL}/agendas/{uid}/events",
        headers={"key": api_key},
        params={"size": 1},
    )
    data = resp.json()
    print(f"{name:22} | status {resp.status_code} | total events: {data.get('total')}")
# %% Check filters: does the total change?
from datetime import datetime, timedelta

UID = 56500817  # "OpenAgenda en IDF"
one_year_ago = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

tests = {
    "no filter":          {},
    "last year + future": {"timings[gte]": one_year_ago},
    "city = Paris":       {"city[]": "Paris"},
    "both":               {"timings[gte]": one_year_ago, "city[]": "Paris"},
}

for label, filters in tests.items():
    resp = requests.get(
        f"{BASE_URL}/agendas/{UID}/events",
        headers={"key": api_key},
        params={"size": 1, **filters},
    )
    print(f"{label:20} | status {resp.status_code} | total: {resp.json().get('total')}")
# %% 7 Pagination avec filters
from datetime import datetime, timedelta

# FILTERS = Paris + depuis un an
one_year_ago = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
FILTERS = {"city[]": "Paris", "timings[gte]": one_year_ago}

all_events = []
after = None
for page in range(1, 30):
    params = {"size": 100, **FILTERS} # FILTERS = Paris + depuis un an
    if after:
        params["after[]"] = after
    data = requests.get(
        f"{BASE_URL}/agendas/{AGENDA_UID}/events",
        headers={"key": api_key},
        params=params,
    ).json()

    events = data.get("events", [])
    print(f"Page {page}: {len(events)} events")
    if not events:
        break
    all_events.extend(events)

    after = data.get("after")
    if not after:
        break

uids = [event["uid"] for event in all_events]
print("\nCollected:", len(all_events), "| unique:", len(set(uids)))
# %% 8. Show events in a human-friendly way
def show_event(event):
    location = event.get("location") or {}
    print("TITLE      :", (event.get("title") or {}).get("fr"))
    print("DESCRIPTION:", (event.get("description") or {}).get("fr"))
    print("DATES      :", (event.get("dateRange") or {}).get("fr"))
    print("PLACE      :", location.get("name"), "|", location.get("address"))
    print("KEYWORDS   :", (event.get("keywords") or {}).get("fr"))
    print("MODE       :", event.get("attendanceMode"))
    print("SOURCE     :", (event.get("originAgenda") or {}).get("title"))
    print("-" * 70)

for event in all_events[:5]:
    show_event(event)
# %% 9. Does 'detailed=1' give more text?
for detailed in [0, 1]:
    data = requests.get(
        f"{BASE_URL}/agendas/{AGENDA_UID}/events",
        headers={"key": api_key},
        params={"size": 1, **FILTERS, "detailed": detailed},
    ).json()
    event = data["events"][0]
    long_desc = (event.get("longDescription") or {}).get("fr") or ""
    print(f"detailed={detailed} | {len(event)} fields | longDescription: {len(long_desc)} characters")
# %%10. Data quality overview
from collections import Counter

total = len(all_events)
no_description = sum(1 for e in all_events if not (e.get("description") or {}).get("fr"))
modes = Counter(e.get("attendanceMode") for e in all_events)

print("Total events          :", total)
print("Without description   :", no_description)
print("attendanceMode values :", dict(modes))

# %% 9b. What does a longDescription look like?
print(long_desc[:1500])

# %% 10b. Events with a description in another language but not in French
other_lang_only = [
    e for e in all_events
    if not (e.get("description") or {}).get("fr") and e.get("description")
]
print("No FR but another language:", len(other_lang_only))
for e in other_lang_only[:]:
    print("  languages available:", list(e["description"].keys()))
# %% 10b.BIS Events without a French description, but with another language
other_lang_only = []                               # empty list to fill

for event in all_events:                           # look at each event, one by one
    description = event.get("description") or {}   # the description dict, or {} if missing
    has_french = bool(description.get("fr"))       # is there a non-empty "fr" text?
    has_other = len(description) > 0               # is there at least one language?

    if not has_french and has_other:               # no French, but something else
        other_lang_only.append(event)              # keep this event aside

print("Events without FR but with another language:", len(other_lang_only))

for event in other_lang_only[:3]:                  # show the first 3
    description = event["description"]
    print("Languages:", list(description.keys()))
    print("Text     :", list(description.values())[0][:150])
    print("-" * 60)


# %% Understanding 'after' (cursor pagination)
params = {"size": 2, "official": 1}

# Page 1: no cursor
data1 = requests.get(f"{BASE_URL}/agendas", headers={"key": api_key}, params=params).json()
print("Page 1:", [a["uid"] for a in data1["agendas"]], "| after =", data1["after"])

# Page 2: give back the cursor from page 1
data2 = requests.get(f"{BASE_URL}/agendas", headers={"key": api_key},
                     params={**params, "after[]": data1["after"]}).json()
print("Page 2:", [a["uid"] for a in data2["agendas"]], "| after =", data2["after"])
# %% A. First page: look at the bookmark we receive
params = {"size": 3, **FILTERS}          # only 3 events, to keep it readable
data = requests.get(f"{BASE_URL}/agendas/{AGENDA_UID}/events",
                    headers={"key": api_key}, params=params).json()

for event in data["events"]:
    print("\nPage 1 ->", event["uid"], (event.get("title") or {}).get("fr"))
    bookmark = data.get("after")
    print("Bookmark received (after):", bookmark)

# %% B. Second page: give the bookmark back
params = {"size": 3, **FILTERS, "after[]": bookmark}
data = requests.get(f"{BASE_URL}/agendas/{AGENDA_UID}/events",
                    headers={"key": api_key}, params=params).json()

for event in data["events"]:
    print("Page 2 ->", event["uid"], (event.get("title") or {}).get("fr"))

print("\nNew bookmark:", data.get("after"))

# %% C. What if we forget the bookmark?
params = {"size": 3, **FILTERS}          # no "after[]"
data = requests.get(f"{BASE_URL}/agendas/{AGENDA_UID}/events",
                    headers={"key": api_key}, params=params).json()

for event in data["events"]:
    print("No bookmark ->", event["uid"], (event.get("title") or {}).get("fr"))
# %% D. Where is the bookmark?
print("Keys of the response:", list(data.keys()))
print("Number of events in this page:", len(data["events"]))
print("Bookmark:", data["after"])
# %% E. What does .get(key, default) do?
fake_error_response = {"success": False, "message": "forbidden"}
print(fake_error_response.get("events", []))   # -> []  (no crash)
print(fake_error_response.get("events"))       # -> None
# print(fake_error_response["events"])         # -> KeyError (uncomment to see)

# %% F. What is inside the response envelope (everything except the events)?
for key in data.keys():
    if key == "events":
        print(f"{key:10} | {type(data[key]).__name__:6} | {len(data[key])} events (skipped)")
    else:
        print(f"{key:10} | {type(data[key]).__name__:6} | {data[key]}")
# %%12. Load the saved raw data (no more API calls)
import json
from pathlib import Path

with open(Path("../data/raw/events.json"), encoding="utf-8") as f:
    raw_events = json.load(f)

print("Events loaded:", len(raw_events))
print("'longDescription' in first event:", "longDescription" in raw_events[0])