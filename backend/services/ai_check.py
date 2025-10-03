from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import re

from .llm_router import run_ollama, has_ollama
from .summarizer_llm import deterministic_summary, build_rewrite_prompt
from ..core.config import settings


def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    return re.findall(r"[a-zA-Z0-9]+", str(text).lower())


def _jaccard(a: str, b: str) -> float:
    A, B = set(_tokenize(a)), set(_tokenize(b))
    if not A or not B:
        return 0.0
    inter = len(A & B)
    union = len(A | B)
    return inter / union if union else 0.0


def _numbers_present(text: str, numbers: List[int]) -> Tuple[int, List[int]]:
    s = str(text or "")
    found: List[int] = []
    hits = 0
    for n in numbers:
        if n is None:
            continue
        # Look for the number as digits, not as part of a larger number
        if re.search(rf"(?<!\d){re.escape(str(n))}(?!\d)", s):
            hits += 1
            found.append(n)
    return hits, found


def ai_rewrite_check(
    records: List[Dict[str, Any]],
    model: Optional[str] = None,
    *,
    min_similarity: float = 0.25,
    min_number_matches: int = 2,
    length_ratio_bounds: Tuple[float, float] = (0.4, 2.5),
) -> Dict[str, Any]:
    """
    Run deterministic summary, attempt an Ollama rewrite, and validate that
    the rewrite preserves key facts and is reasonably similar.

    Returns a structured result with checks and pass/fail.
    """
    base = deterministic_summary(records or [])
    det = (base.get("overview") or base.get("overview_deterministic") or "").strip()

    checks: List[Dict[str, Any]] = []
    llm_text: Optional[str] = None
    llm_available = has_ollama()
    error: Optional[str] = None

    if not llm_available:
        error = "Ollama CLI not found on PATH. Install or ensure it's accessible."
    else:
        try:
            prompt = build_rewrite_prompt(base)
            llm_text = run_ollama(prompt, model=model or settings.ollama_model)
        except Exception as e:
            error = str(e)
            llm_available = False

    # If no LLM output, return early with fail and base details
    if not llm_text:
        result = {
            "ok": False,
            "llm_available": llm_available,
            "error": error,
            "overview_deterministic": det,
            "overview_llm": llm_text,
            "metrics": {
                "similarity": 0.0,
                "length_ratio": None,
                "number_matches": 0,
            },
            "checks": checks,
            "base": {
                "totals": base.get("totals"),
                "top_ports": base.get("top_ports"),
                "severity_matrix": base.get("severity_matrix"),
            },
        }
        return result

    # Run validations
    # 1) Non-empty
    checks.append({
        "name": "non_empty",
        "passed": bool(llm_text.strip()),
        "details": {"length": len(llm_text or "")},
    })

    # 2) Similarity vs deterministic overview
    sim = _jaccard(det, llm_text)
    checks.append({
        "name": "similarity",
        "passed": sim >= float(min_similarity),
        "details": {"jaccard": round(sim, 4), "threshold": float(min_similarity)},
    })

    # 3) Numbers preserved: hosts, countries, unique_ips, services, unique_ports, top port
    totals = base.get("totals") or {}
    numbers_to_check: List[int] = []
    for k in ("hosts", "countries", "unique_ips", "services", "unique_ports"):
        try:
            v = totals.get(k)
            if isinstance(v, int):
                numbers_to_check.append(v)
        except Exception:
            pass
    try:
        top_port_val = (base.get("top_ports") or [{}])[0].get("port")
        if isinstance(top_port_val, int):
            numbers_to_check.append(top_port_val)
    except Exception:
        pass
    num_hits, num_found = _numbers_present(llm_text, numbers_to_check)
    checks.append({
        "name": "numbers_preserved",
        "passed": num_hits >= int(min_number_matches),
        "details": {"matched": num_hits, "required": int(min_number_matches), "numbers_found": num_found},
    })

    # 4) Reasonable length ratio
    det_len = max(1, len(det))
    llm_len = len(llm_text)
    ratio = llm_len / det_len
    lo, hi = length_ratio_bounds
    checks.append({
        "name": "length_ratio",
        "passed": (ratio >= float(lo)) and (ratio <= float(hi)),
        "details": {"ratio": round(ratio, 3), "bounds": [float(lo), float(hi)]},
    })

    ok = all(c.get("passed") for c in checks)
    return {
        "ok": bool(ok),
        "llm_available": bool(llm_available),
        "error": error,
        "overview_deterministic": det,
        "overview_llm": llm_text,
        "metrics": {
            "similarity": round(sim, 4),
            "length_ratio": round(ratio, 3),
            "number_matches": num_hits,
        },
        "checks": checks,
        "base": {
            "totals": totals,
            "top_ports": base.get("top_ports"),
            "severity_matrix": base.get("severity_matrix"),
        },
    }
