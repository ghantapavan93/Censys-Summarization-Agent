# Censys Summarization Agent — Architecture and Implementation Guide

This document explains the entire codebase end-to-end so engineers and LLMs can understand, extend, and operate the system confidently. It maps each module to the A→Z pipeline, details data contracts, configuration, error modes, and includes a practical runbook.

Last updated: 2025-09-29

## 1. Purpose and scope

Analyze Censys host data to produce security insights and a concise executive overview:
- Deterministic analytics (no LLM required)
- Retrieval-based evidence selection (TF‑IDF)
- Rule-derived risks and risk matrix
- Optional local LLM (Ollama) rewrite of the overview
- Visual payload (charts/histograms) for UI or reporting

## 2. Repository map (what each folder/file does)

Top level:
- `backend/` — FastAPI service and the entire analysis pipeline
- `frontend/` — Optional React UI (uploads JSON, displays insights)
- `tests/` — Pytests for schemas, analytics, smoke, and overviews
- `examples/` — Sample inputs for quick tests
- `compose*.yaml`, `docker-compose*.yml`, `Dockerfile` — containerization
- `Makefile`, `README.md`, `run.ps1` — DX and quickstart

Backend core:
- `backend/app.py` — HTTP API (POST /summarize, /query-assistant, GET /debug_llm, /config, /explain)
- `backend/agent/graph.py` — Pipeline orchestration (extract → insights → retrieve → summarize → risks → viz → response)
- `backend/agent/state.py` — Typed state passed through the pipeline
- `backend/services/input_normalizer.py` — Accepts multiple input shapes; flattens Censys hosts to records
- `backend/services/ingest.py` — Canonicalizes raw fields into `Record` via `FieldMap`, extracts CVEs, normalizes country
- `backend/services/analytics.py` — Deterministic dataset insights (top ports/protocols/software/ASNs/countries)
- `backend/services/retrieval.py` — TF‑IDF corpus and similarity search for relevant context (pure Python, deterministic)
- `backend/services/ai_summarizer.py` — Deterministic summary builder; optional Ollama rewrite (style variants)
- `backend/services/llm_router.py` — Minimal Ollama HTTP client (not used in main summarization path)
- `backend/core/config.py` — Settings (retrieval_k, LLM parameters, version)
- `backend/core/logging.py` — JSON structured logging helpers
- `backend/models.py` — Canonical typed models for inputs and `CensAIResponse`
- `backend/schemas.py` — Censys Host/Service/Software ASN/Location schemas
- `backend/prompt_templates.py`, `backend/summarizer_llm.py`, `backend/summarizer_rule.py` — Legacy/aux summarizers (not used by the agent pipeline)

Frontend:
- `frontend/src/App.tsx` — Top-level app wiring
- `frontend/src/components/*` — Upload panel, Insights panel, Summary card (built for an older response shape)
- `frontend/src/lib/api.ts` — Fetch helpers (proxy `/api` → backend)
- `frontend/vite.config.ts` — Dev proxy

## 3. Data contracts (inputs and outputs)

### 3.1 Canonical Record (backend/models.py)
```
Record {
  id: string
  ip: string
  port: int
  product?: string
  version?: string
  hardware?: string
  country?: string   // ISO-2 preferred
  cve?: Array<{ id: string, score?: number }>
  other?: { [key: string]: any }
}
```

Notes:
- `other` may include: protocol (string), tls_enabled, cert_self_signed, cert_san (list), malware_name/type/confidence, error_message, asn, etc.
- CVEs are normalized with regex if present in free text.

### 3.2 Censys Host (backend/schemas.py)
```
Host {
  ip: string
  location?: { country?: string, city?: string, province?: string }
  autonomous_system?: { asn?: number, name?: string, ... }
  services?: Array<{
    port?: number, protocol?: string, banner?: string,
    software?: Array<{ product?: string, vendor?: string, version?: string }>,
    labels?: string[]
  }>
}
```

