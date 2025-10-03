from __future__ import annotations

import json, os, time
from typing import Dict, Any, List, Optional

DATA_DIR = os.environ.get("DATA_DIR", "data")
VIEWS_PATH = os.path.join(DATA_DIR, "saved_views.json")
ALERTS_PATH = os.path.join(DATA_DIR, "alerts.json")


def _load(path: str) -> List[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save(path: str, rows: List[Dict[str, Any]]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f)


def list_views() -> List[Dict[str, Any]]:
    return _load(VIEWS_PATH)


def save_view(name: str, dsl: str) -> Dict[str, Any]:
    now = int(time.time())
    rows = list_views()
    # replace if name exists
    rows = [r for r in rows if r.get("name") != name]
    row = {"name": name, "dsl": dsl, "created_at": now}
    rows.append(row)
    _save(VIEWS_PATH, rows)
    return row


def list_alerts() -> List[Dict[str, Any]]:
    return _load(ALERTS_PATH)


def save_alert(name: str, dsl: str, webhook: Optional[str] = None, email: Optional[str] = None) -> Dict[str, Any]:
    now = int(time.time())
    rows = list_alerts()
    rows = [r for r in rows if r.get("name") != name]
    row = {"name": name, "dsl": dsl, "webhook": webhook, "email": email, "created_at": now}
    rows.append(row)
    _save(ALERTS_PATH, rows)
    return row
