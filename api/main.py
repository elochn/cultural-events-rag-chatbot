"""REST API exposing the RAG engine.

Run (from the project root):
    uvicorn api.main:app --reload
Docs: http://127.0.0.1:8000/docs
"""
import os
import secrets
import rag.engine as engine

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from scripts import build_index, fetch_data, preprocess

load_dotenv()
app = FastAPI(title="Puls-Events RAG API")

class Question(BaseModel):
    # min_length=1: an empty question is refused with a 422 error
    # the JSON body must contain a "question" text
    question: str = Field(min_length=1, max_length=500, 
                          examples=["Quels concerts de jazz à Paris cette semaine ?"])


@app.get("/health")
def health():
    """Check that the API is running."""
    return {"status": "ok"}

@app.post("/ask")
def ask_endpoint(body: Question):
    """Answer a question about upcoming cultural events in Paris."""
    question = body.question.strip()
    if not question:                                  # only spaces
        raise HTTPException(status_code=422, detail="The question is empty.")
    try:
        return engine.ask(question)
    except Exception as error:                        # e.g. Ollama not running
        raise HTTPException(status_code=503, detail=f"The RAG engine failed: {error}")


@app.post("/rebuild")
def rebuild(x_api_key: str = Header(default="")):
    """Fetch the events again, rebuild the FAISS index and reload it.

    Protected: send the header X-API-Key with the REBUILD_API_KEY value from .env.
    """
    expected = os.getenv("REBUILD_API_KEY", "")
    if not expected or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")
    fetch_data.main()                                 # 1. OpenAgenda -> data/raw/events.json
    preprocess.main()                                 # 2. clean + chunk
    build_index.main()                                # 3. embeddings + FAISS index on disk
    engine.vectorstore = build_index.load_index()     # 4. the running API uses the new index
    return {"status": "rebuilt", "vectors": engine.vectorstore.index.ntotal}
