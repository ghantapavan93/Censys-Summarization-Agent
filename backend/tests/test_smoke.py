from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)


def test_healthz():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_enrich_minimal():
    body = {
        "hosts": [
            {
                "services": [{"port": 22}],
                "vulns": [{"cve": "CVE-2024-12345", "cvss": 7.8}],
            }
        ]
    }
    r = client.post("/api/enrich/vulns", json=body)
    assert r.status_code == 200
    data = r.json()
    assert "hosts" in data and len(data["hosts"]) == 1
    h = data["hosts"][0]
    assert "risk_score" in h and h["risk_score"] >= 1
