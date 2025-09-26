import os, json
from typing import Dict, Any
from schemas import Host
from prompt_templates import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

def llm_available() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))

def _openai_call(messages) -> str:
    from openai import OpenAI
    client = OpenAI()
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
        content = _openai_call(messages)
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
import os, json
from typing import Dict, Any
from schemas import Host
from prompt_templates import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

def llm_available() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))

def _openai_call(messages) -> str:
    from openai import OpenAI
    client = OpenAI()
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
        content = _openai_call(messages)
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
