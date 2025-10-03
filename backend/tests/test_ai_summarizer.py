import pytest

from backend.services.ai_summarizer import summarize_with_llm


def test_ai_summarizer_no_duplicate_keys_and_has_overviews():
    insights = {"count": 2, "records": [
        {"ip": "1.1.1.1", "port": 22, "product": "OpenSSH", "location": {"country": "US"}},
        {"ip": "2.2.2.2", "port": 80, "product": "nginx",   "location": {"country": "DE"}},
    ]}
    out = summarize_with_llm(insights, context_snippets=[
        {"id": "r1", "ip": "1.1.1.1", "port": 22, "product": "OpenSSH", "country": "US", "score": 0.7, "cve": []},
        {"id": "r2", "ip": "2.2.2.2", "port": 80, "product": "nginx",   "country": "DE", "score": 0.5, "cve": []},
    ], use_llm=False)

    # Required keys
    for k in [
        "summary",
        "overview",
        "overview_deterministic",
        "key_risks",
        "recommendations",
        "highlights",
    ]:
        assert k in out, f"missing {k}"

    # Ensure types
    assert isinstance(out["overview_deterministic"], str)
    assert isinstance(out.get("overview_llm", "") or "", str)

    # Ensure use_llm_available is boolean
    assert isinstance(out.get("use_llm_available", False), bool)
