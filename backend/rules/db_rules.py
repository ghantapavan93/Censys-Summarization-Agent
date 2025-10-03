from __future__ import annotations

from typing import List, Dict, Any
from .base import RiskItem


def db_open(records: List[Dict[str, Any]], aux: Dict[str, Any]) -> List[RiskItem]:
    out: List[RiskItem] = []
    DB_HINTS = {
        5432: ("PostgreSQL open", "MEDIUM"),
        6379: ("Redis open/no-auth", "HIGH"),
        9200: ("Elasticsearch open", "HIGH"),
        27017: ("MongoDB open", "HIGH"),
    }
    for r in records or []:
        for s in (r.get("services") or []):
            p = s.get("port")
            if p in DB_HINTS:
                title, sev = DB_HINTS[p]
                out.append(RiskItem(
                    id=f"rule:db-open:{r.get('ip')}:{p}",
                    title=title,
                    severity=sev,  # type: ignore
                    risk_score=7.0 if sev == "HIGH" else 5.0,
                    evidence=[f"{r.get('ip')}:{p}"],
                    fix="Restrict to private networks; require auth and TLS.",
                    tags=["db"],
                ))
    return out


def mysql_open(records: List[Dict[str, Any]], aux: Dict[str, Any]) -> List[RiskItem]:
    hits: List[Dict[str, Any]] = []
    for r in records or []:
        ip = r.get("ip")
        for s in (r.get("services") or []):
            port = s.get("port")
            product = (s.get("software") or [{}])[0].get("product") if isinstance(s.get("software"), list) else s.get("product")
            product_l = str(product or "").lower()
            if port == 3306 or ("mysql" in product_l):
                ver = (s.get("software") or [{}])[0].get("version") if isinstance(s.get("software"), list) else s.get("version")
                hits.append({
                    "ip": ip,
                    "service": {"port": port, "product": product or "mysql", "version": ver or "unknown"}
                })
    if not hits:
        return []
    ev = [f"{h['ip']}:{h['service']['port']} • mysql {h['service'].get('version','unknown')}" for h in hits]
    return [RiskItem(
        id="db-mysql-open",
        title="MySQL exposed to Internet",
        severity="MEDIUM",  # type: ignore
        risk_score=6.0,
        evidence=ev,
        fix="Require authentication, restrict by source (ACL/VPC), disable remote root, rotate creds.",
        cves=[],  # type: ignore
        tags=["db","mysql"],
    )]


RULES = [db_open, mysql_open]
