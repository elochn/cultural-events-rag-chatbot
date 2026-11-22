import json
from datetime import datetime, timedelta

import pytest

from scripts.preprocess import (CHUNKS_PATH, CLEAN_PATH, clean_markdown,
                                format_age, get_text)


# ---------- Helper functions ----------
def test_get_text_prefers_french():
    assert get_text({"en": "Hello", "fr": "Bonjour"}) == "Bonjour"


def test_get_text_falls_back_to_other_language():
    assert get_text({"en": "Texte rangé sous en"}) == "Texte rangé sous en"


def test_get_text_handles_missing_value():
    assert get_text(None) == ""


def test_clean_markdown_removes_links_and_symbols():
    clean = clean_markdown("### Infos\n**Gratuit** ! Réservez [ici](https://x.fr)")
    assert "http" not in clean
    assert "#" not in clean and "*" not in clean
    assert "Gratuit" in clean and "ici" in clean


def test_format_age():
    assert format_age({"min": 6, "max": 12}) == "6 - 12 ans"
    assert format_age({"min": None, "max": None}) == ""


# ---------- Processed data ----------

@pytest.fixture
def clean_events():
    if not CLEAN_PATH.exists():
        pytest.skip("Run scripts/preprocess.py first")
    with open(CLEAN_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def chunks():
    if not CHUNKS_PATH.exists():
        pytest.skip("Run scripts/preprocess.py first")
    with open(CHUNKS_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_at_least_one_event(clean_events):
    assert len(clean_events) > 0


def test_no_duplicate_events(clean_events):
    uids = [event["uid"] for event in clean_events]
    assert len(uids) == len(set(uids))


def test_every_event_has_a_title(clean_events):
    for event in clean_events:
        assert event["title"] != ""


def test_events_are_in_paris(clean_events):
    for event in clean_events:
        assert "paris" in event["city"].lower()


def test_events_are_recent(clean_events):
    # small margin: the data was fetched a few days before the test runs
    limit = (datetime.now() - timedelta(days=370)).strftime("%Y-%m-%d")
    for event in clean_events:
        assert event["last_date"][:10] >= limit


def test_every_chunk_has_header_and_metadata(chunks):
    for chunk in chunks:
        assert chunk["text"].startswith("Titre :")
        assert chunk["metadata"]["uid"]
        assert chunk["metadata"]["url"]


def test_every_event_is_chunked(clean_events, chunks):
    event_uids = set(event["uid"] for event in clean_events)
    chunk_uids = set(chunk["metadata"]["uid"] for chunk in chunks)
    assert event_uids == chunk_uids
