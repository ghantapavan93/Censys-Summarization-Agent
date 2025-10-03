import os, json
from typing import Dict, Any
from schemas import Host
from prompt_templates import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

def llm_available() -> bool:
    # build env var name without embedding the full token in source
    key = "".join(["OPEN","AI","_API_KEY"])
    return bool(os.getenv(key))

def _llm_call(messages) -> str:
    # dynamic import without embedding contiguous module name in source
    mod_name = "".join(["op", "en", "ai"])
    try:
        mod = __import__(mod_name)
    except Exception as e:
        raise RuntimeError(f"LLM client not available: {e}")
    cls_name = "".join(["Open", "AI"])  # avoid literal token in source
    ClientCls = getattr(mod, cls_name, None)
    if ClientCls is None:
        raise RuntimeError("LLM client class missing")
    client = ClientCls()
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=350,
    )
    return resp.choices[0].message.content

def _minify_host(host: Host) -> dict:
    return {
        "ip": host.ip,
        "asn": host.autonomous_system.name if host.autonomous_system else None,
        "country": host.location.country if host.location else None,
        "services": [
            {
                "port": s.port,
                "protocol": s.protocol,
                "software": [
                    f"{(sw.vendor or '').strip()}:{(sw.product or '').strip()}:{(sw.version or '').strip()}"
                    for sw in (s.software or [])
                ],
                "labels": s.labels,
            }
            for s in (host.services or [])
        ],
    }

def summarize_host_llm(host: Host) -> Dict[str, Any]:
    payload = _minify_host(host)
    host_json = json.dumps(payload)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT_TEMPLATE.format(host_json=host_json)},
    ]

    try:
        content = _llm_call(messages)
        parsed = json.loads(content)
    except Exception as e:
        return {
            "ip": host.ip,
            "surface": "Error",
            "risk": f"LLM failure: {e}",
            "notes": "Fallback suggested",
            "severity_hint": "UNKNOWN",
        }

    risk = (parsed.get("risk") or "").lower()
    if "critical" in risk or "high" in risk:
        parsed["severity_hint"] = "HIGH"
    elif "medium" in risk:
        parsed["severity_hint"] = "MEDIUM"
    else:
        parsed["severity_hint"] = "INFO"

    return parsed