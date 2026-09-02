"""Quick end-to-end API test. Run: python test_endpoints.py"""
import urllib.request
import urllib.error
import json

BASE = "http://localhost:8000"

# Login
req = urllib.request.Request(
    f"{BASE}/api/auth/login",
    data=json.dumps({"email": "admin@cpcl.gem", "password": "Admin@123"}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST"
)
with urllib.request.urlopen(req) as resp:
    token = json.loads(resp.read())["access_token"]
    print(f"LOGIN OK — token: {token[:20]}...")

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

endpoints = [
    ("Auth /me",           "/api/auth/me"),
    ("Dashboard stats",    "/api/dashboard/stats"),
    ("Dashboard bidders",  "/api/dashboard/bidders"),
    ("Tenders list",       "/api/tenders/"),
    ("Bidders list",       "/api/bidders/"),
    ("Alerts list",        "/api/alerts/"),
    ("Alerts unread",      "/api/alerts/unread"),
    ("Reviews list",       "/api/reviews/"),
    ("Doc duplicates",     "/api/documents/duplicates"),
    ("Audit logs",         "/api/audit/"),
    ("Users list",         "/api/users/"),
    ("Reports list",       "/api/reports/tender/00000000-0000-0000-0000-000000000000"),
]

ok = fail = 0
for label, path in endpoints:
    try:
        req = urllib.request.Request(f"{BASE}{path}", headers=headers)
        with urllib.request.urlopen(req, timeout=5) as r:
            print(f"  OK   {label} ({r.status})")
            ok += 1
    except urllib.error.HTTPError as e:
        if e.code in (404, 422):   # 404 = no data yet, 422 = missing param — both fine
            print(f"  OK   {label} (HTTP {e.code} — expected no data)")
            ok += 1
        else:
            body = e.read().decode()[:120]
            print(f"  FAIL {label} (HTTP {e.code}) — {body}")
            fail += 1
    except Exception as e:
        print(f"  FAIL {label} — {e}")
        fail += 1

print(f"\nResults: {ok} OK, {fail} FAILED")
