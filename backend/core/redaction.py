import re

_RE = re.compile(r"(api[_-]?key|token|password|secret)\s*[:=]\s*([^\s,;]+)", re.I)


def redact(msg: str | None) -> str:
    if not msg:
        return ""
    return _RE.sub(lambda m: f"{m.group(1)}: [REDACTED]", msg)
