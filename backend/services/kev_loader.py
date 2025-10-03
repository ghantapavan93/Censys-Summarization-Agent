from __future__ import annotations
from dataclasses import dataclass, field
from typing import Set, Iterable
import json, os, threading

_KEV_CACHE_PATH = os.environ.get("KEV_CACHE_PATH", "data/kev_ids.json")

@dataclass
class KEVStore:
    kev_ids: Set[str] = field(default_factory=set)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def set_ids(self, ids: Iterable[str]) -> None:
        norm = {self._norm(x) for x in ids if x}
        with self._lock:
            self.kev_ids = norm

    def has(self, cve: str | None) -> bool:
        if not cve:
            return False
        with self._lock:
            return self._norm(cve) in self.kev_ids

    def _norm(self, cve: str) -> str:
        return cve.strip().upper()

    # optional: load/save a simple cache
    def load_cache(self, path: str = _KEV_CACHE_PATH) -> None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.set_ids(data if isinstance(data, list) else data.get("cves", []))
        except Exception:
            # no cache yet – fine
            pass

    def save_cache(self, path: str = _KEV_CACHE_PATH) -> None:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(sorted(self.kev_ids), f)
        except Exception:
            pass

kev_store = KEVStore()
# best-effort warm
kev_store.load_cache()