### 3.3 Response (CensAIResponse, backend/models.py)
```
{
  summary: string,
  overview_deterministic?: string,
  overview_llm?: string,
  use_llm_available?: boolean,
  key_findings: Array<{ id: string, title: string, evidence_ids: string[] }>,
  risks: Array<{ id: string, affected_assets: number, context: string, severity: string, likelihood: string, impact: string }>,
  risk_matrix: { high: number, medium: number, low: number },
  query_trace: { nl?: string, query?: string, topk?: number },
  viz_payload: {
    charts: Array<{ type: string, title: string, data: Array<[string, number]> }>,
    histograms?: { [k: string]: { [label: string]: number } },
    top_ports?: { [port: string]: number }
  },
  next_actions: string[],
  meta: {
    event_id: string, record_count: number, generated_at: string, version: string,
    total_records: number, invalid_records: number,
    timings_ms: { validation: number, insights: number, retrieval: number, summarization: number, total: number }
  }
}
```

## 4. Control flow (sequence)

ASCII sequence for POST /query-assistant (identical for /summarize):

```
Client → FastAPI (/query-assistant)
  └─ normalize_input(payload)            # services/input_normalizer.py
      ├─ If hosts[] → flatten per service/software to raw_records
      └─ Else pass through records/raw_records
  └─ canonicalize_records(raw_records)   # services/ingest.py
      ├─ FieldMap to Record mapping (id/ip/port/product/version/hardware/country/cve)
      ├─ Extract CVEs via regex (from arrays or free text)
      └─ Normalize country (ISO-2 where possible)
  └─ run_pipeline(records, nl, event_id, topk?, use_llm?) # agent/graph.py
      ├─ extract_records → record_count
      ├─ generate_insights_step(records) → top_* + attach insights.records
      ├─ generate_summary_step
      │   ├─ TF‑IDF ensure_index(retrieval.py)
      │   ├─ Build query from nl or derived seeds
      │   ├─ retrieve top‑k context
      │   └─ summarize_with_llm(insights, context, use_llm) # services/ai_summarizer.py
      │       ├─ Group evidence by (product,version,hardware,country)
      │       ├─ Deterministic overview/key_risks/recommendations/highlights
      │       ├─ Derived risks + risk_matrix + viz_payload
      │       └─ Optional: Ollama rewrite of overview (style: one-line|two-three|house-md)
      ├─ Combine concrete risks + port risks → RiskMatrix
      ├─ _viz_from_insights → charts/histograms
      └─ Build CensAIResponse (summary/overviews/findings/risks/viz/meta)
  ← Return JSON (CensAIResponse)
```

## 5. Deterministic analytics and risks

Insights (services/analytics.py):
- Count distribution for ports/protocols/software/ASNs/countries.
- Protocol inference fallback when protocol is absent.

Risk derivation (agent/graph.py and ai_summarizer.py):
- SSH CVEs (special handling for CVE‑2024‑6387, CVE‑2023‑38408)
- Cobalt Strike indicators (malware_name)
- TLS SAN with private IPs (10./192.168./172.16.)
- FTP over TLS with self‑signed cert
- MySQL error message disclosure
- Dataset‑level port exposure risks (Telnet/RDP/SMB/SSH/VNC weighting)

## 6. Retrieval (TF‑IDF engine)

Module: `services/retrieval.py`
- Document text: ip, port, product, version, hardware, country, CVE IDs, and scalar fields in `other`.
- Tokenizer: unicode friendly, stop‑words removed, lowercase, len>1.
- IDF smoothing: `idf = log((N+1)/(df+1)) + 1`; rows L2-normalized.
- Query fallback: uniform vector when NL empty or OOV → ensures non‑empty top‑k.
- Top‑k selection: argpartition + local ordering.

## 7. Summarization (deterministic + optional Ollama rewrite)

Module: `services/ai_summarizer.py`
- Group by (product, version, hardware, country); accumulate ports, counts, retrieval score.
- Risk score: port severity + max(CVE score)/3 + small retrieval tie‑breaker.
- Overview text (deterministic):
  - Records analyzed, top ports, geographies, risk profile counts, top clusters.
