import json
import datetime as dt
from pathlib import Path

def enrich_host(h: dict) -> dict:
    services = h.get("services", [])
    # Highest CVSS
    cvss = [v.get("cvss_score") for s in services for v in s.get("vulnerabilities", []) if isinstance(v.get("cvss_score"), (int, float))]
    highest = max(cvss) if cvss else None
    # KEV (rough heuristic from description)
    kev = sorted({v.get("cve_id") for s in services for v in s.get("vulnerabilities", []) if isinstance(v.get("description"), str) and "Known exploited" in v.get("description", "")})
    # TLS present
    has_tls = any(s.get("tls_enabled") or (s.get("tls", {}).get("enabled") if isinstance(s.get("tls"), dict) else False) for s in services)
    # Service names
    names = sorted({s.get("protocol") or s.get("service_name") for s in services if s.get("protocol") or s.get("service_name")})

    h["derived"] = {
        "open_ports_count": len(services),
        "service_names": names,
        "highest_cvss": highest,
        "kev_cves": [x for x in kev if x],
        "has_tls": bool(has_tls),
        "malware_families": sorted({
            *([*h.get("threat_intelligence", {}).get("malware_families", [])] if h.get("threat_intelligence") else []),
            *[s.get("malware_detected", {}).get("name") for s in services if isinstance(s.get("malware_detected"), dict) and s.get("malware_detected", {}).get("name")]
        })
    }

    rl = (h.get("threat_intelligence", {}) or {}).get("risk_level", "low").lower()
    base = {"critical": 50, "high": 35, "medium": 20, "low": 10}.get(rl, 10)
    score = int(base + (highest or 0) * 3 + (15 if h["derived"]["kev_cves"] else 0))
    factors = []
    if h["derived"]["kev_cves"]:
        factors.append("KEV present: " + ",".join(h["derived"]["kev_cves"]))
    if any(s.get("protocol") == "FTP" and (s.get("tls_enabled") or (isinstance(s.get("certificate"), dict) and s.get("certificate", {}).get("self_signed"))) for s in services):
        factors.append("FTP TLS self-signed")
    if any(s.get("protocol") == "HTTP" and isinstance(s.get("response_details"), dict) and s["response_details"].get("status_code") == 200 and s["response_details"].get("title", "").startswith("404") for s in services):
        factors.append("HTTP 200 with 404 title")

    h["risk"] = {"risk_level": rl, "risk_score": score, "risk_factors": factors}
    return h


def main(src: str, dest: str):
    p = Path(src)
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    # Detect if this is a shaped single-document or NDJSON array
    if isinstance(data, dict) and "hosts" in data:
        hosts = data.get("hosts", [])
        data["metadata"]["schema_version"] = "1.1"
        data["metadata"]["seen_at"] = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        data["hosts"] = [enrich_host(h) for h in hosts]
        out = data
    else:
        # Assume NDJSON read from list
        hosts = data if isinstance(data, list) else []
        out = {
            "metadata": {
                "description": "Censys host data",
                "created_at": dt.date.today().isoformat(),
                "data_sources": ["censys_hosts"],
                "hosts_count": len(hosts),
                "ips_analyzed": [h.get("ip") for h in hosts if isinstance(h, dict) and h.get("ip")]
            },
            "hosts": [enrich_host(h) for h in hosts if isinstance(h, dict)]
        }
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Wrote {dest}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("src", help="Source JSON (shaped JSON or NDJSON converted to JSON array)")
    ap.add_argument("dest", help="Output enriched JSON path")
    args = ap.parse_args()
    main(args.src, args.dest)
