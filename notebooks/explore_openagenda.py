"""Exploration of the OpenAgenda API (draft). 
The clean code is in scripts/."""
# %%
import requests, pandas as pd
from datetime import datetime, timedelta
def fetch_events(city: str, api_key: str) -> pd.DataFrame:
    base_url = 'https://api.openagenda.com/v2/events'
    one_year_ago = (datetime.now() - timedelta(days=365)).isoformat()
    all_events, after = [], None
    while True:
        params = {
            'key': api_key,
            'size': 100,
            'city[]': city,
            'after[timings.end]': one_year_ago,
            **(({'after': after}) if after else {})
        }
        resp = requests.get(base_url, params=params)
        data = resp.json()
        events = data.get('events', [])
        if not events: break
        all_events.extend(events)
        after = data.get('after') # Token de pagination
    return pd.DataFrame(all_events)


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

print(fetch_events("Toulouse", api_key))

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

# %% 13. Load the raw file and look at the candidate fields of one event
import json
from pathlib import Path

print("Current folder:", Path.cwd())          # to understand the relative path below

with open(Path("../data/raw/events.json"), encoding="utf-8") as f:
    raw_events = json.load(f)
print("Events loaded:", len(raw_events))

event = raw_events[0]
candidates = ["uid", "title", "description", "longDescription", "keywords",
              "dateRange", "firstTiming", "lastTiming", "location",
              "attendanceMode", "canonicalUrl", "status"]

for field in candidates:
    value = event.get(field)
    print(f"\n=== {field} ({type(value).__name__}) ===")
    print(str(value)[:300])                   # only the first 300 characters




# %% 14. All fields of the raw file: how often filled + one example
all_keys = set()
for event in raw_events:
    for key in event.keys():
        all_keys.add(key)                  # collect every field name seen

for key in sorted(all_keys):
    filled = 0
    example = None
    for event in raw_events:
        value = event.get(key)
        if value not in (None, "", [], {}):   # "filled" = not empty
            filled += 1
            if example is None:
                example = value
    print(f"{key:20} {filled:5}/{len(raw_events)}  {str(example)[:70]}")

# %% A. Get text: French first, otherwise any available language
def get_text(multilang):
    """Return the 'fr' text, else the first non-empty text, else ''."""
    if not multilang:
        return ""
    if multilang.get("fr"):
        return multilang["fr"]
    for value in multilang.values():
        if value:
            return value
    return ""

print(get_text({"fr": "Bonjour"}))           # -> Bonjour
print(get_text({"en": "Texte rangé en en"}))  # -> Texte rangé en en
print(repr(get_text(None)))                   # -> ''

get_text({"fr": "", "de" : "Hallo", "es": "Holà"})
# %% B. Is there Markdown in longDescription?
text = get_text(raw_events[0].get("longDescription"))
print(repr(text[:400]))     # repr shows the raw string, symbols included
# %% B bis. Clean Markdown 
import re

def clean_markdown(text):
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # [text](url) -> text
    text = re.sub(r"https?://\S+", "", text)               # bare URLs -> removed
    text = re.sub(r"[#*_>`]", "", text)                    # Markdown symbols
    text = re.sub(r"\s+", " ", text)                       # many spaces/lines -> one space
    return text.strip()

sample = "### Infos\n**Gratuit** ! Réservez [ici](https://exemple.fr) ou https://x.fr"
print("Text with Markdown to be removed: \n", sample)
print("\nCleaned text: \n", clean_markdown(sample))

# %% C. Flatten one raw event into one clean row
def flatten_event(event):
    location = event.get("location") or {}
    keywords = (event.get("keywords") or {}).get("fr") or []
    return {
        "uid": event.get("uid"),
        "title": get_text(event.get("title")),
        "description": get_text(event.get("description")),
        "long_description": clean_markdown(get_text(event.get("longDescription"))),
        "keywords": ", ".join(keywords),
        "date_range": get_text(event.get("dateRange")),
        "first_date": (event.get("firstTiming") or {}).get("begin"),
        "last_date": (event.get("lastTiming") or {}).get("end"),
        "location_name": location.get("name"),
        "address": location.get("address"),
        "city": location.get("city"),
        "url": event.get("canonicalUrl"),
    }

print("Text to flatten :", raw_events[0])
row = flatten_event(raw_events[0])
for key, value in row.items():
    print(f"{key:17}: {str(value)[:80]}")

# %% D. Clean all events, check quality, save
import pandas as pd

rows = []
for event in raw_events:
    rows.append(flatten_event(event))
df = pd.DataFrame(rows)

print("Rows              :", len(df))
print("Duplicate uids    :", df["uid"].duplicated().sum())
print("Empty title       :", (df["title"] == "").sum())
print("Empty long desc   :", (df["long_description"] == "").sum())
print("Cities            :", df["city"].value_counts().head(5).to_dict())

output = Path("../data/processed/events_clean.json")
output.parent.mkdir(parents=True, exist_ok=True)
df.to_json(output, orient="records", force_ascii=False, indent=2)
print("Saved to", output.resolve())

