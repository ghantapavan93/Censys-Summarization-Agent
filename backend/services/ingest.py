import re
from typing import Dict, Any, List, Optional
from backend.models import Record, FieldMap

_CVE_RX = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.IGNORECASE)

_COUNTRY_CANON = {
    "united states": "US", "usa": "US", "us": "US", "u.s.": "US", "eeuu": "US", "états-unis": "US",
    "india": "IN", "bharat": "IN",
    "japan": "JP", "nihon": "JP", "nippon": "JP",
    "france": "FR",
    "germany": "DE", "deutschland": "DE",
    "united kingdom": "GB", "uk": "GB", "great britain": "GB",
    "spain": "ES", "españa": "ES",
    "canada": "CA", "ca": "CA",
}

def _to_iso2(country_val: Optional[str]) -> Optional[str]:
    if not country_val:
        return None
    s = str(country_val).strip()
    if s.lower() in _COUNTRY_CANON:
        return _COUNTRY_CANON[s.lower()]
    if len(s) == 2:
        return s.upper()
    return s  # fallback unchanged

def _first_present(d: Dict[str, Any], keys: List[str]) -> Any:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None

_DEFAULT_MAP = FieldMap(
    id=["id", "_id", "uid", "host_id"],
    ip=["ip", "ip_address", "host", "address"],
    port=["port", "dst_port", "service_port"],
    product=["product", "service", "server", "app", "application", "banner_product"],
    version=["version", "ver", "banner_version"],
    hardware=["hardware", "device", "device_type", "hw"],
    country=["country", "country_code", "location.country", "geo.country"],
    cve=["cve", "cves", "vulns", "vulnerabilities", "vulnerability_ids"]
)

def infer_field_map() -> FieldMap:
    return _DEFAULT_MAP

def canonicalize_records(raw_records: List[Dict[str, Any]], field_map: Optional[FieldMap]) -> List[Record]:
    fmap = field_map or infer_field_map()
    out: List[Record] = []
    for idx, row in enumerate(raw_records, start=1):
        flat = dict(row)  # (simple; extend if nested)
        rid = _first_present(flat, fmap.id or ["id"]) or f"rec_{idx}"
        ip = str(_first_present(flat, fmap.ip or ["ip"]) or "")
        port_val = _first_present(flat, fmap.port or ["port"]) or 0
        try:
            port = int(port_val)
        except Exception:
            port = 0
        product = _first_present(flat, fmap.product or ["product"])
        version = _first_present(flat, fmap.version or ["version"])
        hardware = _first_present(flat, fmap.hardware or ["hardware"])
        country = _to_iso2(_first_present(flat, fmap.country or ["country"]))

        cve_field = _first_present(flat, fmap.cve or ["cve"])
        cves = []
        if isinstance(cve_field, list):
            for c in cve_field:
                if isinstance(c, str) and _CVE_RX.match(c):
                    cves.append({"id": c})
                elif isinstance(c, dict) and c.get("id"):
                    e = {"id": c["id"]}
                    if "score" in c:
                        e["score"] = c["score"]
                    cves.append(e)
        else:
            blob = " ".join([str(v) for v in flat.values() if isinstance(v, (str, int, float))])
            for m in _CVE_RX.findall(blob):
                cves.append({"id": m})

        exclude_keys = (fmap.id or []) + (fmap.ip or []) + (fmap.port or []) + (fmap.product or []) + \
                       (fmap.version or []) + (fmap.hardware or []) + (fmap.country or []) + (fmap.cve or [])
        other = {k: v for k, v in flat.items() if k not in exclude_keys}

        out.append(Record(
            id=str(rid), ip=ip, port=port, product=product, version=version,
            hardware=hardware, country=country, cve=cves or None, other=other or None
        ))
    return out
