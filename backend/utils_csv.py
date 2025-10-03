from typing import List, Dict, Any

MAX_CSV_ROWS = 200_000


def to_csv(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return ""
    if len(rows) > MAX_CSV_ROWS:
        rows = rows[:MAX_CSV_ROWS]
    cols = sorted({k for r in rows for k in r.keys()})

    def esc(v: Any) -> str:
        s = "" if v is None else str(v)
        return '"' + s.replace('"', '""') + '"'

    lines = [",".join(cols)]
    for r in rows:
        lines.append(",".join(esc(r.get(c)) for c in cols))
    return "\n".join(lines)
