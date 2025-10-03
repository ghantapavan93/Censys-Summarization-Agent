def looks_like_honeypot(host: dict) -> bool:
    labels = {str(l).upper() for l in (host.get("labels") or [])}
    if "HONEYPOT" in labels:
        return True
    asn_name = (host.get("autonomous_system") or {}).get("name", "")
    if asn_name == "AMAZON-02" and (host.get("service_count") or 0) >= 49:
        return True
    return False


def allowed_host(host: dict, max_services: int = 45, exclude_honeypots: bool = True) -> bool:
    if exclude_honeypots and looks_like_honeypot(host):
        return False
    if (host.get("service_count") or 0) > max_services:
        return False
    return True
