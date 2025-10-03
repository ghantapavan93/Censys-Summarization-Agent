from backend.agent.graph import run_pipeline
from backend.models import Record


def test_run_pipeline_sets_version_fallback():
    recs = [Record(id="1", ip="1.1.1.1", port=22, product="OpenSSH", version=None, hardware=None, country="US", cve=None, other=None)]
    out = run_pipeline(records=recs, nl="", event_id="evt-test", now_utc=None, request_topk=None, use_llm=False)
    assert "meta" in out.dict(), "response missing meta"
    ver = out.meta.get("version")
    assert isinstance(ver, str) and len(ver) > 0
