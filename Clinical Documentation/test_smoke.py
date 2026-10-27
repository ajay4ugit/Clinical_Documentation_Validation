"""Smoke test — verifies every API endpoint returns expected data."""
import urllib.request
import json
import sys

BASE = "http://127.0.0.1:8080"
PASS = 0
FAIL = 0

def check(label, url, method="GET", body=None):
    global PASS, FAIL
    try:
        req = urllib.request.Request(url, data=body, method=method,
                                     headers={"Content-Type": "application/json"})
        r   = urllib.request.urlopen(req, timeout=10)
        d   = json.loads(r.read())
        print(f"  PASS  {label}")
        PASS += 1
        return d
    except Exception as e:
        print(f"  FAIL  {label}: {e}")
        FAIL += 1
        return None

# ── API endpoint tests ────────────────────────────────────────────────────
stats = check("GET /api/stats", f"{BASE}/api/stats")
if stats:
    t = stats["totals"]
    print(f"        docs={t['documents']} patients={t['patients']} "
          f"doctors={t['doctors']} issues={t['issues']}")

docs = check("GET /api/documents?per_page=5", f"{BASE}/api/documents?per_page=5")
if docs:
    print(f"        total={docs['total']} pages={docs['pages']}")

check("GET /api/documents/1", f"{BASE}/api/documents/1")
check("GET /api/patients",    f"{BASE}/api/patients")
check("GET /api/doctors",     f"{BASE}/api/doctors")
check("GET /api/issues",      f"{BASE}/api/issues")

val = check("POST /api/documents/1/validate",
            f"{BASE}/api/documents/1/validate", method="POST", body=b"{}")
if val:
    print(f"        score={val['ai_score']} status={val['status']} engine={val.get('engine','?')}")

check("GET / (dashboard page)", f"{BASE}/")
check("GET /documents page",    f"{BASE}/documents")
check("GET /patients page",     f"{BASE}/patients")
check("GET /issues page",       f"{BASE}/issues")
check("GET /new-document page", f"{BASE}/new-document")

# ── Summary ───────────────────────────────────────────────────────────────
print()
print(f"Results: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
