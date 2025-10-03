from __future__ import annotations

from typing import TypedDict, Literal, Callable, List, Dict, Any


class RiskItem(TypedDict, total=False):
    id: str
    title: str
    severity: Literal["HIGH", "MEDIUM", "LOW"]
    risk_score: float
    cves: List[str]
    evidence: List[str]
    fix: str
    tags: List[str]


RuleFn = Callable[[List[Dict[str, Any]], Dict[str, Any]], List[RiskItem]]


def run_rules(records: List[Dict[str, Any]], aux: Dict[str, Any]) -> List[RiskItem]:
    from . import tls_rules, db_rules, remote_access_rules, admin_ui_rules
    rules: List[RuleFn] = []
    rules.extend(getattr(tls_rules, "RULES", []))
    rules.extend(getattr(db_rules, "RULES", []))
    rules.extend(getattr(remote_access_rules, "RULES", []))
    rules.extend(getattr(admin_ui_rules, "RULES", []))
    out: List[RiskItem] = []
    for fn in rules:
        try:
            out.extend(fn(records, aux) or [])
        except Exception:
            continue
    return out
