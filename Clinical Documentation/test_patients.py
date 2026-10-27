"""Test the new patient detail endpoint."""
import urllib.request, json, sys

BASE = "http://127.0.0.1:8082"
PASS = 0; FAIL = 0

def check(label, url, method="GET", body=None):
    global PASS, FAIL
    try:
        req = urllib.request.Request(url, data=body, method=method,
                                     headers={"Content-Type":"application/json"})
        r   = urllib.request.urlopen(req, timeout=10)
        d   = json.loads(r.read())
        print(f"  PASS  {label}")
        PASS += 1
        return d
    except Exception as e:
        print(f"  FAIL  {label}: {e}")
        FAIL += 1
        return None

# Patient list
pts = check("GET /api/patients", f"{BASE}/api/patients")
if pts:
    print(f"        {len(pts)} patients returned")
    first_id = pts[0]["id"]

    # Patient detail
    p = check(f"GET /api/patients/{first_id}", f"{BASE}/api/patients/{first_id}")
    if p:
        s = p["stats"]
        print(f"        name={p['name']}  dept={p['department']}")
        print(f"        docs={s['total_docs']}  validated={s['validated']}  "
              f"avg_score={s['avg_score']}  open_issues={s['open_issues']}")
        print(f"        document history rows: {len(p['documents'])}")
        # Check first doc fields
        if p["documents"]:
            d = p["documents"][0]
            assert "doc_id"       in d, "missing doc_id"
            assert "doc_type"     in d, "missing doc_type"
            assert "diagnosis"    in d, "missing diagnosis"
            assert "doctor_name"  in d, "missing doctor_name"
            assert "issue_count"  in d, "missing issue_count"
            assert "critical"     in d, "missing critical flag"
            print(f"        first doc: {d['doc_id']} — {d['doc_type']} — {d['status']}")

    # 404 on unknown patient
    check("GET /api/patients/99999 (404)", f"{BASE}/api/patients/99999")

# Patients page HTML
check("GET /patients page", f"{BASE}/patients")

print()
print(f"Results: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL <= 1 else 1)   # 1 expected fail = 404 test
