"""Analyst-grade deterministic summarizer (no external LLM deps).

Produces a concise narrative, prioritized risks, concrete recommendations, and highlights
by grouping evidence and ranking exposures using simple heuristics.
"""

from typing import Dict, List, Any, Optional, Tuple, DefaultDict
from collections import defaultdict, Counter
from ..core.logging import log_json
from ..settings import settings
# LLMRouter no longer used for overview polishing; we call Python ollama client directly when requested

PROMPT_VERSION = "analyst_v1"


# Ports weighted by common remote access / risky services (higher = more concerning)
_PORT_SEVERITY = {
    23: 10,  # telnet
    3389: 9, # rdp
    445: 9,  # smb
    21: 8,   # ftp
    22: 7,   # ssh (still common/expected, but exposed widely is risky)
    25: 6,   # smtp
    5900: 6, # vnc
    3306: 5, # mysql
    5432: 5, # postgres
    9200: 5, # elasticsearch
    80: 4,   # http
    443: 3,  # https (lowest of the set)
}


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default


def _format_top(items: List[Dict[str, Any]], n: int) -> List[str]:
    formatted: List[str] = []
    for it in (items or [])[:n]:
        v = str(it.get("value"))
        c = _safe_int(it.get("count"), 0)
        formatted.append(f"{v} ({c})")
    return formatted


def _group_evidence(context_snippets: Optional[List[Dict[str, Any]]]) -> Tuple[Dict[Tuple[str, str, str, str], Dict[str, Any]], Counter]:
    """Group evidence by (product, version, hardware, country) and compute simple stats.

    Returns a mapping group_key -> {
        count: int,
        ports: Counter,
        score_sum: float,
        ids: List[str]
    } and a global country Counter.
    """
    groups: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
    country_counter: Counter = Counter()
    if not context_snippets:
        return groups, country_counter

    for e in context_snippets:
        product = (e.get("product") or "unknown").strip().lower()
        version = (e.get("version") or "").strip().lower()
        hardware = (e.get("hardware") or "na").strip().lower()
        country = (e.get("country") or "").strip().upper()
        gid = (product, version, hardware, country)
        if gid not in groups:
            groups[gid] = {
                "count": 0,
                "ports": Counter(),
                "score_sum": 0.0,
                "risk_sum": 0.0,
                "ids": [],
            }
        g = groups[gid]
        g["count"] += 1
        g["ids"].append(str(e.get("id")))
        g["score_sum"] += float(e.get("score") or 0.0)
        p = _safe_int(e.get("port"))
        if p:
            g["ports"][p] += 1
        # risk contribution: port severity + CVE boost
        cves = e.get("cve") or []
        max_cve = 0.0
        try:
            if isinstance(cves, list) and cves:
                max_cve = max(float((c or {}).get("score", 0.0) or 0.0) for c in cves)
        except Exception:
            max_cve = 0.0
        g["risk_sum"] += float(_PORT_SEVERITY.get(p, 1)) + (max_cve / 3.0)
        if country:
            country_counter[country] += 1
    return groups, country_counter


def _group_risk_score(g: Dict[str, Any]) -> float:
    # Combine per-evidence risk contributions with retrieval score tie-breaker
    size = g.get("count", 0)
    risk_sum = float(g.get("risk_sum", 0.0))
    avg_retr = (g.get("score_sum", 0.0) / max(size, 1))
    return risk_sum + 0.1 * avg_retr


def _compose_narrative(total: int, top_ports: List[str], countries: List[str], top_groups: List[Tuple[Tuple[str, str, str, str], Dict[str, Any]]]) -> str:
    parts: List[str] = []
    parts.append(f"Analyzed {total} records.")
    if top_ports:
        parts.append(f"Common exposed ports: {', '.join(top_ports)}.")
    if countries:
        parts.append(f"Primary geographies: {', '.join(countries)}.")
    if top_groups:
        desc: List[str] = []
        for (product, version, hardware, country), g in top_groups[:3]:
            label = product if product and product != "unknown" else "unknown software"
            if version:
                label += f" {version}"
            if hardware and hardware != "na":
                label += f" on {hardware}"
            port_list = ", ".join([f"{p} ({c})" for p, c in g["ports"].most_common(2)])
            geo = f" in {country}" if country else ""
            if port_list:
                desc.append(f"{label}{geo} with ports {port_list} across {g['count']} assets")
            else:
                desc.append(f"{label}{geo} across {g['count']} assets")
        if desc:
            parts.append("Top clusters: " + "; ".join(desc) + ".")
    return " ".join(parts)


