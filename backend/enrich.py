from typing import Dict, Any, List, Set

# Initialized at startup from kev_loader.fetch_kev_ids()
KEV_IDS: Set[str] = set()

WEIGHTS = {
    "kev": 40,
    "cvss_high": 25,  # CVSS >= 7
    "label_login": 10,
    "label_open_dir": 10,
    "label_waf": -5,
    "non_std_http": 5,  # HTTP on non-standard ports (incl. ollama non-11434)
}


def set_kev_ids(ids: Set[str]):
    global KEV_IDS
    KEV_IDS = set(ids or [])


def _cvss_score(v: Dict[str, Any]) -> float:
    m = v.get("metrics") or {}
    return float(
        m.get("cvss_v40", {}).get("score")
        or m.get("cvss_v31", {}).get("score")
        or m.get("cvss_v30", {}).get("score")
        or 0
    )


def score_service(svc: Dict[str, Any]) -> int:
    score = 0
    for v in (svc.get("vulns") or []):
        if (v.get("id") in KEV_IDS) or v.get("kev"):
            score += WEIGHTS["kev"]
        if _cvss_score(v) >= 7:
            score += WEIGHTS["cvss_high"]

    labels = {str(l).upper() for l in (svc.get("labels") or [])}
    if "LOGIN_PAGE" in labels:
        score += WEIGHTS["label_login"]
    if "OPEN_DIRECTORY" in labels:
        score += WEIGHTS["label_open_dir"]
    if "WAF" in labels:
        score += WEIGHTS["label_waf"]

    port = svc.get("port")
    if svc.get("protocol") == "HTTP" and port and port not in (80, 443, 11434):
        score += WEIGHTS["non_std_http"]

    return score


def score_host(host: Dict[str, Any]) -> Dict[str, Any]:
    services: List[Dict[str, Any]] = host.get("services") or []
    risk = sum(score_service(s) for s in services)

    host["risk_score"] = max(0, risk)
    host["kev_present"] = any(
        (v.get("id") in KEV_IDS) or v.get("kev")
        for s in services for v in (s.get("vulns") or [])
    )
    host["cvss_high_present"] = any(
        _cvss_score(v) >= 7 for s in services for v in (s.get("vulns") or [])
    )
    return host
