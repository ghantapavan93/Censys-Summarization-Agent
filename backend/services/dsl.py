from __future__ import annotations

import re
from typing import Dict, Any, List, Tuple


Cond = Tuple[str, str]


def parse_dsl(dsl: str) -> List[Cond]:
    """Parse a minimal AND-only DSL into list of (key, value).

    Example: port:22 AND country:US AND product:"OpenSSH"
    Keys allowed: port, country, product, severity, asn, org, kev, epss, cve
    """
    if not isinstance(dsl, str):
        return []
    parts = [p.strip() for p in dsl.split("AND")]
    out: List[Cond] = []
    rx = re.compile(r"^(\w+)\s*:\s*(\"[^\"]*\"|\S+)$")
    for p in parts:
        m = rx.match(p)
        if not m:
            continue
        key = m.group(1).lower()
        val = m.group(2)
        if val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        out.append((key, val))
    return out


def match_risk(r: Dict[str, Any], conds: List[Cond]) -> bool:
    s = lambda x: str(x or "").lower()
    for k, v in conds:
        vv = v.lower()
        if k == "port":
            ev = " ".join(r.get("evidence") or [])
            if (f":{v} " not in (ev + " ")) and (f"port {v}" not in ev):
                return False
        elif k == "country":
            ev = " ".join(r.get("evidence") or [])
            if vv not in ev.lower():
                return False
        elif k == "product":
            ev = " ".join(r.get("evidence") or [])
            if vv not in ev.lower():
                return False
        elif k == "severity":
            if s(r.get("severity")) != vv:
                return False
        elif k == "asn":
            ident = ((r.get("details") or {}).get("identity") or {})
            if vv not in s(ident.get("asn")) and vv not in s(ident.get("org")):
                return False
        elif k == "org":
            ident = ((r.get("details") or {}).get("identity") or {})
            if vv not in s(ident.get("org")):
                return False
        elif k == "kev":
            want = vv in ("true", "1", "yes")
            if bool(r.get("kev")) != want:
                return False
        elif k == "epss":
            try:
                thr = float(v)
            except Exception:
                thr = 0.0
            try:
                if float(r.get("epss") or 0.0) < thr:
                    return False
            except Exception:
                return False
        elif k == "cve":
            cves = [str(x).lower() for x in (r.get("related_cves") or [])]
            if vv not in cves:
                return False
        else:
            return False
    return True
