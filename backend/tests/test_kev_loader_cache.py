import json
import os
from backend.kev_loader import fetch_kev_ids, CACHE_PATH


def test_fetch_kev_ids_uses_cache_when_offline(monkeypatch, tmp_path):
    # Simulate offline by making urlopen raise
    import urllib.request as req

    def boom(*a, **k):
        raise RuntimeError("offline")

    monkeypatch.setattr(req, "urlopen", boom)

    # Write a cache file
    data = {"ids": ["CVE-2021-44228", "CVE-2024-3400"]}
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f)

    ids = fetch_kev_ids()
    assert "CVE-2021-44228" in ids
    assert "CVE-2024-3400" in ids
