from typing import Dict, Any, List, Tuple, Optional
from .llm_router import run_ollama, LLMRouter
from .metrics import SUMMARIZE_TOTAL, SUMMARIZE_LATENCY, time_it
from .delta import dataset_key as _dataset_key, build_risk_snapshot, diff_snapshots, load_snapshot, save_snapshot
from .epss_loader import get_epss
from ..rules.base import run_rules
from .mutes import is_muted
from .rollups import append_rollup
import re, time
from ..core.config import settings


def deterministic_summary(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Deterministic, analyst-grade summary with all features:
    - Executive overview (hosts, countries, unique IPs/ports, severity split)
    - Key risks: title, UPPERCASE severity, risk_score, CVEs, evidence, fix
    - Clusters (product, version, country, count, ports)
    - Top ports & assets by country
    - Highlights (quick stats incl. KEV/CVSS/honeypot)
    - Recommendations (data-aware)
    - Flags/totals for UI charts
    """
    # local imports to adhere to "replace only this function" constraint
    from typing import Optional
    from collections import Counter, defaultdict

    records = records or []

    # ---------- helpers ----------
    def _country(r: Dict[str, Any]) -> Optional[str]:
        loc = r.get("location") or {}
        c = loc.get("country") or r.get("country")
        return c if isinstance(c, str) and c.strip() else None

    def _iter_svcs(r: Dict[str, Any]):
        svcs = r.get("services")
        if isinstance(svcs, list) and svcs:
            for s in svcs:
                yield {
                    "port": s.get("port") or r.get("port"),
                    "product": s.get("product") or r.get("product"),
                    "version": s.get("version") or r.get("version"),
                    "protocol": s.get("protocol") or (r.get("other") or {}).get("protocol"),
                    "cve": s.get("cve") or r.get("cve") or [],
                    "cvss": s.get("cvss") or s.get("cvss_v3") or None,
                    "kev": s.get("kev") or s.get("kev_present") or r.get("kev_present") or False,
                    "ip": r.get("ip"),
                    "other": s.get("other") or r.get("other") or {},
                }
        else:
            yield {
                "port": r.get("port"),
                "product": r.get("product"),
                "version": r.get("version"),
                "protocol": (r.get("other") or {}).get("protocol"),
                "cve": r.get("cve") or [],
                "cvss": r.get("cvss") or r.get("cvss_v3") or None,
                "kev": r.get("kev") or r.get("kev_present") or False,
                "ip": r.get("ip"),
                "other": r.get("other") or {},
            }

    def _sev_from_port(port: Optional[int]) -> str:
        HIGH = {23, 3389, 445, 6379, 9200}
        MED  = {21, 22, 5900, 1883, 8080, 8081, 9090}
        if not isinstance(port, int):
            return "LOW"
        if port in HIGH:
            return "HIGH"
        if port in MED:
            return "MEDIUM"
        return "LOW"

    def _risk_score(port: Optional[int], kev: bool, cvss: Optional[float]) -> float:
        base = {"LOW": 1.0, "MEDIUM": 3.0, "HIGH": 6.0}[_sev_from_port(port)]
        try:
            if cvss is not None and float(cvss) >= 7.0:
                base += 2.5
        except Exception:
            pass
        if kev:
            base += 3.5
        return round(base, 1)

    def _cve_ids(cve_list: Any) -> List[str]:
        out: List[str] = []
        if isinstance(cve_list, list):
            for c in cve_list:
                if isinstance(c, dict) and c.get("id"):
                    out.append(str(c["id"]))
                elif isinstance(c, str):
                    out.append(c)
        return out

    # ---------- tallies ----------
    host_count = len(records)
    ip_set = set()
    country_counter = Counter()
    port_counter = Counter()
    service_count = 0
    kev_total = 0
    cvss7_total = 0
    honeypot_like = 0

    # clusters: (product, version, country) -> {count, ports}
    clusters = defaultdict(lambda: {"count": 0, "ports": set()})

    # ---------- iterate ----------
    risks_raw: List[Dict[str, Any]] = []
    epss_map = get_epss()
    for r in records:
        if r.get("ip"):
            ip_set.add(r["ip"])
        ctry = _country(r)
        if ctry:
            country_counter[ctry] += 1

        labels = r.get("labels") or []
        other = r.get("other") or {}
        asn_name = (other.get("asn_name") or other.get("as_name") or "")
        if (isinstance(labels, list) and any("honeypot" in str(x).lower() for x in labels)) or \
           (isinstance(asn_name, str) and "honeypot" in asn_name.lower()):
            honeypot_like += 1

        for s in _iter_svcs(r):
            service_count += 1
            port = s.get("port") if isinstance(s.get("port"), int) else None
            if isinstance(port, int):
                port_counter[port] += 1

            product = (s.get("product") or "unknown").strip()
            version = (s.get("version") or "unknown").strip()
            k = (product.lower(), version.lower(), ctry or "unknown")
            clusters[k]["count"] += 1
            if port is not None:
                clusters[k]["ports"].add(port)

            # flags
            kev_flag = bool(s.get("kev"))
            if kev_flag:
                kev_total += 1

            try:
                cvss_val = float(s.get("cvss")) if s.get("cvss") is not None else None
            except Exception:
                cvss_val = None
            if isinstance(cvss_val, float) and cvss_val >= 7.0:
                cvss7_total += 1

            # risk item
            sev = _sev_from_port(port)              # already returns UPPERCASE
            score = _risk_score(port, kev_flag, cvss_val)
            cves = _cve_ids(s.get("cve") or [])
            prod_l = product.lower()

            rid_suffix = f"{r.get('ip')}:{port or 'n/a'}:{product.lower() or 'svc'}"
            def _risk(
                title: str, why: str, fix: str,
            ) -> Tuple[str, str, str]:
                return title, why, fix

            if port == 6379 or "redis" in prod_l:
                title = "Redis exposed (6379)"
                why = "Unauthenticated Redis can leak/modify data; modules allow RCE."
                fix = "Restrict to VPC, require AUTH, enable TLS, or disable if unused."
            elif port == 9200 or "elasticsearch" in prod_l:
                title = "Elasticsearch API exposed (9200)"
                why = "Public ES exposes indices and admin APIs."
                fix = "Bind to private nets; add auth/proxy; restrict with network policies."
            elif port in (8080, 8081) or "jenkins" in prod_l:
                title = "Jenkins UI exposed"
                why = "Unauth Jenkins risks credential leakage and build manipulation."
                fix = "Require SSO/auth, enable CSRF, limit ingress to trusted sources."
            elif port == 1883 or "mqtt" in prod_l or "mosquitto" in prod_l:
                title = "MQTT broker open (1883)"
                why = "Often no auth; can broadcast/ingest sensitive telemetry."
                fix = "Require auth/TLS; restrict topics; place behind broker gateway."
            elif port == 21:
                title = "FTP service detected"
                why = "Legacy protocol; cleartext creds/files common."
                fix = "Disable or migrate to SFTP/FTPS; scope to internal."
            elif port == 22:
                title = "OpenSSH exposure"
                why = "Common brute-force surface; outdated versions carry critical CVEs."
                fix = "Keys+MFA, fail2ban; patch to latest LTS; restrict via bastion."
            elif port == 3389:
                title = "RDP exposure"
                why = "High-value target; brute force and RCE history."
                fix = "Close public RDP; require VPN/Bastion; enable NLA."
            elif port == 445:
                title = "SMB exposure"
                why = "Lateral movement & EternalBlue-class exploits."
                fix = "Block SMB from internet; segment; patch consistently."
            elif port == 23:
                title = "Telnet exposure"
                why = "Cleartext authentication; device takeover risk."
                fix = "Disable Telnet; use SSH with keys."
            else:
                title = f"Service exposed on port {port}" if port else "Service exposure detected"
                why = "Publicly reachable service increases attack surface."
                fix = "Restrict exposure; patch and harden configuration."
            # EPSS: take max across related CVEs if known
            epss_vals = [epss_map.get(str(cv).upper(), 0.0) for cv in cves]
            epss_max = max(epss_vals) if epss_vals else 0.0

            # Identity and fingerprints
            rdns = (r.get("dns") or {}).get("hostname") or (r.get("other") or {}).get("rdns")
            asn = ((r.get("autonomous_system") or {}).get("asn") or (r.get("other") or {}).get("asn"))
            org = ((r.get("autonomous_system") or {}).get("name") or (r.get("other") or {}).get("org"))
            http_title = (s.get("other") or {}).get("response_title") or (s.get("other") or {}).get("http_title")
            server = (s.get("other") or {}).get("server") or (s.get("other") or {}).get("http_server")
            fav_hash = (s.get("other") or {}).get("favicon_hash")
            ja3 = (s.get("other") or {}).get("ja3")
            jarm = (s.get("other") or {}).get("jarm")
            # Extract optional banner/tls details
            cert = (s.get("other") or {}).get("certificate") or {}
            tls_details = None
            try:
                if isinstance(cert, dict):
                    tls_details = {
                        "cn": cert.get("subject") or cert.get("cn"),
                        "san": cert.get("san") or cert.get("subject_alt_names") or [],
                        "expiry": cert.get("not_after") or cert.get("expiry"),
                        "protocol": (s.get("other") or {}).get("tls_protocol") or (s.get("other") or {}).get("tls_version"),
                        "cipher": (s.get("other") or {}).get("tls_cipher"),
                        "alpn": (s.get("other") or {}).get("alpn"),
                        "chain": (s.get("other") or {}).get("chain_summary"),
                    }
            except Exception:
                tls_details = None

            # Build evidence with optional TLS/HTTP hints (CN, SAN, http title)
            ev_bits = [f"{s.get('ip')}:{port or 'n/a'} {product} {version}".strip()]
            try:
                title = ((s.get('other') or {}).get('response_title') or (s.get('other') or {}).get('http_title') or None)
                if title:
                    ev_bits.append(f"http.title={title}")
                if tls_details:
                    if tls_details.get('cn'):
                        ev_bits.append(f"tls.cn={tls_details['cn']}")
                    san = tls_details.get('san') or []
                    if isinstance(san, list) and san:
                        ev_bits.append(f"tls.san={','.join(str(x) for x in san[:3])}")
            except Exception:
                pass

            identity = {"hostname": (r.get("hostname") or (r.get("dns") or {}).get("hostname") or None), "rdns": rdns, "cn": (tls_details or {}).get("cn"), "asn": asn, "org": org}
            screenshot_url = None
            if str(s.get("protocol") or "").upper().startswith("HTTP"):
                # Build a lightweight URL to lazy-load screenshots in UI
                screenshot_url = f"/api/screenshot?host={r.get('ip')}&port={port or 80}"

            risks_raw.append({
                "id": f"risk:{(title or 'svc').lower().replace(' ','-')}:{rid_suffix}",
                "title": title,
                "severity": sev,
                "risk_score": score,
                "related_cves": cves,
                "why_it_matters": why,
                "recommended_fix": fix,
                "evidence": ev_bits,
                "kev": kev_flag,
                "cvss": cvss_val,
                "epss": round(float(epss_max), 4) if isinstance(epss_max, (int, float)) else 0.0,
                "details": {
                    "banner": (s.get("other") or {}).get("banner"),
                    "tls": tls_details,
                    "http": {"title": http_title, "server": server, "favicon_hash": fav_hash},
                    "fingerprints": {"ja3": ja3, "jarm": jarm},
                    "identity": identity,
                    "screenshot": screenshot_url,
                },
            })

    # dedupe risks
    sev_rank = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
    dedup: Dict[str, Dict[str, Any]] = {}
    for x in risks_raw:
        key = f"{x['title']}|{x['evidence'][0] if x.get('evidence') else ''}"
        if key not in dedup:
            dedup[key] = x
        else:
            prev = dedup[key]
            if sev_rank.get(x["severity"], 0) > sev_rank.get(prev["severity"], 0):
                prev["severity"] = x["severity"]
            if x["risk_score"] > prev.get("risk_score", 0):
                prev["risk_score"] = x["risk_score"]
            prev["related_cves"] = sorted(set((prev.get("related_cves") or []) + (x.get("related_cves") or [])))

    risks = list(dedup.values())
    # Apply mutes
    visible: List[Dict[str, Any]] = []
    for r in risks:
        m = is_muted(r)
        if m:
            r = dict(r)
            r["muted"] = {"until": m.get("until"), "reason": m.get("reason")}
        visible.append(r)
    risks = visible

    # ---- Rule Packs (P1) ----
    try:
        aux = {"epss": epss_map}
        rule_risks = run_rules(records, aux)
        # Normalize rule risk items to the same structure
        for rr in rule_risks:
            rid = rr.get("id") or f"rule:{rr.get('title') or 'risk'}"
            sev = (rr.get("severity") or "LOW").upper()
            base = {
                "id": rid,
                "title": rr.get("title") or rid,
                "severity": sev,
                "risk_score": float(rr.get("risk_score") or 0.0),
                "related_cves": rr.get("cves") or [],
                "why_it_matters": None,
                "recommended_fix": rr.get("fix") or "",
                "evidence": rr.get("evidence") or [],
                "kev": False,
                "cvss": None,
                "epss": None,
            }
            risks.append(base)
    except Exception:
        pass
    # Sorting per spec: KEV → EPSS≥95% → CVSS≥7 → severity → score
    sev_rank = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
    def _key(r: Dict[str, Any]):
        kevk = 1 if r.get("kev") else 0
        epss95 = 1 if (r.get("epss") is not None and float(r.get("epss") or 0.0) >= 0.95) else 0
        cvss7 = 1 if (r.get("cvss") is not None and float(r.get("cvss") or 0.0) >= 7.0) else 0
        return (kevk, epss95, cvss7, sev_rank.get(str(r.get("severity") or "LOW").upper(), 0), float(r.get("risk_score") or 0.0))
    risks.sort(key=_key, reverse=True)
    # severity matrix for charts
    m = Counter(r["severity"] for r in risks)
    sev_matrix = {"HIGH": m.get("HIGH", 0), "MEDIUM": m.get("MEDIUM", 0), "LOW": m.get("LOW", 0)}

    # top ports & countries (for graphs)
    top_ports = [{"port": p, "count": c} for p, c in port_counter.most_common(10)]
    by_country = [{"country": c, "count": n} for c, n in country_counter.most_common(20)]

    # cluster list
    cluster_list = []
    for (prod, ver, ctry), info in sorted(clusters.items(), key=lambda kv: kv[1]["count"], reverse=True)[:10]:
        cluster_list.append({
            "product": prod,
            "version": ver,
            "country": ctry,
            "count": info["count"],
            "ports": sorted(info["ports"]),
        })

    # executive overview
    # Concise, risk-first, ≤2 lines
    sev_line = f"Severity — HIGH: {sev_matrix['HIGH']} • MEDIUM: {sev_matrix['MEDIUM']} • LOW: {sev_matrix['LOW']}"
    key_risk_bits = []
    if kev_total > 0: key_risk_bits.append("KEV")
    if cvss7_total > 0: key_risk_bits.append("CVSS≥7")
    key_risks_txt = (" and ".join(key_risk_bits) + " findings present. ") if key_risk_bits else ""
    most_port = (top_ports[0]['port'] if top_ports else 'N/A')
    # Optional explicit phrasing for SSH/FTP + uncommon ports
    ssh_ports_present = sorted({p for p, c in port_counter.items() if p in (22, 11558) and c > 0})
    ftp_present = port_counter.get(21, 0) > 0
    STANDARD_PORTS = {80, 443, 22, 21, 3306}
    # Consider uncommon "web/admin" ports as anything observed not in standards and likely HTTP-ish
    uncommon_candidates = [p for p in port_counter.keys() if p not in STANDARD_PORTS]
    uncommon_phrase = "; remaining items are low-severity services on uncommon web/admin ports" if uncommon_candidates else ""
    ssh_phrase = f"OpenSSH ({', '.join(str(p) for p in ssh_ports_present)})" if ssh_ports_present else ""
    ftp_phrase = "FTP (21)" if ftp_present else ""
    lead_phrase = ""
    if ssh_phrase and ftp_phrase:
        lead_phrase = f"{ssh_phrase} and {ftp_phrase}{uncommon_phrase}. "
    elif ssh_phrase:
        lead_phrase = f"{ssh_phrase}{uncommon_phrase}. "
    elif ftp_phrase:
        lead_phrase = f"{ftp_phrase}{uncommon_phrase}. "

    overview = (
        f"{(lead_phrase or '')}{key_risks_txt}Analyzed {host_count} hosts across {len(country_counter)} countries ({len(ip_set)} IPs), {service_count} services, {len(port_counter)} ports; most frequent {most_port}. "
        f"{sev_line}."
    )

    # highlights
    highlights = [
        f"Hosts: {host_count}",
        f"Unique IPs: {len(ip_set)}",
        f"Countries: {len(country_counter)}",
        f"Unique ports: {len(port_counter)}",
        f"Top port: {top_ports[0]['port'] if top_ports else 'N/A'}",
        f"KEV matches: {kev_total}",
        f"CVSS≥7 findings: {cvss7_total}",
        f"Honeypot-like: {honeypot_like}",
    ]

    # recommendations
    recs: List[str] = []
    if kev_total > 0:
        recs.append("Patch KEV-mapped services immediately; prioritize internet-exposed assets.")
    if cvss7_total > 0:
        recs.append("Address CVSS≥7 findings with emergency SLAs and change windows.")
    if any(p["port"] in (23, 445, 3389) for p in top_ports):
        recs.append("Close high-risk services (Telnet/SMB/RDP) from the internet; require VPN/Bastion.")
    if any(p["port"] in (6379, 9200) for p in top_ports):
        recs.append("Harden data stores (Redis/Elasticsearch): auth, network policies, TLS.")
    if not recs:
        recs.append("Maintain patch hygiene; reduce public attack surface via segmentation and WAF.")

    # Build delta view using dataset key and previous snapshot
    dkey = _dataset_key(records)
    curr_snap = build_risk_snapshot(risks)
    prev_snap = load_snapshot(dkey) or {}
    delta = diff_snapshots(prev_snap, curr_snap)
    # Provide a diff_id to key UI pills and caching
    diff_id = f"{dkey}:{len((delta or {}).get('new', []) or [])}-{len((delta or {}).get('resolved', []) or [])}-{len((delta or {}).get('changed', []) or [])}"
    # persist current snapshot for next run
    try:
        save_snapshot(dkey, curr_snap)
    except Exception:
        pass

    # Append rollup for trends
    try:
        append_rollup({
            "hosts": host_count,
            "unique_ips": len(ip_set),
            "services": service_count,
            "countries": len(country_counter),
            "unique_ports": len(port_counter),
        }, {"kev_total": kev_total, "medium_plus": int(sev_matrix.get("MEDIUM", 0)) + int(sev_matrix.get("HIGH", 0))})
    except Exception:
        pass

    return {
        "overview": overview,
        "overview_deterministic": overview,   # for UI
        "key_risks": risks,                   # title, severity, risk_score, CVEs, evidence, fix
        "recommendations": recs,
        "highlights": highlights,
        "severity_matrix": sev_matrix,
        "top_ports": top_ports,
        "assets_by_country": by_country,
        "clusters": cluster_list,
        "totals": {
            "hosts": host_count,
            "unique_ips": len(ip_set),
            "services": service_count,
            "countries": len(country_counter),
            "unique_ports": len(port_counter),
        },
        "flags": {
            "kev_total": kev_total,
            "cvss_high_total": cvss7_total,
            "honeypot_like": honeypot_like,
        },
        "use_llm_available": True,
        "delta": delta,
        "dataset_key": dkey,
        "diff_id": diff_id,
    }


def _trim_for_prompt(base: Dict[str, Any]) -> Dict[str, Any]:
    """Keep only the essentials for the LLM to avoid verbosity and drift."""
    return {
        "overview": base.get("overview_deterministic") or base.get("overview"),
        "key_risks": [
            {
                "title": r.get("title"),
                "severity": r.get("severity"),
                "risk_score": r.get("risk_score"),
                "related_cves": (r.get("related_cves") or [])[:5],
                "kev": r.get("kev"),
                "cvss": r.get("cvss"),
                "epss": r.get("epss"),
            }
            for r in (base.get("key_risks") or [])[:6]
        ],
        "recommendations": (base.get("recommendations") or [])[:4],
        "highlights": (base.get("highlights") or [])[:6],
        "top_ports": (base.get("top_ports") or [])[:5],
        "assets_by_country": (base.get("assets_by_country") or [])[:4],
    }


def build_rewrite_prompt(base: Dict[str, Any]) -> str:
    compact = _trim_for_prompt(base)
    return (
        "Rewrite this dataset summary for an executive audience. Goals:\n"
        "- One-line overview (<= 40 words)\n"
        "- 2-3 bullet-style actions (semicolon-separated)\n"
        "- Keep concrete numbers (hosts, ports, KEV/CVSS)\n"
        "- No markdown, no headings, no emojis.\n\n"
        f"Context (JSON):\n{compact}\n\n"
        "Output format (plain text):\n"
        "Overview: <single sentence>\n"
        "Top actions: <action 1>; <action 2>; <action 3>"
    )


# ---------------- New guarded AI rewrite per spec ----------------

LOCK_KEYS = ("hosts","ips","countries","services","unique_ports","top_port","high","medium","low")


def _cap_words(text: str, max_words: int = 120) -> str:
    w = (text or "").split()
    if len(w) <= max_words:
        return (text or "").strip()
    cut = " ".join(w[:max_words]).rstrip(",;: ")
    p = cut.rfind(".")
    return cut[:p+1] if p != -1 else cut + "…"


def _fact_lock(ai: str, facts: Dict[str, Any], cves: List[str], must_ports: List[int]) -> Tuple[bool, str]:
    t = (ai or "").strip()
    # CVEs must all appear verbatim
    for c in set(cves or []):
        if c and c not in t:
            return False, f"missing CVE {c}"
    # Numbers: if mentioned, must match. Use precise patterns to avoid cross-capturing (e.g., 'hosts across 2 countries').
    def grab_hosts(s: str) -> Optional[int]:
        for rx in (r"(\d+)\s+hosts\b", r"\bhosts\s*[:=]\s*(\d+)"):
            m = re.search(rx, s, re.I)
            if m: return int(m.group(1))
        return None
    def grab_ips(s: str) -> Optional[int]:
        for rx in (r"(\d+)\s+IP[s]?\b", r"\bIP[s]?\b[^0-9]*(\d+)"):
            m = re.search(rx, s, re.I)
            if m: return int(m.group(1))
        return None
    def grab_countries(s: str) -> Optional[int]:
        for rx in (r"(\d+)\s+countries\b", r"\bcountries\b[^0-9]*(\d+)"):
            m = re.search(rx, s, re.I)
            if m: return int(m.group(1))
        return None
    def grab_services(s: str) -> Optional[int]:
        for rx in (r"(\d+)\s+services\b", r"\bservices\b[^0-9]*(\d+)"):
            m = re.search(rx, s, re.I)
            if m: return int(m.group(1))
        return None
    def grab_unique_ports(s: str) -> Optional[int]:
        for rx in (r"(\d+)\s+(?:unique\s+)?ports\b", r"\bunique\s+ports\b[^0-9]*(\d+)"):
            m = re.search(rx, s, re.I)
            if m: return int(m.group(1))
        return None
    def grab_top_port(s: str) -> Optional[int]:
        for rx in (r"\btop\s+port\s*(\d+)", r"\bmost\s+frequent\s*(\d+)"):
            m = re.search(rx, s, re.I)
            if m: return int(m.group(1))
        return None
    def grab_sev(s: str, name: str) -> Optional[int]:
        m = re.search(rf"\b{name}\b\s*[:=]\s*(\d+)", s, re.I)
        return int(m.group(1)) if m else None

    # Compare if present
    got_map = {
        "hosts": grab_hosts(t),
        "ips": grab_ips(t),
        "countries": grab_countries(t),
        "services": grab_services(t),
        "unique_ports": grab_unique_ports(t),
        "top_port": grab_top_port(t),
        "high": grab_sev(t, "HIGH"),
        "medium": grab_sev(t, "MEDIUM"),
        "low": grab_sev(t, "LOW"),
    }
    for k, got in got_map.items():
        if got is None:
            continue
        want_val = facts.get(k, 0)
        try: want = int(want_val)
        except Exception: want = 0
        if got != want:
            return False, f"mismatch {k}: {got}!={want}"
    # Require ports from top risks if provided
    for p in set(must_ports or []):
        if str(p) not in t:
            return False, f"missing port {p}"
    # Digits only (no 'three hosts')
    if re.search(r"\b(one|two|three|four|five|six|seven|eight|nine|ten)\b", t, re.I):
        return False, "number words present"
    # No hedging
    if re.search(r"\b(might|could)\b", t, re.I):
        return False, "hedging language present"
    return True, ""


STYLE_PROMPTS = {
  "executive": "60–120 words, risk-first (KEV/CVSS/EPSS first), then counts, then 2–4 actions. No fluff.",
  "bulleted":  "3–6 concise bullets: Top risks, Affected/ports, Actions. Preserve all numbers/CVEs.",
  "ticket":    "Jira-style: Title, Impact, Affected, Actions, Due-by. Keep counts/CVEs exact."
}


def _extract_structured_from_base(base: Dict[str, Any]) -> Dict[str, Any]:
    """Map our deterministic output into the keys expected by the prompt builder."""
    sev = base.get("severity_matrix") or {}
    totals = base.get("totals") or {}
    top_ports = base.get("top_ports") or []
    risks = base.get("key_risks") or []

    # Extract best-effort ports used in risks from first evidence entry (format: ip:port ...)
    risk_ports: List[int] = []
    for r in risks[:8]:
        ev = (r.get("evidence") or [])
        if ev:
            m = re.search(r":(\d+)\b", str(ev[0]))
            if m:
                try:
                    risk_ports.append(int(m.group(1)))
                except Exception:
                    pass

    # Collect CVEs
    cves: List[str] = []
    for r in risks:
        for c in (r.get("related_cves") or []):
            if isinstance(c, str):
                cves.append(c)

    return {
        "SEVERITY MATRIX": {"HIGH": int(sev.get("HIGH", 0)), "MEDIUM": int(sev.get("MEDIUM", 0)), "LOW": int(sev.get("LOW", 0))},
        "totals": {
            "Hosts": int(totals.get("hosts", 0)),
        },
        "hosts": int(totals.get("hosts", 0)),
        "unique_ips": int(totals.get("unique_ips", 0)),
        "countries": int(totals.get("countries", 0)),
        "services": int(totals.get("services", 0)),
        "unique_ports": int(totals.get("unique_ports", 0)),
        "top_port": int((top_ports[0] or {}).get("port", 0)) if top_ports else 0,
        "RISKS": risks,
        "TOP PORTS": top_ports,
        "_derived": {"risk_ports": risk_ports, "cves": sorted(set(cves))},
    }


def build_prompt(structured: Dict[str, Any], deterministic_text: str, *, style: str = "executive", language: str = "en") -> Tuple[str, str, Dict[str, Any], List[str], List[int]]:
    sev = structured.get("SEVERITY MATRIX", structured.get("severity_matrix", {})) or {}
    facts = {
        "hosts": structured.get("hosts") or (structured.get("Totals", structured.get("totals", {})) or {}).get("Hosts") or 0,
        "ips": structured.get("unique_ips") or 0,
        "countries": structured.get("countries") or 0,
        "services": structured.get("services") or 0,
        "unique_ports": structured.get("unique_ports") or 0,
        "top_port": structured.get("top_port") or 0,
        "high": (sev.get("HIGH") or 0),
        "medium": (sev.get("MEDIUM") or 0),
        "low": (sev.get("LOW") or 0),
    }
    # CVEs from risks
    def _collect_cves() -> List[str]:
        out: List[str] = []
        rs = structured.get("RISKS") or []
        for r in rs:
            for c in (r.get("related_cves") or r.get("cves") or []):
                if isinstance(c, str):
                    out.append(c)
        return sorted(set(out))
    cves = structured.get("_derived", {}).get("cves") or _collect_cves()

    epss_flag = False
    kev_flag = False
    cvss7 = 0
    try:
        rs = structured.get("RISKS") or []
        epss_flag = max([float(r.get("epss") or 0.0) for r in rs] + [0.0]) >= 0.95 if rs else False
        kev_flag = any(bool(r.get("kev")) for r in rs)
        cvss7 = sum(1 for r in rs if (r.get("cvss") is not None and float(r.get("cvss") or 0.0) >= 7.0))
    except Exception:
        pass

    system = settings.ollama_system or (
        "You rewrite a security brief. DO NOT change numeric facts or CVE lists. Never invent new assets/ports/CVEs. Use active voice."
    )
    # Style-specific formatting rules
    style_key = (style or "executive").strip().lower()
    if style_key == "bulleted":
        formatting_rules = (
            "Output 4–6 bullets, each on its own line starting with '• ' (bullet). "
            "Bullet 1 must mention KEV/CVSS/EPSS if present. "
            "Include a bullet listing counts (hosts, countries, services, unique ports, top port). "
            "If uncommon ports are present, include a bullet with the exact phrase 'uncommon web/admin ports (p1, p2, …)'. "
            "End with a bullet that begins 'Actions: ' followed by 2–4 concrete steps separated by semicolons. "
            "Write all numeric values as digits. No hedging (‘might’, ‘could’)."
        )
    elif style_key == "ticket":
        formatting_rules = (
            "Output labeled sections exactly in this order, one per line: "
            "Title: <one-line executive title>. "
            "Impact: <concise business/risk impact>. "
            "Affected: <hosts/ips/countries/services/ports; include 'uncommon web/admin ports (p1, p2, …)' if present>. "
            "Actions: <2–4 steps separated by semicolons>. "
            "Due-by: <SLA like 'KEV ≤ 72h; CVSS≥7 ≤ 14d'>. "
            "The first sentence (in Title or Impact) must reflect KEV/CVSS/EPSS if present. "
            "Write all numeric values as digits. No hedging."
        )
    else:  # executive
        formatting_rules = (
            "One paragraph, 60–120 words. First sentence must mention KEV/CVSS/EPSS if present. "
            "If uncommon web/admin ports are present, include the exact phrase 'uncommon web/admin ports (p1, p2, …)' with the provided list. "
            "End with 'Actions: ' followed by 2–4 concrete steps separated by semicolons. "
            "Write all numeric values as digits. No hedging (‘might’, ‘could’)."
        )
    constraints = (
        f"Facts (lock exactly): {facts}. CVEs (verbatim): {cves}. "
        f"Signal present: KEV={'yes' if kev_flag else 'no'}, CVSS7={cvss7}, EPSS>=95%={'yes' if epss_flag else 'no'}. "
        f"Style: {STYLE_PROMPTS.get(style, STYLE_PROMPTS['executive'])} Language: {language}. "
        f"Formatting rules: {formatting_rules}"
    )
    compact = {
        "top_ports": (structured.get("TOP PORTS") or structured.get("top_ports") or [])[:8],
        "top_risk_ports": (structured.get("_derived", {}).get("risk_ports") or [])[:6],
        "countries": structured.get("ASSETS BY COUNTRY") or structured.get("assets_by_country") or [],
    }
    # Compute uncommon web/admin ports from top_ports (exclude common standards)
    try:
        std = {80, 443, 22, 21, 3306}
        tp = compact.get("top_ports") or []
        uncommon_ports = [int(x.get("port")) for x in tp if isinstance(x, dict) and isinstance(x.get("port"), int) and int(x.get("port")) not in std]
        compact["uncommon_ports"] = uncommon_ports[:8]
    except Exception:
        compact["uncommon_ports"] = []
    prompt = (
        f"{constraints}\n\nDETERMINISTIC DRAFT:\n{deterministic_text}\n\n"
        f"STRUCTURED SIGNALS (compact):\n{compact}\n\nTASK: Produce the rewrite now."
    )
    must_ports = compact.get("top_risk_ports") or []
    return system, prompt, facts, cves, must_ports


def rewrite_with_ai(structured: Dict[str, Any], deterministic_text: str, *, style: str = "executive", language: str = "en") -> Dict[str, Any]:
    system, prompt, facts, cves, must_ports = build_prompt(structured, deterministic_text, style=style, language=language)
    model = settings.ollama_model
    t0 = time.time()
    ai = ""
    error: Optional[str] = None
    try:
        try:
            router = LLMRouter()
            ai = router.complete(prompt, model=model, system=system) or ""
        except Exception:
            # Fallback to CLI
            ai = run_ollama(prompt, model=model) or ""
    except Exception as e:
        error = str(e)
        ai = ""
    latency_ms = int((time.time() - t0) * 1000)

    # Risk-first check: if KEV/CVSS7/EPSS≥95 exist, they must appear in sentence #1
    kev_flag = any(bool(r.get("kev")) for r in (structured.get("RISKS") or []))
    try:
        epss_flag = max([float(r.get("epss") or 0.0) for r in (structured.get("RISKS") or [])] + [0.0]) >= 0.95
    except Exception:
        epss_flag = False
    cvss7_flag = any((r.get("cvss") is not None and float(r.get("cvss") or 0.0) >= 7.0) for r in (structured.get("RISKS") or []))

    def _format_bulleted(text: str) -> str:
        # If already bulleted, return as is
        if any(line.strip().startswith("• ") for line in text.splitlines() if line.strip()):
            return text
        # Split into sentences and convert to bullets without changing wording
        import re as _re
        sentences = [s.strip() for s in _re.split(r"(?<=[\.!?])\s+", text) if s and s.strip()]
        if not sentences:
            return text
        # Move any sentence that begins with 'Actions:' to the end to preserve closing actions
        actions = [s for s in sentences if s.lower().startswith("actions:")]
        rest = [s for s in sentences if s not in actions]
        ordered = rest + actions
        return "\n".join([f"• {s}" for s in ordered])

    ok, reason = _fact_lock(ai, facts, cves, must_ports)
    # If style requires bullets but the model returned a paragraph, format into bullets and re-validate
    if ok and ai and (style or "").strip().lower() == "bulleted":
        ai_bulleted = _format_bulleted(ai)
        if ai_bulleted != ai:
            ai = ai_bulleted
            ok, reason = _fact_lock(ai, facts, cves, must_ports)
    auto_fix_applied = False
    if not ok and ai and isinstance(reason, str) and (reason.startswith("missing CVE ") or reason.startswith("missing port ")):
        # Minimal, safe auto-fix: append any missing CVEs/ports as a short suffix
        missing_cves = [c for c in (cves or []) if c and c not in ai]
        missing_ports = [p for p in (must_ports or []) if str(p) not in ai]
        suffix_bits: List[str] = []
        if missing_cves:
            suffix_bits.append(f"CVEs: {', '.join(missing_cves)}.")
        if missing_ports:
            suffix_bits.append(f"Ports: {', '.join(str(p) for p in missing_ports)}.")
        if suffix_bits:
            ai = (ai.rstrip() + " " + " ".join(suffix_bits)).strip()
            ok, reason = _fact_lock(ai, facts, cves, must_ports)
            auto_fix_applied = ok
    if ok and ai:
        first_sentence = (ai.split(".")[0] or "").strip()
        if kev_flag and "KEV" not in first_sentence:
            ok, reason = False, "risk-first missing KEV"
        if cvss7_flag and "CVSS" not in first_sentence:
            ok, reason = False, "risk-first missing CVSS"
        if epss_flag and "EPSS" not in first_sentence:
            ok, reason = False, "risk-first missing EPSS"
    # Apply word cap primarily to executive paragraph; allow more lines for list/ticket styles
    style_key = (style or "executive").strip().lower()
    if ok and ai:
        if style_key == "executive":
            result_text = _cap_words(ai, 120)
        else:
            # Soft limit: cap at ~160 words to avoid runaway generations but preserve bullets/sections
            result_text = _cap_words(ai, 160)
    else:
        result_text = deterministic_text
    return {
        "text": result_text,
        "final_text": result_text,
        "raw_text": ai or "",
        "used_ai": bool(ai and ok),
        "guard_pass": bool(ok),
        "guard_reason": None if ok else (reason or error or "fallback"),
        "model": model,
        "latency_ms": latency_ms,
        "generated_at": int(time.time() * 1000),
        "auto_fix": bool(auto_fix_applied),
    }


@time_it(SUMMARIZE_LATENCY, rewrite_with_ai="false", llm="none")
def _summarize_only(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    return deterministic_summary(records)


@time_it(SUMMARIZE_LATENCY, rewrite_with_ai="true", llm="ollama")
def _summarize_and_rewrite_ollama(records: List[Dict[str, Any]], model: str, *, style: Optional[str] = None, language: Optional[str] = None) -> Dict[str, Any]:
    base = deterministic_summary(records)
    # Prepare structured signals from base and perform guarded rewrite
    structured = _extract_structured_from_base(base)
    det_text = base.get("overview_deterministic") or base.get("overview") or ""
    lang = (language or settings.language or "en")
    sty = (style or "executive")
    ai_res = rewrite_with_ai(structured, det_text, style=sty, language=lang)
    out = dict(base)
    out["overview_llm"] = ai_res.get("final_text") or ai_res.get("text")
    out["overview_llm_raw"] = ai_res.get("raw_text") or ""
    # Telemetry/meta for UI and logs
    out["ai_overview"] = {
        "used_ai": ai_res.get("used_ai", False),
        "guard_pass": ai_res.get("guard_pass", False),
        "guard_reason": ai_res.get("guard_reason"),
        "model": ai_res.get("model"),
        "latency_ms": ai_res.get("latency_ms"),
        "generated_at": ai_res.get("generated_at"),
        "delta_counts": {
            "new": int((base.get("delta") or {}).get("counts", {}).get("new", 0)),
            "resolved": int((base.get("delta") or {}).get("counts", {}).get("resolved", 0)),
            "changed": int((base.get("delta") or {}).get("counts", {}).get("changed", 0)),
        },
        "auto_fix": ai_res.get("auto_fix", False),
    }
    return out


def summarize(records: List[Dict[str, Any]], rewrite_with_ai: bool, llm_preference: str | None, *, style: Optional[str] = None, language: Optional[str] = None) -> Dict[str, Any]:
    if rewrite_with_ai:
        model = llm_preference or "qwen2.5:7b"
        SUMMARIZE_TOTAL.labels(rewrite_with_ai="true", llm="ollama").inc()
        return _summarize_and_rewrite_ollama(records, model=model, style=style, language=language)
    else:
        SUMMARIZE_TOTAL.labels(rewrite_with_ai="false", llm="none").inc()
        return _summarize_only(records)
