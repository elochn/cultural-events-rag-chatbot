"""Functional test of the running API (black box: we only use HTTP).

Start the API first, in another terminal:
    uvicorn api.main:app
Then run:
    python api_test.py
"""
import sys
import time

import requests

BASE_URL = "http://127.0.0.1:8000"
failures = 0


def check(name, response, expected_status):
    """Print OK/FAIL for one call and count the failures."""
    global failures
    ok = response.status_code == expected_status
    if not ok:
        failures += 1
    print(f"[{'OK' if ok else 'FAIL'}] {name}: got {response.status_code}, expected {expected_status}")
    return ok


# 1. The API is running
check("GET /health", requests.get(f"{BASE_URL}/health", timeout=10), 200)

# 2. Bad requests are refused before calling the LLM (fast)
check("POST /ask empty question",
      requests.post(f"{BASE_URL}/ask", json={"question": ""}, timeout=10), 422)
check("POST /ask only spaces",
      requests.post(f"{BASE_URL}/ask", json={"question": "   "}, timeout=10), 422)
check("POST /ask missing field",
      requests.post(f"{BASE_URL}/ask", json={}, timeout=10), 422)

# 3. /rebuild is protected (never send the real key here: it would rebuild everything)
check("POST /rebuild without key",
      requests.post(f"{BASE_URL}/rebuild", timeout=10), 401)
check("POST /rebuild wrong key",
      requests.post(f"{BASE_URL}/rebuild", headers={"X-API-Key": "wrong"}, timeout=10), 401)

# 4. A real question: check the structure, not the exact text (the LLM varies)
question = "Quels concerts de jazz à Paris cette semaine ?"
start = time.time()
response = requests.post(f"{BASE_URL}/ask", json={"question": question}, timeout=180)
if check("POST /ask real question", response, 200):
    data = response.json()
    print(f"     time: {time.time() - start:.0f} s, sources: {len(data['sources'])}")
    print(f"     answer: {data['answer'][:200]}...")
    if not data["answer"] or not data["sources"]:
        failures += 1
        print("[FAIL] answer or sources is empty")

print(f"\n{failures} failure(s)")
sys.exit(1 if failures else 0)   # exit code 1 = something failed (useful for CI)