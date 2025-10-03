import json
import os
from fastapi.testclient import TestClient

from backend.app import app

client = TestClient(app)


def _load_hosts_payload():
    p = os.path.join(os.path.dirname(__file__), "..", "examples", "input_sample.json")
    with open(p, "r", encoding="utf-8") as f:
        hosts = json.load(f)
    return {"hosts": hosts}


def test_healthz_ok():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_config_endpoint():
    r = client.get("/config")
    assert r.status_code == 200
    data = r.json()
    for k in ("model_backend", "model_name", "retrieval_k", "language", "enable_validation"):
        assert k in data


def test_legacy_summarize_ok():
    payload = _load_hosts_payload()
    r = client.post("/summarize/legacy", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "count" in data and "summaries" in data and "insights" in data
    assert isinstance(data["summaries"], list)
    assert len(data["summaries"]) >= 1


def test_query_assistant_modern_shape():
    payload = _load_hosts_payload()
    r = client.post("/query-assistant", json=payload)
    assert r.status_code == 200
    data = r.json()
    for k in ("summary", "viz_payload", "risk_matrix", "meta", "key_findings"):
        assert k in data