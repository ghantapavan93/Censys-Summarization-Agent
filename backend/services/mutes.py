from __future__ import annotations

import json, os, time
from typing import Dict, Any, List, Optional

DATA_DIR = os.environ.get("DATA_DIR", "data")
MUTES_PATH = os.path.join(DATA_DIR, "mutes.json")


def _load() -> List[Dict[str, Any]]:
    try:
        with open(MUTES_PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except Exception:
        return []


def _save(rows: List[Dict[str, Any]]):
    os.makedirs(os.path.dirname(MUTES_PATH), exist_ok=True)
    with open(MUTES_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f)


def list_mutes() -> List[Dict[str, Any]]:
    return _load()


def add_mute(risk_id: str, days: int, reason: str) -> Dict[str, Any]:
    until = int(time.time()) + int(days) * 86400
    rows = [r for r in _load() if r.get("id") != risk_id]
    row = {"id": risk_id, "until": until, "reason": reason}
    rows.append(row)
    _save(rows)
    return row


def is_muted(risk: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rid = risk.get("id") or ""
    now = int(time.time())
    for r in _load():
        if r.get("id") == rid and r.get("until", 0) >= now:
            return r
    return None
