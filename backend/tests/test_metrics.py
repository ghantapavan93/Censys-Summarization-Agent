from fastapi.testclient import TestClient
from backend.app import app

def test_metrics_liveness():
    c = TestClient(app)
    # trigger at least one request so histogram observations exist
    c.get("/api/health")
    r = c.get("/metrics")
    assert r.status_code == 200
    body = r.text
    assert "censys_requests_total" in body
    assert "censys_request_latency_seconds_bucket" in body
