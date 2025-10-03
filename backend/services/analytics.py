"""Analytics service: derive dataset insights from simplified records or Record models."""

from typing import Dict, Any, List, Optional
from collections import Counter
from ..core.logging import log_json
from ..models import Record as _Record


def _top_k(counter: Counter, k: int = 10) -> List[Dict[str, Any]]:
    return [{"value": str(v), "count": c} for v, c in counter.most_common(k)]


def generate_insights(records: List[Any]) -> Dict[str, Any]:
    ports, protos, sw, asns, countries = Counter(), Counter(), Counter(), Counter(), Counter()

    def _get_dict(d: Dict[str, Any], key: str) -> Optional[Any]:
        return d.get(key) if isinstance(d, dict) else None

    for r in records or []:
        try:
            if isinstance(r, _Record):
                p = r.port
                if p is not None:
                    ports[str(p)] += 1
                if r.country:
                    countries[str(r.country)] += 1
                # asn may exist in other
                a = (r.other or {}).get("asn")
                if a is not None:
                    asns[str(a)] += 1
                if r.product:
                    sw[str(r.product)] += 1
                proto = (r.other or {}).get("protocol")
                if isinstance(proto, str) and proto:
                    protos[proto.lower()] += 1
                else:
                    # Infer from product name if protocol missing
                    prod_l = (r.product or "").lower()
                    for hint in ("ssh","https","http","ftp","smtp","mysql"):
                        if hint in prod_l:
                            protos[hint] += 1
            elif isinstance(r, dict):
                p = _get_dict(r, "port")
                if p is not None:
                    ports[str(p)] += 1
                c = _get_dict(r, "country") or _get_dict(r, "location.country")
                if c:
                    countries[str(c)] += 1
                a = _get_dict(r, "asn")
                if a is not None:
                    asns[str(a)] += 1
                s = _get_dict(r, "software") or _get_dict(r, "product")
                if s:
                    sw[str(s)] += 1
                proto = _get_dict(r, "protocol") or _get_dict(r, "service_name")
                if proto:
                    protos[str(proto).lower()] += 1
                else:
                    t = str(_get_dict(r, "text") or "").lower()
                    for hint in ("ssh","https","http","ftp","smtp","mysql"):
                        if hint in t:
                            protos[hint] += 1
            else:
                continue
        except Exception:
            continue

    insights = {
        "count": len(records or []),
        "top_ports": _top_k(ports),
        "top_protocols": _top_k(protos),
        "top_software": _top_k(sw),
        "top_asns": _top_k(asns),
        "countries": _top_k(countries),
    }

    log_json("insights_computed", record_count=len(records or []))
    return insights

# Optional: simple risk weighting that can be used by callers for ranking
_PORT_SEVERITY = {22: 1.5, 80: 1.4, 443: 1.3, 3389: 1.8, 5900: 1.6, 23: 1.7}

def risk_weight(record: Dict[str, Any]) -> float:
    try:
        port = int(record.get("port", 0))
    except Exception:
        port = 0
    base = _PORT_SEVERITY.get(port, 1.0)
    cve_boost = 0.0
    cves = record.get("cve") or []
    try:
        if isinstance(cves, list) and cves:
            max_score = max(float((c or {}).get("score", 0.0) or 0.0) for c in cves)
            cve_boost = max_score / 3.0  # scale CVSS 0-10 → 0-3.3
    except Exception:
        cve_boost = 0.0
    return float(base) + float(cve_boost)