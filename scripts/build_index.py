"""Build the FAISS vector index from the processed chunks.

Input : data/processed/chunks.json   (created by scripts/preprocess.py)
Output: faiss_index/                 (FAISS index + metadata, not versioned)

Usage (from the project root):
    python scripts/build_index.py
"""
import json
import time
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHUNKS_PATH = PROJECT_ROOT / "data" / "processed" / "chunks.json"
INDEX_DIR = PROJECT_ROOT / "faiss_index"

# Multilingual model (French), 512 tokens max, small enough for Docker.
# e5 models expect "passage: " before indexed texts and "query: " before questions.
EMBEDDING_MODEL = "intfloat/multilingual-e5-small"

TEST_QUERIES = [
    "concert de jazz",
    "exposition de photographie",
    "activité gratuite pour les enfants",
]

def get_embeddings():
    """Load the embedding model (also used later by the chatbot)."""
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        encode_kwargs={"normalize_embeddings": True, "prompt": "passage: "},
        query_encode_kwargs={"normalize_embeddings": True, "prompt": "query: "},
        show_progress=True,
    )


def load_documents(path=CHUNKS_PATH):
    """Turn each chunk {text, metadata} into a LangChain Document."""
    with open(path, encoding="utf-8") as f:
        chunks = json.load(f)
    documents = []
    for chunk in chunks:
        documents.append(Document(page_content=chunk["text"], metadata=chunk["metadata"]))
    return documents


def build_index(documents, embeddings):
    """Embed all documents, store them in FAISS and save the index to disk."""
    vectorstore = FAISS.from_documents(documents, embeddings)
    vectorstore.save_local(str(INDEX_DIR))
    return vectorstore


def load_index(embeddings=None):
    """Reload the saved index (used by the chatbot and the API)."""
    if embeddings is None:
        embeddings = get_embeddings()
    # Our own file, created by this script: safe to deserialize.
    return FAISS.load_local(str(INDEX_DIR), embeddings,
                            allow_dangerous_deserialization=True)


def main():
    documents = load_documents()
    print(f"Documents to index : {len(documents)}")

    start = time.time()
    embeddings = get_embeddings()
    vectorstore = build_index(documents, embeddings)
    print(f"Index built in     : {time.time() - start:.0f} s -> {INDEX_DIR}")

    # Check: every chunk has been indexed
    indexed = vectorstore.index.ntotal
    print(f"Vectors in index   : {indexed}")
    assert indexed == len(documents), "Some chunks were not indexed!"

    # Search tests’
    for query in TEST_QUERIES:
        print(f"\n=== {query} ===")
        results = vectorstore.similarity_search_with_score(query, k=3)
        for doc, score in results:
            print(f"  {score:.3f} | {doc.metadata['title']}")


if __name__ == "__main__":
    main()