# %% E. Build one text per event (what the chatbot will search in)
def build_text(row):
    parts = [
        f"Titre : {row['title']}",
        f"Dates : {row['date_range']}",
        f"Lieu : {row['location_name']}, {row['address']}",
        f"Mots-clés : {row['keywords']}",
        f"Résumé : {row['description']}",
        f"Description : {row['long_description']}",
    ]
    return "\n".join(parts)

df["text"] = df.apply(build_text, axis=1)
print(df["text"].iloc[0][:500])
# %% F. How long are the texts? (to choose a chunk size)
lengths = df["text"].str.len()
print(lengths.describe().round())
print("Texts longer than 1000 chars:", (lengths > 1000).sum())

# %% G. Split long texts into chunks
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)

long_text = df.loc[lengths.idxmax(), "text"]      # the longest event
chunks = splitter.split_text(long_text)
print("Number of chunks:", len(chunks))
print("\n--- Chunk 2 ---\n", chunks[1][:300])

# %% Test the Mistral key
import os
from dotenv import load_dotenv
from mistralai.client import Mistral

load_dotenv(override=True)                 # reload .env (the file changed)
client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))

response = client.chat.complete(
    model="mistral-small-2603",
    messages=[{"role": "user", "content": "Dis bonjour en une phrase."}],
)
print(response.choices[0].message.content)
# %% H. Split only the description, then put the header back on every chunk
def build_header(row):
    return (f"Titre : {row['title']}\n"
            f"Dates : {row['date_range']}\n"
            f"Lieu : {row['location_name']}, {row['address']}\n"
            f"Mots-clés : {row['keywords']}")

row = df.loc[lengths.idxmax()]               # the same longest event as in G
print(build_header(row))

def build_chunks(row):
    header = build_header(row)
    body = f"Résumé : {row['description']}\nDescription : {row['long_description']}"
    pieces = splitter.split_text(body)       # split ONLY the body
    chunks = []
    for piece in pieces:
        chunks.append(header + "\n" + piece) # glue the header in front of each piece
    return chunks

chunks = build_chunks(row)
print("Number of chunks:", len(chunks))
print("\n--- Chunk 2 ---\n", chunks[1][:400])
# %% I. Overlap demo
from langchain_text_splitters import RecursiveCharacterTextSplitter
text = "Concert de jazz au Sunset. Entrée gratuite pour les moins de 26 ans, sur réservation."
for overlap in [0, 20]:
    demo = RecursiveCharacterTextSplitter(chunk_size=40, chunk_overlap=overlap)
    print(f"overlap={overlap}:", demo.split_text(text))
# %% J. See embeddings: similar meanings -> high score
from langchain_huggingface import HuggingFaceEmbeddings

emb = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-small",
                            encode_kwargs={"normalize_embeddings": True})
sentences = ["concert de jazz", "soirée de musique improvisée", "atelier de poterie"]
vectors = emb.embed_documents(sentences)          # 3 texts -> 3 vectors
print("Vector size:", len(vectors[0]))            # each vector = 384 numbers
print("First 5 numbers:", [round(x, 3) for x in vectors[0][:5]])
for i in range(1, 3):
    similarity = sum(a * b for a, b in zip(vectors[0], vectors[i]))   # dot product
    print(f"'{sentences[0]}' vs '{sentences[i]}': {similarity:.2f}")

# %% K. Inside the model (model card code, with French examples)
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel

def average_pool(last_hidden_states, attention_mask):
    # one vector per token -> average them -> one vector per text (ignore padding)
    last_hidden = last_hidden_states.masked_fill(~attention_mask[..., None].bool(), 0.0)
    return last_hidden.sum(dim=1) / attention_mask.sum(dim=1)[..., None]

input_texts = [
    "query: concert de jazz",                               # the question
    "passage: Soirée de musique improvisée au Sunset.",     # a text to search in
    "passage: Atelier de poterie pour enfants.",            # another text
]
tokenizer = AutoTokenizer.from_pretrained("intfloat/multilingual-e5-small")
model = AutoModel.from_pretrained("intfloat/multilingual-e5-small")

batch = tokenizer(input_texts, max_length=512, padding=True, truncation=True, return_tensors="pt")
print("Tokens of text 0:", tokenizer.convert_ids_to_tokens(batch["input_ids"][0]))

outputs = model(**batch)
vecs = F.normalize(average_pool(outputs.last_hidden_state, batch["attention_mask"]), p=2, dim=1)
print("Shape:", tuple(vecs.shape))                          # (3 texts, 384 numbers)
print("Question vs passages:", ((vecs[:1] @ vecs[1:].T) * 100).tolist())

# %% L. Same thing in 3 lines with sentence-transformers
from sentence_transformers import SentenceTransformer

st_model = SentenceTransformer("intfloat/multilingual-e5-small")
st_vecs = st_model.encode(input_texts, normalize_embeddings=True)
print("Shape:", st_vecs.shape)
print("Question vs passages:", (st_vecs[:1] @ st_vecs[1:].T * 100).round(1))

