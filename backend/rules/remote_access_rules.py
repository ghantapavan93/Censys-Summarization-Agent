from __future__ import annotations

from typing import List, Dict, Any
from .base import RiskItem


def remote_access(records: List[Dict[str, Any]], aux: Dict[str, Any]) -> List[RiskItem]:
    out: List[RiskItem] = []
    RA_HINTS = {
        3389: ("RDP internet-exposed", "HIGH"),
        445: ("SMB internet-exposed", "HIGH"),
        23: ("Telnet internet-exposed", "HIGH"),
        5900: ("VNC internet-exposed", "MEDIUM"),
    }
    for r in records or []:
        for s in (r.get("services") or []):
            p = s.get("port")
            if p in RA_HINTS:
                title, sev = RA_HINTS[p]
                out.append(RiskItem(
                    id=f"rule:remote.{str(title).split()[0].lower()}:{r.get('ip')}:{p}",
                    title=f"remote.{str(title).split()[0].lower()}: {title}",
                    severity=sev,  # type: ignore
                    risk_score=8.5 if sev == "HIGH" else 6.0,
                    evidence=[f"{r.get('ip')}:{p}"],
                    fix="Close public exposure; require VPN/Bastion; harden configuration.",
                    tags=["remote"],
                ))
            # SMBv1 dialect flag if protocol hint present
            if p == 445:
                other = s.get("other") or {}
                dialect = str(other.get("smb_dialect") or "").lower()
                if dialect.startswith("smb1") or dialect == "1.0":
                    out.append(RiskItem(
                        id=f"rule:remote.smbv1:{r.get('ip')}:{p}",
                        title="remote.smbv1: SMBv1 protocol detected",
                        severity="HIGH",  # type: ignore
                        risk_score=9.0,
                        evidence=[f"{r.get('ip')}:{p} dialect={other.get('smb_dialect')}",],
                        fix="Disable SMBv1 (CIFS); require SMBv2+ and apply MS17-010 class patches.",
                        tags=["remote","smb"],
                    ))
    return out


RULES = [remote_access]
