from __future__ import annotations

from typing import List, Dict, Any
from .base import RiskItem


def tls_min(records: List[Dict[str, Any]], aux: Dict[str, Any]) -> List[RiskItem]:
    out: List[RiskItem] = []
    for r in records or []:
        svcs = r.get("services") or []
        for s in svcs or []:
            other = s.get("other") or {}
            tls_ver = other.get("tls_version") or other.get("tls_protocol")
            if tls_ver and str(tls_ver).startswith(("SSL", "TLS1.0", "TLS1.1")):
                out.append(RiskItem(
                    id=f"rule:tls.min_version:{r.get('ip')}:{s.get('port')}",
                    title="tls.min_version: TLS below 1.2",
                    severity="HIGH",
                    risk_score=8.0,
                    cves=[],
                    evidence=[f"{r.get('ip')}:{s.get('port')} {tls_ver}"],
                    fix="Enforce TLS 1.2+; disable legacy protocols.",
                    tags=["tls"],
                ))
    return out


def cert_expired(records: List[Dict[str, Any]], aux: Dict[str, Any]) -> List[RiskItem]:
    out: List[RiskItem] = []
    for r in records or []:
        for s in (r.get("services") or []):
            cert = (s.get("other") or {}).get("certificate") or {}
            if cert and cert.get("expired") is True:
                out.append(RiskItem(
                    id=f"rule:tls.expired_cert:{r.get('ip')}:{s.get('port')}",
                    title="tls.expired_cert: Expired TLS certificate",
                    severity="MEDIUM",
                    risk_score=5.0,
                    cves=[],
                    evidence=[f"{r.get('ip')}:{s.get('port')} CN={cert.get('subject') or ''}"],
                    fix="Renew or replace certificate; automate rotation.",
                    tags=["tls"],
                ))
    return out


def cert_self_signed(records: List[Dict[str, Any]], aux: Dict[str, Any]) -> List[RiskItem]:
    out: List[RiskItem] = []
    for r in records or []:
        for s in (r.get("services") or []):
            cert = (s.get("other") or {}).get("certificate") or {}
            if cert and cert.get("self_signed") is True:
                out.append(RiskItem(
                    id=f"rule:tls.self_signed:{r.get('ip')}:{s.get('port')}",
                    title="tls.self_signed: Self-signed certificate",
                    severity="MEDIUM",
                    risk_score=4.5,
                    cves=[],
                    evidence=[f"{r.get('ip')}:{s.get('port')} CN={cert.get('subject') or ''}"],
                    fix="Use a publicly trusted CA certificate or private PKI for internal-only.",
                    tags=["tls"],
                ))
    return out


def weak_cipher(records: List[Dict[str, Any]], aux: Dict[str, Any]) -> List[RiskItem]:
    out: List[RiskItem] = []
    WEAK = ["RC4", "3DES", "DES", "NULL", "EXPORT", "MD5"]
    for r in records or []:
        for s in (r.get("services") or []):
            other = s.get("other") or {}
            cipher = str(other.get("tls_cipher") or "")
            if cipher and any(w in cipher.upper() for w in WEAK):
                out.append(RiskItem(
                    id=f"rule:tls.weak_cipher:{r.get('ip')}:{s.get('port')}",
                    title="tls.weak_cipher: Weak TLS cipher in use",
                    severity="MEDIUM",
                    risk_score=5.0,
                    cves=[],
                    evidence=[f"{r.get('ip')}:{s.get('port')} {cipher}"],
                    fix="Disable legacy/weak ciphers; prefer AES-GCM/CHACHA20 and TLS1.2+.",
                    tags=["tls"],
                ))
    return out


RULES = [tls_min, cert_expired]
RULES = [tls_min, cert_expired, cert_self_signed, weak_cipher]
