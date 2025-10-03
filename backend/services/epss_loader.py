from __future__ import annotations

"""EPSS loader: returns mapping {CVE: score} and simple in-memory cache.

By default loads from data/epss.json if present. File format options:
- {"CVE-2023-1234": 0.97, ...}
- {"rows": [{"cve": "CVE-2023-1234", "score": 0.97}, ...]}
"""

import json
import os
from typing import Dict

_EPSS_PATH = os.environ.get("EPSS_PATH", os.path.join("data", "epss.json"))
_CACHE: Dict[str, float] | None = None


def _load_from_file(path: str) -> Dict[str, float]:
    if not os.path.exists(path):
        # Fallback: try data/epss.csv when epss.json is missing
        csv_path = os.path.join("data", "epss.csv")
        if os.path.exists(csv_path):
            return _load_from_csv(csv_path)
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            # direct mapping
            if all(isinstance(v, (int, float)) for v in data.values()):
                return {str(k).upper(): float(v) for k, v in data.items()}
            # rows structure
            rows = data.get("rows")
            if isinstance(rows, list):
                out: Dict[str, float] = {}
                for r in rows:
                    cve = str(r.get("cve") or r.get("id") or "").strip().upper()
                    try:
                        score = float(r.get("score"))
                    except Exception:
                        continue
                    if cve and 0 <= score <= 1:
                        out[cve] = score
                return out
        return {}
    except Exception:
        # If JSON load fails but it's a CSV file, try CSV parser
        try:
            if path.lower().endswith(".csv"):
                return _load_from_csv(path)
        except Exception:
            pass
        return {}


def _load_from_csv(path: str) -> Dict[str, float]:
    try:
        import csv
        out: Dict[str, float] = {}
        with open(path, newline="", encoding="utf-8") as f:
            rdr = csv.DictReader(f)
            # Accept common headers: cve, epss|score
            for row in rdr:
                cve = str((row.get("cve") or row.get("CVE") or row.get("id") or "").strip()).upper()
                val = row.get("epss") or row.get("EPSS") or row.get("score") or row.get("Score")
                try:
                    score = float(val)
                except Exception:
                    continue
                if cve and 0 <= score <= 1:
                    out[cve] = score
        return out
    except Exception:
        return {}


def get_epss() -> Dict[str, float]:
    global _CACHE
    if _CACHE is None:
        _CACHE = _load_from_file(_EPSS_PATH)
    return _CACHE


def warm_reload(path: str | None = None) -> int:
    """Reload EPSS mapping from a path; returns number of entries."""
    global _CACHE
    p = path or _EPSS_PATH
    # Support CSV explicitly
    if p.lower().endswith(".csv") and not os.path.exists(p):
        p = os.path.join("data", "epss.csv")
    _CACHE = _load_from_file(p)
    return len(_CACHE or {})
