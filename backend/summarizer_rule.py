from typing import Dict, Any, List

from .analytics import generate_insights
from .schemas import Host, SummaryResponse, HostSummary, DatasetInsights, Severity

RISK_HINTS = {
    22: "SSH exposed",
    23: "Telnet exposed",
    80: "HTTP",
    443: "HTTPS",
    3306: "MySQL",
    5432: "Postgres",
    3389: "RDP",
}

def _surface_str(h: Host) -> str:
    parts = []
    # Prepend location/ASN context if available
    asn = h.autonomous_system.name if (h.autonomous_system and h.autonomous_system.name) else None
    loc = h.location.country if (h.location and h.location.country) else None
    if asn or loc:
        parts.append(" | ".join([x for x in [loc, asn] if x]))
    for s in (h.services or []):
        p = []
        if s.port: p.append(str(s.port))
        if s.protocol: p.append(s.protocol)
        if s.software:
            soft = ["/".join(filter(None, [sw.vendor, sw.product, sw.version]))
                    for sw in s.software if (sw.product or sw.vendor or sw.version)]
            if soft:
                p.append("[" + ", ".join(soft) + "]")
        if s.labels: p.append("{" + ",".join(s.labels) + "}")
        if p: parts.append(" ".join(p))
    if not parts:
        return "No services observed"
    return "; ".join(parts)[:240]

def _risk_str(h: Host) -> str:
    risks = set()
    ports = [s.port for s in (h.services or []) if s.port is not None]
    for s in (h.services or []):
        if s.port in RISK_HINTS:
            risks.add(RISK_HINTS[s.port])
    if 22 in ports:
        risks.add("Use key-based auth & rate limiting on SSH")
    if 80 in ports and 443 not in ports:
        risks.add("HTTP without TLS")
    return ", ".join(sorted(risks)) or "Minimal surface detected"

def summarize_host_rule(h: Host) -> Dict[str, Any]:
    asn = h.autonomous_system.name if (h.autonomous_system and h.autonomous_system.name) else None
    loc = h.location.country if (h.location and h.location.country) else None
    notes = ", ".join([x for x in [asn, loc] if x])
    return {
        "ip": h.ip,
        "summary": _surface_str(h),
        "risk": _risk_str(h),
        "notes": notes,
    }


class RuleSummarizer:
    """Simple rule-based summarizer used in tests.

    - Produces per-host summaries
    - Assigns a coarse severity hint based on detected risk
    - Aggregates dataset insights
    """

    def _severity_from_risk(self, risk: str) -> Severity:
        text = (risk or "").lower()
        if "telnet" in text:
            return Severity.CRITICAL
        if "ssh exposed" in text or "http without tls" in text:
            return Severity.HIGH
        if "mysql" in text or "postgres" in text:
            return Severity.MEDIUM
        if "http" in text or "https" in text:
            return Severity.LOW
        if text:
            return Severity.INFO
        return Severity.UNKNOWN

    def summarize(self, hosts: List[Host]) -> SummaryResponse:
        hosts = hosts or []
        summaries: List[Dict[str, Any]] = []
        for h in hosts:
            base = summarize_host_rule(h)
            sev = self._severity_from_risk(base.get("risk"))
            host_summary = HostSummary(ip=base["ip"], summary=base.get("summary", ""), severity_hint=sev)
            summaries.append(host_summary.model_dump())

        insights: DatasetInsights = generate_insights(hosts)
        return SummaryResponse(count=len(hosts), summaries=summaries, insights=insights)