# (removed stray stub of summarize_with_llm)
def summarize_with_llm(insights: Dict[str, Any], context_snippets: Optional[List[Dict]] = None, use_llm: bool = False) -> Dict[str, Any]:
    """Produce a structured, analyst-style summary from insights and evidence.

    Returns a dict with keys: overview, key_risks, recommendations, highlights.
    """
    total = _safe_int((insights or {}).get("count"), 0)
    top_ports_fmt = _format_top((insights or {}).get("top_ports") or [], 3)
    countries_fmt = _format_top((insights or {}).get("countries") or [], 3)

    groups, country_counts = _group_evidence(context_snippets)
    ranked_groups = sorted(groups.items(), key=lambda kv: _group_risk_score(kv[1]), reverse=True)

    # Keep legacy short narrative, but we'll build a richer deterministic overview soon
    overview = _compose_narrative(total, top_ports_fmt, countries_fmt, ranked_groups)

    # Key risks from ports and concentrations
    key_risks: List[str] = []
    # 1) High-risk port exposures
    port_counter: Counter = Counter()
    if context_snippets:
        port_counter = Counter([_safe_int(e.get("port")) for e in context_snippets if _safe_int(e.get("port"))])
        if port_counter:
            top_port, top_cnt = max(port_counter.items(), key=lambda kv: kv[1])
            sev = _PORT_SEVERITY.get(top_port, 1)
            if sev >= 7:
                key_risks.append(f"Widespread exposure of high-risk service on port {top_port} across {top_cnt} assets.")
            else:
                key_risks.append(f"Significant surface on port {top_port} across {top_cnt} assets.")

    # 2) Geo concentration
    if country_counts:
        top_country, ccnt = max(country_counts.items(), key=lambda kv: kv[1])
        if ccnt >= max(5, int(0.1 * max(total, ccnt))):
            key_risks.append(f"Asset concentration in {top_country} ({ccnt} assets) may amplify localized risk.")

    # 3) Product/version clusters
    if ranked_groups:
        (product, version, hardware, country), g = ranked_groups[0]
        label = product if product and product != "unknown" else "an unknown product"
        ver = f" {version}" if version else ""
        hw = f" on {hardware}" if hardware and hardware != "na" else ""
        geo = f" in {country}" if country else ""
        key_risks.append(f"{g['count']} assets running{ver} {label}{hw}{geo} with exposed ports {', '.join(str(p) for p,_ in g['ports'].most_common(3))}.")

    # Recommendations aligned to risks
    recommendations: List[str] = []
    if context_snippets and port_counter:
        # Target top riskiest known ports first
        hot_ports = [p for p, _ in port_counter.most_common(5) if _PORT_SEVERITY.get(p, 0) >= 7]
        if hot_ports:
            recommendations.append(f"Immediately restrict external access to {', '.join(map(str, hot_ports))}; require VPN or bastion.")
    if ranked_groups:
        recommendations.append("Patch and standardize top product/version clusters; enforce configuration baselines.")
    if total >= 50:
        recommendations.append("Roll out network-level segmentation and rate limiting for high-volume services.")
    recommendations.append("Enable detailed logging and alerts on administrative and remote access services.")

    # Highlights for UI cards
    highlights: List[str] = []
    for (product, version, hardware, country), g in ranked_groups[:3]:
        label = product if product and product != "unknown" else "unknown software"
        if version:
            label += f" {version}"
        if hardware and hardware != "na":
            label += f" on {hardware}"
        geo = f" in {country}" if country else ""
        top_p = ", ".join([str(p) for p, _ in g["ports"].most_common(2)])
        if top_p:
            highlights.append(f"{label}{geo}: {g['count']} assets; ports {top_p}")
        else:
            highlights.append(f"{label}{geo}: {g['count']} assets")

    # Fallbacks if evidence was empty
    if not context_snippets:
        if not overview:
            overview = f"Analyzed {total} records. No specific evidence available; review top software and countries."
        if not highlights:
            for it in ((insights or {}).get("top_software") or [])[:3]:
                highlights.append(f"Software: {it.get('value')} x{_safe_int(it.get('count'), 0)}")
        if not key_risks and (insights or {}).get("top_ports"):
            p0 = (insights or {}).get("top_ports")[0]
            key_risks.append(f"Concentration on port {p0.get('value')} across {p0.get('count')} assets may indicate exposure risk.")

    # ---- Additional: derive concrete risks and simple charts from available context ----
    def _hist(records: List[Dict[str, Any]], key: str, topn: int = 10) -> List[Dict[str, Any]]:
        def _get_nested(d: Dict[str, Any], path: str):
            if not isinstance(d, dict):
                return None
            cur = d
            for part in path.split("."):
                if isinstance(cur, dict) and part in cur:
                    cur = cur[part]
                else:
                    return None
            return cur
        c = Counter()
        for r in records or []:
            v = r.get(key) if isinstance(r, dict) else None
            if v in (None, "") and "." in key:
                v = _get_nested(r, key) if isinstance(r, dict) else None
            if v not in (None, ""):
                c[str(v)] += 1
        return [{"label": k, "value": v} for k, v in c.most_common(topn)]

    def _derive_risks(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        risks: List[Dict[str, Any]] = []
        for r in records or []:
            product_upper = str(r.get("product") or "").upper()
            other = r.get("other") or {}
            # CVEs are provided in context as list of dicts under key 'cve'
            cve_list = r.get("cve") or []
            cve_ids = [c.get("id", "") for c in cve_list if isinstance(c, dict)]
            # SSH CVEs
            if product_upper == "SSH" and cve_ids:
                sev = "medium"
                if any(i.startswith("CVE-2024-6387") for i in cve_ids):
                    sev = "high"
                if any(i.startswith("CVE-2023-38408") for i in cve_ids):
                    sev = "high"  # treat critical as high for matrix
                risks.append({
                    "id": f"risk:ssh-cve:{r.get('ip')}:{r.get('port')}",
                    "affected_assets": 1,
                    "context": f"SSH service with CVEs {', '.join(cve_ids)} on {r.get('ip')}:{r.get('port')}",
                    "severity": sev,
                    "likelihood": "high" if sev == "high" else "medium",
                    "impact": "high" if sev == "high" else "medium",
                })
            # Cobalt Strike
            mal_name = str(other.get("malware_name") or other.get("malware") or "")
            if mal_name.lower() == "cobalt strike":
                risks.append({
                    "id": f"risk:cobalt:{r.get('ip')}:{r.get('port')}",
                    "affected_assets": 1,
                    "context": f"Cobalt Strike C2 indicator on {r.get('ip')}:{r.get('port')}",
                    "severity": "high",
                    "likelihood": "high",
                    "impact": "high",
                })
            # TLS SAN private IPs
            san = other.get("cert_san") or []
            if isinstance(san, list) and any(isinstance(x, str) and (x.startswith("10.") or x.startswith("192.168.") or x.startswith("172.16.")) for x in san):
                risks.append({
                    "id": f"risk:priv-san:{r.get('ip')}:{r.get('port')}",
                    "affected_assets": 1,
                    "context": f"TLS cert SAN contains private IPs on {r.get('ip')}:{r.get('port')}",
                    "severity": "medium",
                    "likelihood": "medium",
                    "impact": "medium",
                })
            # FTP over TLS self-signed
            tls_enabled = bool(other.get("tls_enabled"))
            self_signed = bool(other.get("cert_self_signed"))
            if product_upper == "FTP" and tls_enabled and self_signed:
                risks.append({
                    "id": f"risk:ftp-tls-self:{r.get('ip')}:{r.get('port')}",
                    "affected_assets": 1,
                    "context": f"FTP over TLS uses self-signed certificate on {r.get('ip')}:{r.get('port')}",
                    "severity": "medium",
                    "likelihood": "medium",
                    "impact": "medium",
                })
            # MySQL error disclosure
            if product_upper == "MYSQL" and other.get("error_message"):
                risks.append({
                    "id": f"risk:mysql-error:{r.get('ip')}:{r.get('port')}",
                    "affected_assets": 1,
                    "context": f"MySQL access error reveals policy: {other.get('error_message')}",
                    "severity": "low",
                    "likelihood": "low",
                    "impact": "low",
                })
        return risks

    derived_risks = _derive_risks(context_snippets or [])
    risk_matrix = {
        "high": sum(1 for r in derived_risks if r.get("severity") == "high"),
        "medium": sum(1 for r in derived_risks if r.get("severity") == "medium"),
        "low": sum(1 for r in derived_risks if r.get("severity") == "low"),
    }
    # Always use all normalized records for charts
    records_for_hist = (insights or {}).get("records") or []
    viz_payload = {
        "charts": [
            {"type": "bar", "title": "Top Ports", "data": _hist(records_for_hist, "port")},
            {"type": "bar", "title": "Protocols", "data": _hist(records_for_hist, "protocol")},
            {"type": "bar", "title": "Software", "data": _hist(records_for_hist, "product")},
            {"type": "bar", "title": "Countries", "data": _hist(records_for_hist, "location.country")},
        ],
        "histograms": {
            "protocols": _hist(records_for_hist, "protocol"),
            "products": _hist(records_for_hist, "product"),
            "countries": _hist(records_for_hist, "location.country"),
        },
        "top_ports": _hist(records_for_hist, "port"),
        "time_buckets": [],
    }

    # Build enhanced deterministic overview using all records and cluster info
    def _overview_deterministic(records: List[Dict[str, Any]], clusters: List[Tuple[Tuple[str, str, str, str], Dict[str, Any]]], risks: List[Dict[str, Any]]) -> str:
        total_records = len(records or [])
        unique_ips = len({r.get("ip") for r in (records or []) if isinstance(r, dict) and r.get("ip")})
        def _country_of(r: Dict[str, Any]) -> Optional[str]:
            if not isinstance(r, dict):
                return None
            loc = r.get("location") or {}
            return (loc or {}).get("country")
        countries = { _country_of(r) for r in (records or []) if _country_of(r) }
        num_countries = len(countries)

        port_counts = Counter(r.get("port") for r in (records or []) if isinstance(r, dict) and r.get("port"))
        top_ports = ", ".join([f"{p} ({c})" for p, c in port_counts.most_common(3)]) or "none"

        high = sum(1 for rr in (risks or []) if rr.get("severity") == "high")
        medium = sum(1 for rr in (risks or []) if rr.get("severity") == "medium")
        low = sum(1 for rr in (risks or []) if rr.get("severity") == "low")

        cluster_descs: List[str] = []
        for key, meta in (clusters or [])[:3]:
            product, version, os_name, country = key
            ports_str = ", ".join([str(p) for p, _ in (meta.get("ports") or Counter()).most_common(3)]) if isinstance(meta.get("ports"), Counter) else "unknown"
            cluster_descs.append(f"{product or 'unknown'} {version or ''} in {country or 'UNKNOWN'} ({meta.get('count', 0)} assets, ports {ports_str})".strip())
        clusters_str = "; ".join(cluster_descs) or "no clusters detected"

        return (
            f"Analyzed {total_records} services across {num_countries} countries "
            f"({unique_ips} unique IPs). Top 3 ports: {top_ports}. "
            f"Risk profile: {high} high, {medium} medium, {low} low severity issues. "
            f"Top clusters: {clusters_str}."
        )

    # Strict Ollama rewrite helper (Python client, plain text enforcement)
    def _overview_ollama(det_summary: str, model: str | None = None, style: str | None = None) -> str:
        import os, re
        model = model or os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        style = (style or os.getenv("OVERVIEW_STYLE", "one-line")).strip().lower()
        try:
            import ollama  # type: ignore
        except Exception:
            return det_summary

        # prompt variants
        if style == "two-three":
            prompt = (
                "Rewrite the following technical summary into 2-3 concise executive sentences. "
                "KEEP ALL FACTS EXACT. Use max 75 words. Output as plain text only. NO markdown or headings.\n\n"
                f"{det_summary}\n"
            )
        elif style == "house-md":
            prompt = (
                "Rewrite into a short executive overview using this exact format:\n"
                "**Executive summary:** <one sentence>\n"
                "**Key risks:** <one sentence>\n"
                "**Actions:** <one sentence>\n"
                "KEEP ALL FACTS EXACT.\n\n"
                f"{det_summary}\n"
            )
        else:  # one-line default
            prompt = (
                "Rewrite the following technical summary into ONE concise executive sentence. "
                "KEEP ALL FACTS EXACT. Use max 35 words. Output as plain text only. "
                "NO markdown, NO lists, NO headings—just one sentence.\n\n"
                f"{det_summary}\n"
            )

        def _norm(s: str) -> str:
            s = re.sub(r'[#*_`>\-\[\]\(\)]+', ' ', s)
            s = re.sub(r'\s+', ' ', s).strip()
            return s

        def _limit(text: str, max_sents: int, max_words: int) -> str:
            parts = re.split(r'(?<=[.!?])\s+', text)
            text = ' '.join(parts[:max_sents]).strip() if max_sents > 0 else text.strip()
            words = text.split()
            if len(words) > max_words:
                text = ' '.join(words[:max_words]).rstrip(",;:")
            if text and text[-1] not in ".!?":
                text += "."
            return text

        def _call():
            try:
                r = ollama.chat(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a precise executive rewriter. Output plain text only."},
                        {"role": "user", "content": prompt},
                    ],
                    options={"temperature": 0},
                    stream=False,
                )
                return r.get("message", {}).get("content", "")
            except AttributeError:
                r = ollama.generate(model=model, prompt=prompt, options={"temperature": 0}, stream=False)
                return r.get("response", "")

        try:
            raw = _call()
            if style == "house-md":
                # keep markdown-like structure, just trim to three lines
                lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
                return "\n".join(lines[:3]) or det_summary
            # plain-text variants
            txt = _norm(raw)
            if style == "two-three":
                return _limit(txt, max_sents=3, max_words=75) or det_summary
            return _limit(txt, max_sents=1, max_words=35) or det_summary
        except Exception:
            return det_summary

    # Always use all normalized records for charts and overviews
    records_for_hist = (insights or {}).get("records") or []
    det_overview = _overview_deterministic(records_for_hist, ranked_groups, derived_risks)
    # Call Ollama only when requested; otherwise keep deterministic
    try:
        llm_overview = _overview_ollama(det_overview) if use_llm else det_overview
    except Exception:
        llm_overview = det_overview
    # Final summary is deterministic unless rewrite is requested and succeeded
    final_summary = llm_overview if use_llm and (llm_overview or "").strip() else (det_overview or overview or "No significant patterns detected.")
    final_overview = final_summary

    log_json("analyst_summary_built", groups=len(groups), highlights=len(highlights))
    return {
        # Safe default summary, with optional auto-fallback when enabled
        "summary": final_summary,
        # Keep explicit overviews for UI choice
        "overview": final_overview,
        "overview_deterministic": det_overview,
        "overview_llm": (llm_overview or None),
        "use_llm_available": bool(
            use_llm
            and (llm_overview or "")
            and (llm_overview.strip() != (det_overview or "").strip())
        ),
        "key_risks": key_risks,
        "recommendations": recommendations,
        "highlights": highlights,
        # extended payloads (optional consumers)
        "derived_risks": derived_risks,
        "risk_matrix": risk_matrix,
        "viz_payload": viz_payload,
    }


def get_prompt_info() -> Dict[str, str]:
    return {
        "version": PROMPT_VERSION,
        "description": "Analyst-grade deterministic summarizer (no external LLM)",
        "schema_fields": "overview, key_risks, recommendations, highlights",
    }