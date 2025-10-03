import json
from pathlib import Path

from backend.services.ai_check import ai_rewrite_check


def test_ai_check_structure_without_ollama():
    here = Path(__file__).resolve().parents[1]
    sample = json.loads((here / 'examples' / 'input.sample.json').read_text(encoding='utf-8'))
    res = ai_rewrite_check(sample, model="qwen2.5:7b")
    # Always returns a dict with these keys
    for k in ("ok", "llm_available", "overview_deterministic", "metrics", "checks"):
        assert k in res
    assert isinstance(res["checks"], list)
    assert isinstance(res["metrics"], dict)
    # If Ollama is not installed, ok should be False and error populated
    if not res.get("llm_available"):
        assert res["ok"] is False
        assert res.get("error")
