from __future__ import annotations

import os, json, time
from typing import Dict, Any, List

DATA_DIR = os.environ.get("DATA_DIR", "data")
ROLLUPS_PATH = os.path.join(DATA_DIR, "rollups.json")


def _load() -> List[Dict[str, Any]]:
    try:
        with open(ROLLUPS_PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except Exception:
        return []


def _save(rows: List[Dict[str, Any]]):
    os.makedirs(os.path.dirname(ROLLUPS_PATH), exist_ok=True)
    with open(ROLLUPS_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f)


def append_rollup(totals: Dict[str, Any], flags: Dict[str, Any]):
    rows = _load()
    rows.append({
        "ts": int(time.time()),
        "open_ports": int(totals.get("unique_ports") or 0),
        "medium_or_higher": int(flags.get("medium_plus") or 0),
        "kev": int(flags.get("kev_total") or 0),
    })
    # keep last 365
    rows = rows[-365:]
    _save(rows)


def get_trends() -> Dict[str, List[List[int]]]:
    rows = _load()
    # Return [ [ts, value], ... ] for 7/30/90
    def series(key: str, days: int) -> List[List[int]]:
        cutoff = int(time.time()) - days * 86400
        return [[r["ts"], int(r.get(key) or 0)] for r in rows if r.get("ts", 0) >= cutoff]
    return {
        "open_ports": {
            "7": series("open_ports", 7),
            "30": series("open_ports", 30),
            "90": series("open_ports", 90),
        },
        "medium_plus": {
            "7": series("medium_or_higher", 7),
            "30": series("medium_or_higher", 30),
            "90": series("medium_or_higher", 90),
        },
        "kev": {
            "7": series("kev", 7),
            "30": series("kev", 30),
            "90": series("kev", 90),
        }
    }
