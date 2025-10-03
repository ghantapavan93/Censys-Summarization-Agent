# Censys Summarization Agent

An AI-powered, full‑stack application that ingests Censys host data and turns it into analyst‑grade summaries: risks, insights, and next actions. It ships with a modern React UI, a FastAPI backend, optional LLM rewrite, metrics, and a few handy export tools.

Recruiter view: skim Features, Quick Start, and the End‑to‑End Flow diagram. Engineer view: the Setup, API, and Testing sections are copy‑paste runnable on Windows (PowerShell) and via Docker.

## 🚀 Highlights

- Dual summarizers: deterministic rule engine + optional LLM “rewrite with AI”
- Analytics: top ports/protocols/software/ASNs/countries, severity matrix, clusters
- Frontend: React + Vite with proxy to backend, CSV/PDF export, filters, trends, and saved views
- Backend: FastAPI with clean routes under /api, Prometheus metrics at /metrics
- LLM routing: runs locally via Ollama by default; OpenAI is supported by design
- DX: one‑click Windows start, Makefile, Docker Compose, and VS Code tasks

---

## 🔗 Quick links

- Install dependencies: see [Installation](#installation-dependencies)
- Run both services: [How to run](#how-to-run) → Recommended: `npm run dev`
- One‑click backend only: [Quick Start → Option A](#option-a--one-click-backend-windows-powershell)
- Docker (full stack + Ollama): [Quick Start → Option B](#option-b--docker-compose-full-stack--ollama)
- API docs: [Swagger UI](#access-points)
- Metrics: [Prometheus endpoint](#metrics--observability)
- Example request: [Summarize dataset](#example-summarize-a-dataset-file)
- Tests: [How to run tests](#testing)
- If something breaks: [Troubleshooting](#troubleshooting)

---

## 🧭 End‑to‑End Flow (How it works)

1) You paste or upload a dataset in the UI (or use the provided sample).  
2) Frontend normalizes to a flexible `records[]` shape and calls `POST /api/summarize`.  
3) Backend produces a deterministic, data‑grounded overview, risks, insights, and charts.  
4) Optionally, the backend asks the local LLM (Ollama) to rewrite the executive overview (guarded + measured).  
5) You explore the result, filter by severity, export CSV/PDF, or trigger a rewrite in a different style.

---

## 🧱 System architecture (single diagram)

<!-- Replace the placeholder below with your image. Example:
![System architecture](docs/architecture.png)
-->

<p align="center"><strong> c:\Users\Pavan Kalyan\Downloads\Untitled diagram _ Mermaid Chart-2025-10-03-113206.png  </strong></p>

In short
- Deterministic-first: Frontend → FastAPI → Deterministic summarizer → Enrich → Response (JSON + CSV/PDF)
- AI optional: Deterministic overview → LLM (Ollama/OpenAI) → Guardrails → Merge → Response
- Observability: Prometheus `/metrics` from validation/summarizer/LLM stages

Note: Keep the diagram 16:9 and ~1200px wide for crisp GitHub rendering. Put the file under `docs/` and update the path above.

---

## 📋 Requirements

Backend
- Python 3.10+ (tested on 3.10–3.13)
- FastAPI, Pydantic, Prometheus client (see `backend/requirements.txt`)
- Optional: Ollama for local LLM, or `OPENAI_API_KEY` for OpenAI

Frontend
- Node.js 18+ (Vite 7, React 18, TypeScript)

---

## 📦 Installation (dependencies)

Install prerequisites once per machine, then project dependencies.

PowerShell (Windows):

```powershell
# Backend deps (creates virtual env and installs requirements)
python -m venv .venv
. .\.venv\Scripts\Activate
pip install -r backend\requirements.txt

# Frontend deps
cd frontend; npm install; cd ..

# Root dev helper (installs concurrently used by `npm run dev`)
npm install
```

Notes
- Python 3.10+ is recommended; verify with `python --version`.
- Node.js 18+ is required; verify with `node --version`.

---

## ▶️ How to run

Choose one of the following depending on your workflow.

First-time quickstart (Windows, TL;DR)
- In a new PowerShell window at the repo root:
  ```powershell
  # 1) Root helpers for dev scripts
  npm install
  # 2) Frontend dependencies
  npm --prefix frontend install
  # 3) Prime backend env (creates .venv and installs Python deps)
  .\run.ps1
  # When the backend shows "Uvicorn running" you can Ctrl+C to stop it
  # 4) Start both services together
  npm run dev
  ```
  Tip: first install can take several minutes (PyTorch/Transformers wheels).

- Recommended — one command (backend + frontend together):
  ```powershell
  # First time only: install root dev helper
  npm install
  # First time only: this script creates .venv and installs backend deps
  ```

- Frontend only (dev server with API proxy):
  ```powershell
  # First time only: install UI deps, then start Vite
  cd frontend; npm install; npm run dev
  ```

- Docker Compose (full stack + Ollama):
  # First time only: images will be built/pulled automatically
  make up   # or: docker compose up --build -d
  ```


---

From the repo root:

.\run.ps1
```

- Creates `.venv` if missing, installs backend deps, sets `PYTHONPATH`, and runs FastAPI at http://127.0.0.1:8000

Open Swagger UI: http://127.0.0.1:8000/docs
Frontend (in another terminal):

```powershell
cd frontend; npm install; npm run dev
```

Vite opens http://127.0.0.1:5173 and proxies /api to http://127.0.0.1:8000.

### Option B — Docker Compose (full stack + Ollama)

```powershell
Set-Content -Path .env -Value "OPENAI_API_KEY=your_openai_api_key_here"

make up   # or: docker compose up --build -d
```

Services
- Frontend: http://127.0.0.1:3000
- Backend:  http://127.0.0.1:8000
- Swagger:  http://127.0.0.1:8000/docs
- Ollama:   http://127.0.0.1:11434

Pull a local model in the Ollama container (first time only):
```powershell
docker exec -it ollama ollama pull qwen2.5:7b
```

Then in the UI, click “Rewrite with AI” or call the API with `rewrite_with_ai=true`.

---

### AI rewrite (optional): Local Ollama setup (Windows)

You only need this if you want the “Rewrite with AI” feature without Docker. The deterministic summaries work without any LLM.

```powershell
# Install Ollama (native Windows)
winget install -e --id Ollama.Ollama

# Close & reopen your terminal, then pull a model (first time)
ollama pull qwen2.5:7b

# Optional: point the backend at a custom Ollama host
$env:OLLAMA_HOST = "http://127.0.0.1:11434"
```

Notes
- Default Ollama endpoint is http://127.0.0.1:11434 when installed locally.
- In Docker Compose, the backend uses http://ollama:11434 (container network).
- Alternative: skip Ollama and use OpenAI by setting `OPENAI_API_KEY`.

---

## ⚙️ Environment Variables

Backend (read from process env; many are optional)
- `ALLOW_ORIGINS`: Comma‑separated CORS allowlist (example: `http://localhost:5173,http://localhost:3000`)
- `DEFAULT_VALIDATION_POLICY`: `off | lenient | strict` (default: `lenient`)
- `OLLAMA_HOST`: Base URL of Ollama (default in Docker: `http://ollama:11434`)
- `OLLAMA_MODEL`: Default model name (default: `qwen2.5:7b`)
- `OPENAI_API_KEY`: Enables OpenAI client for prompts that use it (optional)
- `KEV_CACHE_PATH`: Path to KEV cache file (default: `data/kev_ids.json`)

Frontend
- `VITE_API_BASE`: Override API base (default `/api` in dev via proxy)
- `VITE_SHOW_DEVTOOLS`: `1` to show the DevTools panel on the Search page. The Compact Toolbar (Alt+D on the Summary page) does not require an env var.

- Swagger UI: http://127.0.0.1:8000/docs
- Health:     http://127.0.0.1:8000/api/health
- Metrics:    http://127.0.0.1:8000/metrics (Prometheus)

Quick smoke (PowerShell):

```powershell
curl -s http://127.0.0.1:8000/api/health | ConvertFrom-Json | Format-List
  ## 🛠️ Quick Start (Windows‑friendly)
curl -s -Method POST http://127.0.0.1:8000/api/summarize -Headers @{ 'content-type'='application/json' } -Body '{"records":[]}' | Out-Null

# Rewrite with AI (Ollama model must be pulled)
curl -s -Method POST http://127.0.0.1:8000/api/summarize -Headers @{ 'content-type'='application/json' } -Body '{"records":[],"rewrite_with_ai":true,"llm_preference":"qwen2.5:7b"}' | Out-Null

# Check counters
curl -s http://127.0.0.1:8000/metrics | Select-String censys_summarize_total
```

---

## 📁 Project Structure

```
Censys-Summarization-Agent/
├─ backend/                     # FastAPI app and services
│  ├─ app.py                    # App wiring, /api routers, metrics, CORS
│  ├─ routes/                   # API routes (summarize, enrich, export, ai, trends, etc.)
│  │  ├─ summarize.py           # POST /api/summarize (deterministic + LLM rewrite)
│  │  ├─ enrich.py              # POST /api/enrich/vulns (KEV/CVSS scoring, port signals)
│  │  ├─ export.py              # POST /api/export/{csv|pdf}
│  │  ├─ compat.py              # Legacy/compat endpoints (/health, /summarize, /query-assistant)
│  │  └─ ...                    # admin, ai/check, tickets, views, trends, etc.
│  ├─ services/                 # Summarization engine, metrics, kev/epss loaders, mutes, etc.
│  │  ├─ summarizer_llm.py      # Deterministic report + optional Ollama rewrite
│  │  └─ metrics.py             # Prometheus counters/histograms
│  ├─ rules/                    # Rule sets used by deterministic analysis
│  ├─ prompt_templates.py       # LLM prompts for host rewrites
│  └─ requirements.txt
│
├─ frontend/                    # React + Vite UI (Tailwind, Recharts)
│  ├─ src/lib/api.ts            # Client for /api/* endpoints
│  ├─ src/components/*          # Summary, charts, export, settings, etc.
│  └─ vite.config.ts            # Proxies /api → http://127.0.0.1:8000
│
├─ examples/                    # Sample datasets and outputs
│  └─ hosts_dataset.json        # Example hosts payload (3 hosts)
│
├─ tools/                       # Utilities (export/validate/shape via jq/PS)
├─ tests/                       # End‑to‑end + backend tests
├─ docker-compose.yml           # Full stack incl. Ollama
├─ Makefile                     # dev/up/down/logs/test helpers
└─ run.ps1                      # Windows one‑click backend starter
```

---

## 🔧 API (core routes)

All modern endpoints are under the `/api` prefix.

### POST /api/summarize
Body (SummarizeRequest)
- `records`: List<object> — flexible host/service shape (the UI normalizes Censys data for you)
- `rewrite_with_ai`: boolean (default false)
- `llm_preference`: string (e.g., `"qwen2.5:7b"`)
- `style`: optional (`executive`, `bulleted`, `ticket`)
- `language`: optional (e.g., `"en"`)

Returns
- Deterministic overview, key risks (with CVE/EPSS/KEV where possible), charts, totals
- Optionally `overview_llm` plus `ai_overview` metadata when rewrite is enabled

Validation
- Lightweight server checks; client can set header `X-Validation-Policy: off|lenient|strict` (default: lenient)
- On strict violations, API returns 422 with error details and non‑blocking warnings

### POST /api/enrich/vulns
Scores and annotates hosts by KEV/CVSS and sensitive/mgmt ports to produce a sortable risk score.

### POST /api/export/csv
Union of keys → CSV; returns a file download with a timestamped filename.

### POST /api/export/pdf
Generates a concise “Executive Brief” (uses ReportLab if available, falls back to text).

### POST /api/ai/check
Runs an automated check to compare deterministic vs AI rewrite (similarity, length bounds).

### GET /api/health
Simple health with version and timestamp.

### GET /metrics
Prometheus metrics (see Metrics section).

Compatibility routes (no prefix)
- `/health`, `/healthz`, `/config`, `/summarize`, `/query-assistant` — for legacy flows used in tests.

---

## 📊 Metrics & Observability

Exposed at `GET /metrics` (Prometheus).

- `censys_requests_total{path,method,status}`
- `censys_request_latency_seconds_bucket{path}`
- `censys_summarize_total{rewrite_with_ai,llm}`
- `censys_summarize_latency_seconds_bucket{rewrite_with_ai,llm}`
- `censys_enrich_total`, `censys_export_total`, `censys_inflight_requests`

Example Prometheus scrape config

```yaml
scrape_configs:
  - job_name: censys-agent
    scrape_interval: 15s
    static_configs:
      - targets: ['127.0.0.1:8000']
```

---

## 🧪 Testing

Backend (local)
```powershell
cd backend; python -m pytest -q
```

Entire repo tests (when available)
```powershell
python -m pytest -q
```

Docker (from repo root)
```powershell
make test
```

Manual smoke (UI)
- Start backend and frontend
- Click “Use Sample” → verify KPIs, charts, and risk cards render within ~1–2s
- Toggle filters (severity/port/country) and ensure counts update
- Export CSV/PDF; confirm downloads
- Trigger “Rewrite with AI”; verify AI badge + metadata in the drawer

---

## 🧠 AI Techniques (brief)

- Deterministic analyst report
  - Computes overview, totals, severity matrix, clusters
  - Produces actionable “Top Risks” with title, severity, CVEs, EPSS hints, evidence, fixes
  - Heuristics: KEV presence, CVSS≥7 bumps, sensitive/mgmt port weights, honeypot guard

- LLM rewrite (optional):
  - Local first via Ollama (default model: `qwen2.5:7b`), API‑driven rewrite of the executive overview
  - Guardrails: prompt constrained to JSON/keys when using OpenAI‑style prompts; length and similarity checks
  - Telemetry: `ai_overview` captures latency, model, guard_pass, and delta counts

- Data shaping: flexible normalizer accepts realistic Censys shapes (services.vulnerabilities[], software[], banners, TLS certs)

---

## 🧰 Developer Experience & VS Code Tasks

Makefile (see `make help`)
- `make dev` (dev compose), `make up` (prod), `make down`, `make logs`, `make test`, `make clean`

VS Code tasks (Terminal → Run Task)
- Export: Censys → NDJSON + shape (runs `tools/censys_export.ps1`)
- Validate: hosts_dataset.json (JSON schema validation)
- Publish: latest dataset to `frontend/public/datasets/latest.json`
- Docker build/run for the frontend

Tip: the frontend dev server shows a tiny banner with API base and build timestamp for easy debugging.

---

## 🧾 Assumptions

- The app consumes pre‑fetched Censys‑like host JSON (see `examples/hosts_dataset.json`); no live Censys API calls in this demo.
- No database; results are in‑memory per request. Views/alerts are stubbed for UX demonstration.
- LLM rewrite is optional; if Ollama/OpenAI isn’t available, the deterministic summary stands on its own.
- Security model is demo‑grade (no auth); deploy behind your gateway if exposing publicly.

---

## 🔮 Future Enhancements (shortlist)

- Integrate live Censys queries and pagination with caching
- Persistent store (SQLite/Postgres) for saved views, alerts, and historical deltas
- Authentication/SSO and role‑based export controls
- Streaming responses (Server‑Sent Events) for long‑running LLM rewrites
- More guardrails (PII scrub, jailbreak/TOX checks) with policy knobs
- Vector search (FAISS/pgvector) for cross‑host similarity and trend annotations
- Deeper KEV/EPSS enrich (per‑CVE drilldowns, time‑to‑exploit overlays)
- Richer UI interactions (map, topology, diff viewers across snapshots)
- e2e tests (Playwright) and contract tests for API schemas

---

## 📎 Data Shapes (reference)

Input (per host — flexible; these are common fields)

```json
{
  "ip": "1.2.3.4",
  "location": { "country": "United States", "city": "New York" },
  "autonomous_system": { "asn": 12345, "name": "Example AS" },
  "services": [
    {
      "port": 22,
      "protocol": "SSH",
      "software": [{ "vendor": "openbsd", "product": "openssh", "version": "9.6" }],
      "vulnerabilities": [{ "cve_id": "CVE-2024-6387", "cvss_score": 8.1 }],
      "banner": "SSH-2.0-OpenSSH_9.6"
    }
  ]
}
```

## 🧰 Debug UI: Compact Toolbar vs DevTools

- Compact Toolbar (Summary page)
  - Always available in development; toggled with Alt+D; no env var required.
  - Lets you quickly toggle “Rewrite with AI”, pick an Ollama model, and re-run.

- DevTools panel (Search page)
  - Only shown when `VITE_SHOW_DEVTOOLS=1`.
  - Useful for inspecting parsed hosts and quick checks while iterating.

Enable DevTools panel during development:

```powershell
$env:VITE_SHOW_DEVTOOLS = "1"
```

Unset or set to `0` to hide in production builds.

---

## 🧪 Example: Summarize a dataset file

Post the included `examples/hosts_dataset.json` to the API. The frontend already normalizes, but for raw API you can send `records` directly (the backend also accepts nested `services`).

```powershell
$body = Get-Content -Raw examples/hosts_dataset.json | ConvertFrom-Json
$records = @()
foreach ($h in $body.hosts) { $records += $h }
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/summarize" -ContentType 'application/json' -Body (@{ records = $records } | ConvertTo-Json -Depth 8)
```

Pass `rewrite_with_ai=true` and `llm_preference='qwen2.5:7b'` to trigger the Ollama rewrite once you’ve pulled the model.

---

## 🚢 Production tips

- Backend workers: run `uvicorn backend.app:app --host 0.0.0.0 --port 8000 --workers 2` behind a reverse proxy
- Frontend build: `cd frontend; npm run build` (serves static assets; set `VITE_API_BASE` to your backend URL)
- CORS: set `ALLOW_ORIGINS` appropriately when serving FE and BE on different hosts/ports
- Health and metrics: expose `/api/health` and `/metrics` to your platform monitors

---

## 🛠️ Troubleshooting

- `npm run dev` exits with code 1
  - Ensure Node.js ≥ 18 and run `npm install` in the repo root (installs `concurrently`)
  - If `.venv` is missing, run `./run.ps1` once to create it and install backend deps
  - If port 8000/5173 is in use, stop the other process or change ports (see vite/uvicorn options)

- PowerShell blocked running run.ps1
  - Your execution policy may block local scripts. In a PowerShell session run as your user:
    ```powershell
    Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
    ```
    Then retry `.\run.ps1`. You can revert later with:
    ```powershell
    Set-ExecutionPolicy -Scope CurrentUser Restricted
    ```
  - If the frontend reports missing modules, install UI deps:
    ```powershell
    npm --prefix frontend install
    ```

- AI rewrite returns 400
  - Pull a model: `docker exec -it ollama ollama pull qwen2.5:7b` (or change `llm_preference`)
  - Verify `OLLAMA_HOST` is reachable, or switch to OpenAI by setting `OPENAI_API_KEY`

- CORS errors in the browser
  - Set `ALLOW_ORIGINS` to include your frontend origin, e.g. `http://localhost:5173`

- Strict validation blocked my request (422)
  - Either fix the reported shape issues (ports 1–65535, service dicts in lists), or send header `X-Validation-Policy: lenient` for iteration

- Frontend can’t reach API in preview/prod
  - Set `VITE_API_BASE` to your API origin before build or via environment at deploy time

```

Output (excerpt)

```json
{
  "overview_deterministic": "…",
  "risks": [ { "title": "OpenSSH exposure", "severity": "HIGH", "related_cves": ["CVE-2024-6387"], "recommended_fix": "Keys+MFA …" } ],
  "viz_payload": { "charts": [ { "type": "bar", "title": "Top Ports", "data": [["22", 10], ["80", 7]] } ] },
  "ai_overview": { "used_ai": true, "model": "qwen2.5:7b", "latency_ms": 980 }
}
```

---

## 📜 License

MIT — see [LICENSE](LICENSE).

## 🙌 Acknowledgments

- Censys for the data format conventions and inspiration
- FastAPI, React, Vite, Tailwind, Recharts, Prometheus client
- Ollama and OpenAI for the LLM ecosystem
