from __future__ import annotations

from typing import List, Dict, Any
from .base import RiskItem


def admin_ui(records: List[Dict[str, Any]], aux: Dict[str, Any]) -> List[RiskItem]:
    out: List[RiskItem] = []
    HINTS = [
        "jenkins",
        "grafana",
        "prometheus",
        "kibana",
        "tomcat",
        "kubelet",
        "kubernetes",
        "k8s",
        "sonarqube",
    ]
    for r in records or []:
        for s in (r.get("services") or []):
            prod = (s.get("product") or "").lower()
            if any(h in prod for h in HINTS):
                out.append(RiskItem(
                    id=f"rule:admin_ui:{r.get('ip')}:{s.get('port')}",
                    title=f"admin_ui: {(s.get('product') or 'Admin UI')} exposed",
                    severity="MEDIUM",
                    risk_score=5.5,
                    evidence=[f"{r.get('ip')}:{s.get('port')} {s.get('product') or ''}".strip()],
                    fix="Require auth/SSO, restrict ingress, place behind reverse proxy.",
                    tags=["admin-ui"],
                ))
    return out


RULES = [admin_ui]
