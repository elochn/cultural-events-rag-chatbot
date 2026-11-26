"""Tests for the FAISS index. Run: python -m pytest -v"""
import json

import pytest

from scripts.build_index import CHUNKS_PATH, INDEX_DIR, load_index


@pytest.fixture(scope="module")
def vectorstore():
    if not INDEX_DIR.exists():
        pytest.skip("Run scripts/build_index.py first")
    return load_index()


def test_every_chunk_is_indexed(vectorstore):
    with open(CHUNKS_PATH, encoding="utf-8") as f:
        chunks = json.load(f)
    assert vectorstore.index.ntotal == len(chunks)


def test_search_returns_results_with_metadata(vectorstore):
    results = vectorstore.similarity_search("concert de jazz", k=5)
    assert len(results) == 5
    for doc in results:
        assert doc.metadata["title"]
        assert doc.metadata["url"]