- key_risks, recommendations, highlights built from ranked clusters and distributions.
- viz_payload: bar charts + histograms for ports/protocols/software/countries.
- Optional rewrite with Ollama (Python client):
  - Env: `OLLAMA_MODEL` (e.g., `qwen2.5:7b`), `OVERVIEW_STYLE` (`one-line`|`two-three`|`house-md`).
  - Strict plain text enforcement; clamp sentences and words; fallback to deterministic on error.
  - Response fields: `overview_deterministic`, `overview_llm`, `use_llm_available`.

## 8. Configuration and environment

Module: `core/config.py` (Pydantic BaseSettings)
- `retrieval_k` (default 50), override per request via payload `topk`.
- `use_llm_overview` (default True) — config flag; runtime toggle is query param `rewrite_with_ai`.
- `llm_primary = "ollama"`, `llm_timeout_s`, `ollama_url`, `ollama_model`.
- `version` string used in response meta.

Additional env (read by summarizer rewrite helper):
- `OLLAMA_MODEL` (e.g., `qwen2.5:7b`, `llama3.1:8b`)
- `OVERVIEW_STYLE` (`one-line` | `two-three` | `house-md`)

Quick check endpoint: `GET /debug_llm` prints LLM config snapshot.

## 9. Error modes and fallbacks

- Empty or malformed input → normalized to 0 records; safe fallback overview.
- TF‑IDF on empty vocab → early return of empty hits.
- NL with no vocab overlap → uniform vector fallback.
- Ollama unavailable → deterministic overview used; `use_llm_available=false`.
- Oversized `topk` → clamped to `record_count`.
- Logs include structured events: `records_extracted`, `insights_generated`, `summary_generated`, and `*_error` events.

## 10. Performance and complexity

- TF‑IDF build: O(N×V) time; dense but adequate for small/medium corpora.
- Retrieval: matrix‑vector multiply (N×V); top‑k via argpartition.
- Summarization: linear in k for grouping; charts over all normalized records (linear in N).

## 11. Runbook (Windows PowerShell)

Backend only:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000

curl.exe -s http://127.0.0.1:8000/health
curl.exe -s http://127.0.0.1:8000/debug_llm
```

Optional local LLM:
```powershell
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" serve
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" pull qwen2.5:7b
$env:OLLAMA_MODEL = "qwen2.5:7b"
$env:OVERVIEW_STYLE = "two-three"
```

Requests:
```powershell
# Deterministic
curl.exe -s -X POST "http://127.0.0.1:8000/query-assistant" -H "Content-Type: application/json" --data-binary "@backend/examples/input_sample.json"

# With LLM rewrite
curl.exe -s -X POST "http://127.0.0.1:8000/query-assistant?rewrite_with_ai=true" -H "Content-Type: application/json" --data-binary "@backend/examples/input_sample.json"
```

Frontend dev server:
```powershell
cd frontend
npm install
npm run dev
# http://localhost:3000 (proxies /api → 8000)
```

## 12. Testing and observability

Run tests:
```powershell
cd backend
pytest -v
```

Logs:
- Raw JSON lines via `core/logging.log_json`.
- Key events: `records_extracted`, `insights_generated`, `summary_generated`, `insights_generation_error`, `summary_generation_error`.

## 13. Extension points

- Add risk rules: `agent/graph.py::_derive_risks_from_records` and mirrored logic in `services/ai_summarizer.py`.
- Add charts: `agent/graph.py::_viz_from_insights` and `services/ai_summarizer.py` viz builder.
- New inputs: extend `services/input_normalizer.py` + `services/ingest.py` field maps.
- Frontend compatibility: add an adapter endpoint that projects `CensAIResponse` to `{count, summaries, insights}` if needed.

## 14. Known limitations

- Dense TF‑IDF can become memory‑heavy for very large corpora; consider sparse matrices and/or chunked map‑reduce if N grows large.
- Protocol inference is heuristic when explicit protocol is absent.
- Ollama rewrite preserves facts but remains style‑focused; it does not change findings.

---

This document reflects the code on the `main` branch and references exact modules and functions to keep it implementation‑faithful and actionable.
