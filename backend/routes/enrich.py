from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any
from ..services.kev_loader import kev_store
from ..services.metrics import ENRICH_TOTAL

router = APIRouter(tags=["enrich"])


class EnrichRequest(BaseModel):
    hosts: List[Dict[str, Any]]


class EnrichResponse(BaseModel):
    hosts: List[Dict[str, Any]]


SENSITIVE_PORTS = {22, 23, 25, 80, 110, 143, 389, 443, 445, 465, 587, 993, 995,
                   1433, 1521, 2049, 2375, 2380, 27017, 3000, 3306, 3389, 5432,
                   5601, 5900, 6379, 8000, 8080, 9200, 9300}
MGMT_PORTS = {22, 3389, 5900, 2375, 2380}  # ssh, rdp, vnc, docker


def _cvss_from(v: Dict[str, Any]) -> float:
    # tolerate cvss fields in different shapes
    for k in ("cvss_v3", "cvss", "cvssScore", "cvss3"):
        val = v.get(k)
        try:
            if val is None:
                continue
            return float(val)
        except Exception:
            continue
    return 0.0


def _cve_from(v: Dict[str, Any]) -> str | None:
    return v.get("cve") or v.get("id") or v.get("cve_id")


def _score_host(h: Dict[str, Any]) -> Dict[str, Any]:
    vulns = h.get("vulns") or h.get("vulnerabilities") or []
    services = h.get("services") or []
    open_ports = {s.get("port") for s in services if isinstance(s, dict) and s.get("port") is not None}

    kev_present = False
    cvss_high_present = False
    cvss_critical_present = False

    score = 0

    for v in vulns:
        cve = _cve_from(v)
        cvss = _cvss_from(v)
        if kev_store.has(cve):
            kev_present = True
            score += 60
        if cvss >= 9.0:
            cvss_critical_present = True
            score += 30
        elif cvss >= 7.0:
            cvss_high_present = True
            score += 15

    # service heuristics
    if open_ports:
        # general “attack surface” signal (capped)
        score += min(20, len(open_ports) * 2)
        # sensitive ports bump
        sens_hits = len([p for p in open_ports if p in SENSITIVE_PORTS])
        score += min(15, sens_hits * 3)
        # mgmt ports (ssh/rdp/vnc/docker) bump
        mgmt_hits = len([p for p in open_ports if p in MGMT_PORTS])
        score += min(10, mgmt_hits * 5)

    score = min(100, score)  # cap to 100

    out = dict(h)
    out.update({
        "kev_present": kev_present,
        "cvss_high_present": cvss_high_present or cvss_critical_present,
        "cvss_critical_present": cvss_critical_present,
        "risk_score": int(score),
        "open_ports": sorted([p for p in open_ports if isinstance(p, int)]),
    })
    return out


@router.post("/enrich/vulns", response_model=EnrichResponse)
def enrich_vulns(req: EnrichRequest):
    try:
        ENRICH_TOTAL.inc()
    except Exception:
        pass
    enriched = [_score_host(h) for h in (req.hosts or [])]
    # simple descending sort by risk
    enriched.sort(key=lambda h: h.get("risk_score", 0), reverse=True)
    return {"hosts": enriched}
