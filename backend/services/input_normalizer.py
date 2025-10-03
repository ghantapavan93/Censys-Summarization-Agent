from typing import Any, Dict, List, Optional


def _flat_record_from_host_service(host: Dict[str, Any], svc: Dict[str, Any], sw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    loc = (host.get("location") or {}) if isinstance(host, dict) else {}
    asn = (host.get("autonomous_system") or {}) if isinstance(host, dict) else {}
    os_info = (host.get("operating_system") or {}) if isinstance(host, dict) else {}
    # Compute product/version with sensible fallback if software block is missing
    sw_product = (sw or {}).get("product") if isinstance(sw, dict) else None
    sw_version = (sw or {}).get("version") if isinstance(sw, dict) else None
    proto_fallback = None
    try:
        # use protocol (e.g., http, ftp, mysql) when software entry is missing
        proto_fallback = (svc.get("protocol") if isinstance(svc, dict) else None)
        if isinstance(proto_fallback, str):
            proto_fallback = proto_fallback.lower()
    except Exception:
        proto_fallback = None

    rec: Dict[str, Any] = {
        "ip": host.get("ip"),
        "country": loc.get("country"),
        "country_code": loc.get("country_code"),
        "asn": asn.get("asn"),
        "as_name": asn.get("name"),

        "port": svc.get("port") if isinstance(svc, dict) else None,
        "protocol": (svc.get("protocol") if isinstance(svc, dict) else None),
        "banner": (svc.get("banner") if isinstance(svc, dict) else None),
    "product": sw_product or proto_fallback,
    "version": sw_version,
        "vendor": (sw or {}).get("vendor") if isinstance(sw, dict) else None,

        # extra signals
        "hardware": os_info.get("product"),
        "tls_enabled": bool((svc or {}).get("tls_enabled")) if isinstance(svc, dict) else False,
        "auth_required": bool((svc or {}).get("authentication_required")) if isinstance(svc, dict) else False,
        "error_message": (svc or {}).get("error_message") if isinstance(svc, dict) else None,
    }

    # CVEs → list + max score for quick ranking
    vulns = (svc.get("vulnerabilities") or []) if isinstance(svc, dict) else []
    rec["cves"] = [v.get("cve_id") for v in vulns if isinstance(v, dict) and v.get("cve_id")]
    try:
        rec["cvss_max"] = max([float(v.get("cvss_score", 0.0) or 0.0) for v in vulns]) if vulns else 0.0
    except Exception:
        rec["cvss_max"] = 0.0

    # Malware intel, if present
    if isinstance(svc, dict) and "malware_detected" in svc:
        md = svc.get("malware_detected") or {}
        if isinstance(md, dict):
            rec["malware_name"] = md.get("name")
            rec["malware_type"] = md.get("type")
            rec["malware_confidence"] = md.get("confidence")
            rec["threat_actors"] = md.get("threat_actors")

    # TLS cert details
    if rec.get("tls_enabled"):
        cert = (svc.get("certificate") or {}) if isinstance(svc, dict) else {}
        if isinstance(cert, dict):
            rec["cert_subject"] = cert.get("subject")
            rec["cert_issuer"] = cert.get("issuer")
            rec["cert_self_signed"] = cert.get("self_signed")
            rec["cert_san"] = cert.get("subject_alt_names")

    return rec


def normalize_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accepts:
      - {"raw_records": [...], "nl": "...", "event_id": "..."}
      - {"records": [...], ...}
      - {"hosts": [...], "metadata": {...}}

    Returns: {"raw_records": [...], "nl": str, "event_id": str}
    """
    # Legacy paths (already flat)
    raw = payload.get("raw_records")
    if isinstance(raw, list):
        return {
            "raw_records": raw,
            "nl": payload.get("nl", ""),
            "event_id": payload.get("event_id", "evt-unknown"),
        }

    recs = payload.get("records")
    if isinstance(recs, list):
        return {
            "raw_records": recs,
            "nl": payload.get("nl", ""),
            "event_id": payload.get("event_id", "evt-unknown"),
        }

    # Censys hosts path → flatten per service/software
    hosts = payload.get("hosts")
    if isinstance(hosts, list):
        out: List[Dict[str, Any]] = []
        for h in hosts:
            services = (h.get("services") or []) if isinstance(h, dict) else []
            for svc in services:
                sw_list = (svc.get("software") or [None]) if isinstance(svc, dict) else [None]
                for sw in sw_list:
                    out.append(_flat_record_from_host_service(h, svc, sw))
        evt = payload.get("event_id") or (payload.get("metadata") or {}).get("description") or "evt-hosts"
        return {"raw_records": out, "nl": payload.get("nl", ""), "event_id": evt}

    # Fallbacks
    if isinstance(payload, list):
        return {"raw_records": payload, "nl": "", "event_id": "evt-unknown"}
    return {
        "raw_records": [],
        "nl": payload.get("nl", "") if isinstance(payload, dict) else "",
        "event_id": payload.get("event_id", "evt-unknown") if isinstance(payload, dict) else "evt-unknown",
    }
