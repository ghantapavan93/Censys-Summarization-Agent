import glob
import json
from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)


def test_no_openai_import():
    hits = []
    for path in glob.glob("backend/**/*.py", recursive=True):
        # skip virtualenv or third-party caches if present under backend/
        lower = path.lower().replace("\\", "/")
        if any(seg in lower for seg in ["/venv/", "/site-packages/", "/__pycache__/"]):
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                if "openai" in f.read().lower():
                    hits.append(path)
        except Exception:
            # ignore files with problematic encodings
            continue
    assert not hits, f"Found unexpected openai imports in: {hits}"


def _hosts_payload_from_examples():
    # Build a /summarize body that uses hosts key as per normalizer
    with open("backend/examples/input_sample.json", "r", encoding="utf-8") as f:
        hosts = json.load(f)
    return {"hosts": hosts, "nl": "", "event_id": "evt-test"}


def test_schema_and_charts():
    body = _hosts_payload_from_examples()
    r = client.post("/summarize", json=body)
    assert r.status_code == 200
    js = r.json()

    for k in [
        "summary","key_findings","risks","risk_matrix","viz_payload","query_trace","next_actions","meta"
    ]:
        assert k in js

    # risk_matrix keys present
    rm = js["risk_matrix"]
    assert isinstance(rm.get("high", 0), int)
    assert isinstance(rm.get("medium", 0), int)
    assert isinstance(rm.get("low", 0), int)

    # charts present
    vp = js["viz_payload"]
    assert isinstance(vp.get("charts", []), list)
    # optional histograms convenience maps if present
    h = vp.get("histograms", {})
    if h:
        assert isinstance(h.get("protocols", {}), dict)
    # top_ports convenience map if present
    tp = vp.get("top_ports", {})
    assert isinstance(tp, dict)


def test_topk_override_caps():
    body = _hosts_payload_from_examples()
    body["topk"] = 9999
    r = client.post("/summarize", json=body)
    assert r.status_code == 200
    js = r.json()
    assert "query_trace" in js
    assert js["query_trace"].get("topk", 0) > 0
