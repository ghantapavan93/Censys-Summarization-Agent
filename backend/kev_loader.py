import json
import os
import tempfile
import time
import urllib.request
import contextlib
from typing import Set

from .settings import settings


CACHE_PATH = os.path.join(tempfile.gettempdir(), "kev_cache.json")


def _load_cache() -> Set[str]:
    with contextlib.suppress(Exception):
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and "ids" in data:
                return set(data["ids"])
    return set()


def _save_cache(ids: Set[str]) -> None:
    with contextlib.suppress(Exception):
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump({"ids": sorted(ids), "saved_at": int(time.time())}, f)


def fetch_kev_ids() -> Set[str]:
    """Attempt network fetch; fall back to cache; finally a minimal seed."""
    try:
        with urllib.request.urlopen(settings.KEV_FEED_URL, timeout=20) as r:
            data = json.load(r)
        ids = {x["cveID"] for x in data.get("vulnerabilities", []) if "cveID" in x}
        if ids:
            _save_cache(ids)
            return ids
    except Exception:
        pass
    cached = _load_cache()
    if cached:
        return cached
    return {
        "CVE-2023-44487",
        "CVE-2021-44228",
        "CVE-2023-4966",
        "CVE-2024-3400",
        "CVE-2025-1695",
    }
