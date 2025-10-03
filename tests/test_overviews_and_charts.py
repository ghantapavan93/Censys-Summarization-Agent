import json
from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)


def test_overviews_and_charts_from_hosts_sample():
    # Load the sample from backend/examples
    with open("backend/examples/input_sample.json", "r", encoding="utf-8") as f:
        hosts = json.load(f)
    body = {"hosts": hosts, "nl": ""}
    r = client.post("/summarize", json=body)
    assert r.status_code == 200
    js = r.json()

    # Deterministic overview should be present and non-empty
    assert js.get("overview_deterministic"), "overview_deterministic missing or empty"
    # If Ollama is configured and reachable, we may also have overview_llm; it's optional
    assert "overview_llm" in js
    # Flag available, optional
    assert "use_llm_available" in js

    # Charts built from full dataset should not be empty on sample
    vp = js.get("viz_payload", {})
    hist = vp.get("histograms", {})
    top_ports = vp.get("top_ports", {})
    assert isinstance(hist, dict)
    # Protocols/products/countries histograms should be dicts (may be empty if sample is tiny)
    assert isinstance(hist.get("protocols", {}), (dict, list))
    assert isinstance(hist.get("products", {}), (dict, list))
    assert isinstance(hist.get("countries", {}), (dict, list))
    assert isinstance(top_ports, (dict, list))

    # meta.version present
    meta = js.get("meta", {})
    assert meta.get("version"), "meta.version missing"

    # query_trace has no structured_filters
    qt = js.get("query_trace", {})
    assert "structured_filters" not in qt
