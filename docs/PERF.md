Performance profiling

This repo includes a tiny profiling harness to measure end-to-end latency and stage timings via the public API.

Prereqs
- Backend running locally on http://127.0.0.1:8000
- Python env with requests installed (pip install requests)

Run

```powershell
# From repo root (Windows PowerShell)
python tools/profile_run.py --url http://127.0.0.1:8000 --payload backend/examples/input_sample.json --repeat 5
```

Output
- Prints per-run wall time and the server-reported timings_ms per stage
- Prints the average wall time

Notes
- The timings_ms are computed server-side in `backend/agent/graph.py` and reflect rough elapsed durations for retrieval and summarization stages.
- For larger inputs, expect insights and retrieval to dominate; try your own dataset by changing `--payload`.
