import json
from pathlib import Path
from fastapi.testclient import TestClient

from backend.app import app

client = TestClient(app)


def test_golden_sample_basic_invariants():
    hosts = json.loads(Path("backend/examples/input_sample.json").read_text(encoding="utf-8"))
    payload = {"hosts": hosts}
    r = client.post("/query-assistant", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["meta"]["record_count"] >= 0
    assert "overview_deterministic" in data
    assert isinstance(data["viz_payload"]["charts"], list)
    assert all(k in data["risk_matrix"] for k in ("high", "medium", "low"))


def test_legacy_adapter_shape():
    hosts = json.loads(Path("backend/examples/input_sample.json").read_text(encoding="utf-8"))
    payload = {"hosts": hosts}
    r = client.post("/summarize/legacy", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "count" in data and "summaries" in data and "insights" in data
    assert isinstance(data["summaries"], list) and len(data["summaries"]) >= 1


def test_golden_regression_against_snapshot():
    hosts = json.loads(Path("backend/examples/input_sample.json").read_text(encoding="utf-8"))
    payload = {"hosts": hosts}
    expected = json.loads(Path("backend/tests/golden/expected.json").read_text(encoding="utf-8"))
    r = client.post("/query-assistant", json=payload)
    assert r.status_code == 200
    data = r.json()

    # Meta.record_count stable for this fixture
    assert data.get("meta", {}).get("record_count") == expected["meta"]["record_count"]

    # Risk matrix tallies from deterministic rules + port heuristics
    rm = data.get("risk_matrix", {})
    exp_rm = expected["risk_matrix"]
    assert {"high": rm.get("high", 0), "medium": rm.get("medium", 0), "low": rm.get("low", 0)} == exp_rm

    # Viz histograms and top ports
    vp = data.get("viz_payload", {})
    # top_ports map equality
    assert vp.get("top_ports") == expected["viz_payload"]["top_ports"]
    # protocols/products/countries histograms are lists in runtime; convert to maps when needed
    hist = vp.get("histograms", {})
    # If lists present (from ai_summarizer path), coerce to maps
    def _to_map(lst):
        if isinstance(lst, dict):
            return lst
        if isinstance(lst, list):
            out = {}
            for it in lst:
                label = str(it.get("label") or it.get("value"))
                val = int(it.get("value") or it.get("count") or 0)
                if label not in (None, ""):
                    out[label] = val
            return out
        return {}
    proto_map = _to_map(hist.get("protocols"))
    prod_map = _to_map(hist.get("products"))
    country_map = _to_map(hist.get("countries"))
    assert proto_map == expected["viz_payload"]["histograms"]["protocols"]
    assert prod_map == expected["viz_payload"]["histograms"]["products"]
    assert country_map == expected["viz_payload"]["histograms"]["countries"]
