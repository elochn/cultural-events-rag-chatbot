"""Clean the raw OpenAgenda events and split them into chunks for the vector index.

Input : data/raw/events.json              (created by scripts/fetch_data.py)
Output: data/processed/events_clean.json  (one clean row per event)
        data/processed/chunks.json        (text chunks + metadata, for build_index.py)

Usage (from the project root):
    python scripts/preprocess.py
"""
import json
import re
from pathlib import Path

import pandas as pd
from langchain_text_splitters import RecursiveCharacterTextSplitter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "events.json"
CLEAN_PATH = PROJECT_ROOT / "data" / "processed" / "events_clean.json"
CHUNKS_PATH = PROJECT_ROOT / "data" / "processed" / "chunks.json"

CHUNK_SIZE = 1000      # max characters of description per chunk
CHUNK_OVERLAP = 150    # characters repeated between two consecutive chunks

# Codes documented in https://developers.openagenda.com/en/evenements/structure
ATTENDANCE_MODES = {1: "Sur place", 2: "En ligne", 3: "Sur place et en ligne"}
STATUSES = {
    1: "Programmé",
    2: "Reprogrammé",
    3: "Déplacé en ligne",
    4: "Reporté (nouvelles dates à venir)",
    5: "Complet",
    6: "Annulé",
}


# ---------- 1. Small cleaning helpers ----------

def get_text(multilang):
    """Return the 'fr' value, else the first non-empty value, else ''.

    The language key is not reliable (French text was found under 'en').
    """
    if not multilang:
        return ""
    if multilang.get("fr"):
        return multilang["fr"]
    for value in multilang.values():
        if value:
            return value
    return ""


def clean_markdown(text):
    """Remove Markdown: keep link text, drop URLs, symbols and extra spaces."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # [text](url) -> text
    text = re.sub(r"https?://\S+", "", text)               # bare URLs -> removed
    text = re.sub(r"[#*_>`]", "", text)                    # Markdown symbols
    text = re.sub(r"\s+", " ", text)                       # many spaces/lines -> one
    return text.strip()


def format_age(age):
    """Turn {'min': 6, 'max': 12} into '6 - 12 ans' ('' if unknown)."""
    age = age or {}
    low = age.get("min")
    high = age.get("max")
    if low is None and high is None:
        return ""
    if high is None:
        return f"à partir de {low} ans"
    if low is None:
        return f"jusqu'à {high} ans"
    return f"{low} - {high} ans"


# ---------- 2. One raw event -> one clean row ----------

def flatten_event(event):
    """Keep only the fields useful to answer a user, as simple text values."""
    location = event.get("location") or {}
    keywords = get_text(event.get("keywords")) or []
    registration = []
    for item in event.get("registration") or []:
        if item.get("value"):
            registration.append(str(item["value"]))

    return {
        "uid": event.get("uid"),
        "title": get_text(event.get("title")),
        "description": get_text(event.get("description")),
        "long_description": clean_markdown(get_text(event.get("longDescription"))),
        "keywords": ", ".join(keywords),
        "conditions": get_text(event.get("conditions")),
        "age": format_age(event.get("age")),
        "attendance_mode": ATTENDANCE_MODES.get(event.get("attendanceMode"), ""),
        "status": STATUSES.get(event.get("status"), ""),
        "date_range": get_text(event.get("dateRange")),
        "first_date": (event.get("firstTiming") or {}).get("begin"),
        "last_date": (event.get("lastTiming") or {}).get("end"),
        "location_name": location.get("name") or "",
        "address": location.get("address") or "",
        "city": location.get("city") or "",
        "access": get_text(location.get("access")),
        "url": event.get("canonicalUrl"),
        "registration": ", ".join(registration),
    }


# ---------- 3. One clean row -> several chunks ----------

def build_header(row):
    """Practical info repeated at the top of every chunk (empty lines skipped)."""
    fields = [
        ("Titre", row["title"]),
        ("Dates", row["date_range"]),
        ("Lieu", f"{row['location_name']}, {row['address']}".strip(", ")),
        ("Format", row["attendance_mode"]),
        ("Statut", row["status"]),
        ("Tarif / conditions", row["conditions"]),
        ("Âge", row["age"]),
        ("Accès", row["access"]),
        ("Mots-clés", row["keywords"]),
    ]
    lines = []
    for label, value in fields:
        if value:
            lines.append(f"{label} : {value}")
    return "\n".join(lines)


def build_chunks(row, splitter):
    """Split only the description, then glue the header on every piece."""
    header = build_header(row)
    body = f"Résumé : {row['description']}\nDescription : {row['long_description']}"
    pieces = splitter.split_text(body)

    chunks = []
    for index, piece in enumerate(pieces):
        chunks.append({
            "text": header + "\n" + piece,
            "metadata": {
                "uid": row["uid"],
                "title": row["title"],
                "date_range": row["date_range"],
                "first_date": row["first_date"],
                "last_date": row["last_date"],
                "location_name": row["location_name"],
                "city": row["city"],
                "url": row["url"],
                "chunk_index": index,
            },
        })
    return chunks


# ---------- 4. Main pipeline ----------

def main():
    with open(RAW_PATH, encoding="utf-8") as f:
        raw_events = json.load(f)
    print(f"Raw events loaded      : {len(raw_events)}")

    # Clean
    rows = []
    for event in raw_events:
        rows.append(flatten_event(event))
    df = pd.DataFrame(rows)

    # Quality report (numbers for the technical report)
    print(f"Duplicate uids         : {df['uid'].duplicated().sum()}")
    print(f"Empty title            : {(df['title'] == '').sum()}")
    print(f"Empty long description : {(df['long_description'] == '').sum()}")
    print(f"With price/conditions  : {(df['conditions'] != '').sum()}")
    print(f"Statuses               : {df['status'].value_counts().to_dict()}")
    df = df.drop_duplicates(subset="uid")

    CLEAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_json(CLEAN_PATH, orient="records", force_ascii=False, indent=2)
    print(f"Clean events saved     : {len(df)} -> {CLEAN_PATH}")

    # Chunk
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE,
                                              chunk_overlap=CHUNK_OVERLAP)
    all_chunks = []
    for _, row in df.iterrows():
        all_chunks.extend(build_chunks(row, splitter))

    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)
    print(f"Chunks saved           : {len(all_chunks)} -> {CHUNKS_PATH}")


if __name__ == "__main__":
    main()