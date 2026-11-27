"""RAG engine: search the FAISS index, then ask the LLM to answer from the results.

Usage (from the project root):
    python -m rag.engine
"""
from langchain_ollama import ChatOllama
from scripts.build_index import load_index
from datetime import date

LLM_MODEL = "mistral"   # local model served by Ollama
TOP_K = 5               # number of events given to the LLM

PROMPT = """Tu es l'assistant de Puls-Events. Tu recommandes des événements culturels à Paris.
Nous sommes le {today}.
Réponds en français, uniquement à partir des événements ci-dessous.
Pour chaque événement cité, donne son titre, ses dates et son lieu.
Si aucun événement ne correspond à la question, dis-le simplement.

Événements :
{context}

Question : {question}
Réponse :"""

vectorstore = load_index()                       # loaded once, reused for every question
llm = ChatOllama(model=LLM_MODEL, temperature=0.1)


def retrieve(question, k=TOP_K):
    """Return k chunks from k different events that are not finished yet."""
    today = date.today().isoformat()                         # e.g. "2026-11-26"
    candidates = vectorstore.similarity_search(
        question, k=50, fetch_k=200,                         # many candidates...
        filter=lambda m: m["last_date"][:10] >= today,       # ...keep only events that end today or later
    )
    docs, seen_uids = [], set()
    for doc in candidates:                                   # closest first
        uid = doc.metadata["uid"]
        if uid in seen_uids:                                 # event already kept: skip this chunk
            continue
        seen_uids.add(uid)
        docs.append(doc)
        if len(docs) == k:
            break
    return docs


def ask(question, k=TOP_K):
    """Return the LLM answer and the sources used."""
    docs = retrieve(question, k)                                    # 1. retrieve
    context = "\n\n---\n\n".join(doc.page_content for doc in docs)  # 2. build the context
    prompt = PROMPT.format(today=date.today().isoformat(),          # 3. fill the prompt
                           context=context, question=question)
    answer = llm.invoke(prompt).content                             # 4. generate
    sources = [{"title": doc.metadata["title"], "url": doc.metadata["url"]} for doc in docs]
    return {"answer": answer, "sources": sources}


# Quick test: runs only when this file is executed directly, not when it is imported
if __name__ == "__main__":
    import time
    for question in ["Quels concerts de jazz à Paris cette semaine ?",
                     "Y a-t-il un match de football au Parc des Princes ?"]:
        start = time.time()
        result = ask(question)
        print(f"\n=== {question} ({time.time() - start:.0f} s)")
        print(result["answer"])
        for source in result["sources"]:
            print("  -", source["title"])