# %% 16. Embedding model, with the e5 prefixes (same as build_index.py)
embeddings = HuggingFaceEmbeddings(
    model_name="intfloat/multilingual-e5-small",
    encode_kwargs={"normalize_embeddings": True, "prompt": "passage: "},
    query_encode_kwargs={"normalize_embeddings": True, "prompt": "query: "},
)
print("Vector size:", len(embeddings.embed_query("concert de jazz")))

# %% 17. Load our chunks and turn 100 of them into LangChain Documents
import json
from langchain_core.documents import Document

with open("../data/processed/chunks.json", encoding="utf-8") as f:
    chunks = json.load(f)

documents = [Document(page_content=c["text"], metadata=c["metadata"]) for c in chunks[:100]]
print(len(documents), "documents")
print(documents[0].page_content[:200])
print(documents[0].metadata)

# %% 18. Tiny demo: FAISS on 3 sentences (demo_ names: do not overwrite ours)
from langchain_community.vectorstores import FAISS

demo_docs = [
    Document(page_content="Concert de jazz au Sunset", metadata={"source": "demo1"}),
    Document(page_content="Atelier de poterie pour enfants", metadata={"source": "demo2"}),
    Document(page_content="Hello, world!", metadata={"source": "demo3"}),
]
demo_store = FAISS.from_documents(demo_docs, embeddings)
for doc, score in demo_store.similarity_search_with_score("soirée musicale", k=3):
    print(f"{score:.3f} | {doc.page_content}")

# %% 19. Build a test index on our 100 documents and save it
vectorstore = FAISS.from_documents(documents, embeddings)
vectorstore.save_local("../faiss_index_test")
print("Vectors in index:", vectorstore.index.ntotal)
print("Index type:", type(vectorstore.index).__name__)

# %% 20. Reload the saved index (no recomputation)
vectorstore = FAISS.load_local("../faiss_index_test", embeddings,
                               allow_dangerous_deserialization=True)
print("Reloaded vectors:", vectorstore.index.ntotal)

# %% 21. Search: the 3 closest chunks to a question
results = vectorstore.similarity_search_with_score("concert de jazz", k=3)
for doc, score in results:
    print(f"{score:.3f} | {doc.metadata['title']}")
# %% Open the saved index and look inside
import sys
sys.path.append("..")                    # so the notebook can import scripts/
import numpy as np
from scripts.build_index import load_index

vs = load_index()                        # reads index.faiss + index.pkl

# 1. index.faiss: the vectors
print(vs.index.ntotal, vs.index.d)       # how many vectors, size of each
print(vs.index.reconstruct(0)[:5])       # first 5 numbers of vector n°0

# 2. index.pkl: position -> id -> Document
first_id = vs.index_to_docstore_id[0]
doc = vs.docstore.search(first_id)
print(first_id)
print(doc.page_content[:200])
print(doc.metadata)

# %% Search by hand: exactly what similarity_search does for us
q = vs.embeddings.embed_query("concert de jazz")                  # 1. question -> vector
distances, positions = vs.index.search(np.array([q], dtype="float32"), 3)  # 2. FAISS: 3 closest positions
print(distances, positions)
for p in positions[0]:
    doc = vs.docstore.search(vs.index_to_docstore_id[p])         # 3. position -> id -> Document
    print(doc.metadata["title"])

# %% The same thing, with LangChain, in one line
for doc, score in vs.similarity_search_with_score("concert de jazz", k=3):
    print(f"{score:.3f} | {doc.metadata['title']}")

# %% 
from langchain_ollama import ChatOllama

llm = ChatOllama(model="mistral", temperature=0.9)
response = llm.invoke("Dis bonjour en une phrase.")
print(response.content)

# %% Chunk statistics
import json
import pandas as pd

with open("../data/processed/chunks.json", encoding="utf-8") as f:
    chunks = json.load(f)

meta = pd.DataFrame([c["metadata"] for c in chunks])   # one row per chunk, one column per metadata
counts = meta["uid"].value_counts()                     # uid -> how many chunks
print("Chunks              :", len(meta))
print("Events              :", counts.size)
print("Events with 1 chunk :", (counts == 1).sum())
print("Max chunks per event:", counts.max())

# %% Compare the 3 retrieval versions
import sys
sys.path.append("..")
from datetime import date
from scripts.build_index import load_index

vectorstore = load_index()
today = date.today().isoformat()
question = "Je cherche un concert de jazz."

print("== V1: 5 closest chunks")
for doc in vectorstore.similarity_search(question, k=5):
    print(" ", doc.metadata["last_date"][:10], doc.metadata["title"])

print("== V2: + only events not finished")
for doc in vectorstore.similarity_search(question, k=5, fetch_k=50,
                                         filter=lambda m: m["last_date"][:10] >= today):
    print(" ", doc.metadata["last_date"][:10], doc.metadata["title"])
# %%
