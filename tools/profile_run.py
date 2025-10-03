import json
import time
from pathlib import Path
from typing import Any, Dict

import requests


def run_once(base_url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    t0 = time.perf_counter()
    r = requests.post(f"{base_url}/query-assistant", json=payload, timeout=60)
    elapsed = time.perf_counter() - t0
    r.raise_for_status()
    data = r.json()
    timings = ((data.get("meta") or {}).get("timings_ms") or {})
    return {
        "status": r.status_code,
        "elapsed_s": elapsed,
        "timings_ms": timings,
    }


def main():
    import argparse
    p = argparse.ArgumentParser(description="Profile summarization pipeline via HTTP")
    p.add_argument("--url", default="http://127.0.0.1:8000", help="Backend base URL")
    p.add_argument("--payload", default="backend/examples/input_sample.json")
    p.add_argument("--repeat", type=int, default=5)
    args = p.parse_args()

    payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
    # If file is a list of hosts, wrap into {hosts: [...]} per API
    if isinstance(payload, list):
        payload = {"hosts": payload}

    results = []
    for i in range(args.repeat):
        out = run_once(args.url, payload)
        print(f"Run {i+1}: {out['elapsed_s']*1000:.1f} ms | stage timings(ms)={out['timings_ms']}")
        results.append(out)

    avg = sum(r["elapsed_s"] for r in results) / max(len(results), 1)
    print(f"Average wall time: {avg*1000:.1f} ms over {len(results)} runs")


if __name__ == "__main__":
    main()
