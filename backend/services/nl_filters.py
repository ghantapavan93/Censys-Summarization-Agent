from __future__ import annotations
from typing import Dict, Any, List
import re

_RX_COUNTRY_HINT = re.compile(r"(?:country|located in|from)\s*[:=]?\s*([A-Za-z \.-]{2,})", re.I)
_RX_COUNTRY_IN = re.compile(r"\bin\s+([A-Za-z][A-Za-z \.-]{2,})\b", re.I)
_RX_PORT = re.compile(r"port\s*[:=]?\s*(\d{1,5})", re.I)
_RX_PRODUCT = re.compile(r"\b(product|service|app|application)\s*[:=]?\s*([\w\.-]{2,})", re.I)
_RX_CVE = re.compile(r"(CVE-\d{4}-\d{4,7})", re.I)
_RX_VERSION = re.compile(r"\b(\d+(?:\.\d+){1,3})\b")
_RX_HARDWARE = re.compile(r"\b(camera|router|switch|firewall|server|workstation|gateway|ap|access point)s?\b", re.I)

_COUNTRY_MAP = {
    "united states": "US", "usa": "US", "us": "US",
    "united kingdom": "GB", "uk": "GB", "great britain": "GB",
    "russia": "RU", "russian federation": "RU",
    "china": "CN", "people's republic of china": "CN",
    "canada": "CA", "germany": "DE", "france": "FR",
}

_STOP = {"in", "the", "of", "and", "for", "on"}


def parse_query_to_filters(query: str) -> Dict[str, Any]:
    if not query:
        return {}
    filters: Dict[str, Any] = {}
    q = query.strip()

    # Country
    country_val = None
    if m := _RX_COUNTRY_HINT.search(q):
        country_val = m.group(1).strip()
    elif m := _RX_COUNTRY_IN.search(q):
        country_val = m.group(1).strip()
    if country_val:
        key = country_val.lower()
        filters["country"] = _COUNTRY_MAP.get(key, country_val.upper() if len(country_val) <= 3 else country_val)

    # Port
    if m := _RX_PORT.search(q):
        try:
            filters["port"] = int(m.group(1))
        except Exception:
            pass

    # Product (explicit label) or first token heuristic
    if m := _RX_PRODUCT.search(q):
        filters["product"] = m.group(2).strip().lower()
    else:
        # Heuristic: first meaningful token becomes product
        tokens = re.findall(r"\b([a-z][a-z0-9_\.-]{2,})\b", q.lower())
        tokens = [t for t in tokens if t not in _STOP]
        if tokens:
            filters["product"] = tokens[0]

    # Version
    if m := _RX_VERSION.search(q):
        filters["version"] = m.group(1)

    # Hardware
    if m := _RX_HARDWARE.search(q):
        filters["hardware"] = m.group(1).lower()

    # CVEs
    cves: List[str] = []
    for m in _RX_CVE.findall(q):
        cves.append(m.upper())
    if cves:
        filters["cve"] = cves
    return filters
