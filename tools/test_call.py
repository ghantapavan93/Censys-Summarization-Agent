import json
import os
import pathlib
import sys

try:
    import requests
except ImportError:
    print("This script requires the 'requests' package. Install with: python -m pip install requests", file=sys.stderr)
    sys.exit(1)

URL = os.environ.get("CENSAI_URL", "http://127.0.0.1:8000/summarize")

def main():
    src = pathlib.Path("examples/hosts_dataset.json")
    if not src.exists():
        print(f"Dataset not found: {src}", file=sys.stderr)
        sys.exit(2)
    data = json.loads(src.read_text(encoding="utf-8"))

    # Build a broader query to avoid bias toward OpenSSH-only matches
    nl = "ssh OR cobalt strike OR nginx OR ftp OR mysql OR bt panel"

    # Prefer sending under 'hosts' so the server's normalizer flattens correctly
    if isinstance(data, dict) and "hosts" in data:
        payload = {
            "hosts": data["hosts"],
            "nl": nl,
            "event_id": "evt-hosts-dataset",
            # optional hints the server may ignore
            "topk": 25,
        }
    elif isinstance(data, dict) and ("raw_records" in data or "records" in data):
        payload = {**data, "nl": nl, "event_id": data.get("event_id", "evt-hosts-dataset"), "topk": 25}
    elif isinstance(data, list):
        payload = {"raw_records": data, "nl": nl, "event_id": "evt-list", "topk": 25}
    else:
        print("Unrecognized dataset shape; expected dict with 'hosts' or 'raw_records'/'records', or a list.", file=sys.stderr)
        sys.exit(3)

    # Simple size hint for logs
    count_hint = (
        len(payload.get("hosts", [])) if isinstance(payload, dict) and "hosts" in payload
        else len(payload.get("raw_records", [])) if isinstance(payload, dict) and "raw_records" in payload
        else (len(payload.get("records", [])) if isinstance(payload, dict) and "records" in payload else 0)
    )
    print(f"Sending payload to {URL} ... (items: {count_hint})")
    resp = requests.post(URL, json=payload, timeout=60)
    try:
        resp.raise_for_status()
    except Exception as e:
        print(f"Request failed: {e}\nBody: {resp.text}", file=sys.stderr)
        sys.exit(4)

    print(json.dumps(resp.json(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
