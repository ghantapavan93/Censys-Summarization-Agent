from __future__ import annotations

import hashlib
import json
import os
from typing import Dict, Any, List, Optional

DATA_DIR = os.environ.get("DATA_DIR", "data")
SNAP_DIR = os.path.join(DATA_DIR, "snapshots")


def _norm_text(x: Any) -> str:
    try:
        return str(x or "").strip()
    except Exception:
        return ""


def dataset_key(records: List[Dict[str, Any]] | None) -> str:
    """Produce a stable dataset identity from key tokens of records.

    Uses the set of (ip,port,product) tokens sorted, then SHA1 hash.
    """
    tokens: List[str] = []
    for r in records or []:
        ip = _norm_text(r.get("ip"))
        if not ip:
            continue
        services = r.get("services") if isinstance(r.get("services"), list) else [r]
        for s in services or []:
            port = _norm_text(s.get("port") or r.get("port"))
            prod = _norm_text(s.get("product") or r.get("product"))
            tokens.append(f"{ip}:{port}:{prod}".lower())
    if not tokens:
        return hashlib.sha1(b"empty").hexdigest()
    payload = "|".join(sorted(set(tokens))).encode("utf-8")
    return hashlib.sha1(payload).hexdigest()


def build_risk_snapshot(risks: List[Dict[str, Any]]) -> Dict[str, Any]:
    snap: Dict[str, Any] = {}
    for r in risks or []:
        rid = _norm_text(r.get("id") or r.get("title"))
        if not rid:
            continue
        snap[rid] = {"severity": _norm_text(r.get("severity")).upper()}
    return snap


def diff_snapshots(prev: Dict[str, Any] | None, curr: Dict[str, Any] | None) -> Dict[str, Any]:
    prev = prev or {}
    curr = curr or {}
    p_ids = set(prev.keys())
    c_ids = set(curr.keys())
    new = sorted(c_ids - p_ids)
    resolved = sorted(p_ids - c_ids)
    changed: List[Dict[str, str]] = []
    for rid in (p_ids & c_ids):
        if (prev.get(rid) or {}).get("severity") != (curr.get(rid) or {}).get("severity"):
            changed.append({"id": rid, "from": (prev.get(rid) or {}).get("severity"), "to": (curr.get(rid) or {}).get("severity")})
    return {
        "counts": {"new": len(new), "resolved": len(resolved), "changed": len(changed)},
        "new": new,
        "resolved": resolved,
        "changed": changed,
    }


def _path_for(key: str) -> str:
    os.makedirs(SNAP_DIR, exist_ok=True)
    return os.path.join(SNAP_DIR, f"{key}.json")


def load_snapshot(key: str) -> Optional[Dict[str, Any]]:
    path = _path_for(key)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_snapshot(key: str, snap: Dict[str, Any]) -> None:
    path = _path_for(key)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(snap, f)
    except Exception:
        pass
 
