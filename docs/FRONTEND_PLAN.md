# Frontend Architecture and Implementation Plan

Last updated: 2025-09-30

This guide maps the current repository to a modern, robust frontend. It documents the backend APIs and data contracts we must honor, then proposes an end-to-end frontend structure, screens, components, and UX patterns to build a polished product.

## 1) Full repository structure (as of main)

Top-level folders and key files:

- `backend/`
  - `app.py` — FastAPI app exposing HTTP endpoints (/summarize, /query-assistant, /explain, /config, /metrics, /health).
  - `app_legacy.py` — Legacy endpoint `/summarize/legacy` returning an older response shape (count/insights/summaries).
  - `models.py` — Canonical Pydantic models used by the pipeline and API responses (Record, FieldMap, CensAIResponse, etc.).
  - `schemas.py` — Censys Host/Service/Software ASN/Location models (for input typing and tests).
  - `agent/`
    - `graph.py` — Orchestrates the pipeline (extract → insights → retrieve → summarize → derive risks → viz → build response).
    - `state.py` — Pipeline state object.
  - `services/`
    - `input_normalizer.py` — Accepts multiple input shapes; flattens `hosts` to per-service/software records.
    - `ingest.py` — Canonicalizes raw fields into `Record` via `FieldMap` and CVE extraction.
    - `analytics.py` — Deterministic dataset insights (top ports/protocols/software/ASNs/countries).
    - `retrieval.py` — TF‑IDF corpus builder and similarity retrieval.
    - `ai_summarizer.py` — Deterministic overview/key risks/recommendations/highlights, viz payload; optional Ollama rewrite.
    - `llm_router.py` — Minimal Ollama HTTP client (not on main path; summarizer calls Python client directly when requested).
  - `core/`
    - `config.py` — Settings (retrieval_k, LLM config, version, etc.).
    - `logging.py`, `metrics.py`, `observability.py`, `security.py`, `redaction.py` — Infra: logging, Prometheus, request-id, headers/limits, message redaction.
  - Other helpers and examples.

- `frontend/`
  - Vite + React + TypeScript app scaffold.
  - `vite.config.ts` — Dev proxy routes `/api` → `http://localhost:8000`.
  - `src/App.tsx`, `src/components/*`, `src/lib/api.ts` — Initial UI (built around the older legacy response shape).

- `tests/` and `backend/tests/` — Pytests covering analytics, schema, smoke tests, etc.
- `compose*.y*ml`, `Dockerfile`, `Makefile`, `run.ps1` — Containerization and DX.
- `docs/` — Architecture docs, performance notes. This file lives here too.

See `docs/ARCHITECTURE.md` for deeper backend context and contracts.

## 2) Backend API surface and data contracts

Endpoints (FastAPI):

- `GET /health` → `{ "status": "ok", "version": "0.2.0" }`
- `GET /healthz` → `{ "ok": true }`
- `GET /config` → `ConfigResponse` with model backend/name, retrieval_k, language, enable_validation.
- `GET /debug_llm` → snapshot of LLM-related settings (ollama_url, model, etc.).
- `POST /summarize?rewrite_with_ai=false|true` → `CensAIResponse` (see below). Input can be one of:
  - `{ hosts: Host[] }` (recommended for raw Censys data)
  - `{ records: Record[] }` (already canonicalized)
  - `{ raw_records: any[], field_map?: FieldMap }` (custom mapping)
  - Or bare `[]` (array of flat dicts) — will be treated as `raw_records`.
  - Optional: `{ topk: number }` to override retrieval_k per request.
- `POST /query-assistant?rewrite_with_ai=false|true` → same as `/summarize` but geared to NL query assistance; accepts same body with optional `nl` string.
- `GET /explain?finding_id=KF_ID` → `ExplainResponse` with evidence and scoring for a key finding id.
- `GET /metrics` → Prometheus exposition.

Legacy compatibility:
- `POST /summarize/legacy` → `{ count: number; insights: Record<string, Record<string, number>>; summaries: string[] }` (old shape, still available).

Key models (converted to TypeScript for frontend typing):

```ts
// Canonical Record (flattened per host-service-software)
export interface Record {
  id: string;
  ip: string;
  port: number;
  product?: string;
  version?: string;
  hardware?: string;
  country?: string; // ISO‑2 preferred
  cve?: Array<{ id: string; score?: number }>;
  other?: Record<string, unknown>; // protocol, tls flags, cert fields, malware info, asn, errors
}

export interface KeyFinding { id: string; title: string; evidence_ids: string[] }

export interface RiskItem {
  id: string;
  affected_assets: number;
  context: string;
  severity: 'low' | 'medium' | 'high' | 'critical' | string;
  likelihood: string;
  impact: string;
}

export interface RiskMatrix { high: number; medium: number; low: number }

export interface VizSeries { type: 'bar' | string; title: string; data: Array<[string, number]> }

export interface VizPayload {
  charts: VizSeries[];
  histograms?: Record<string, Record<string, number>>;
  top_ports?: Record<string, number>;
}

export interface CensAIResponse {
  summary: string; // full stitched text (overview + bullets when available)
  overview_deterministic?: string;
  overview_llm?: string;          // present if rewrite_with_ai and Ollama returns text
  use_llm_available?: boolean;    // whether LLM produced a distinct overview
  key_findings: KeyFinding[];
  risks: RiskItem[];
  risk_matrix: RiskMatrix;
  query_trace: { nl?: string; query?: string; topk?: number; structured_filters?: Record<string,string> };
  viz_payload: VizPayload;
  next_actions: string[];
  meta: {
    event_id: string; record_count: number; generated_at: string; version: string;
    total_records: number; invalid_records: number;
    timings_ms: { validation: number; insights: number; retrieval: number; summarization: number; total: number };
  };
}
```

Important behavior notes for the frontend:

- If `rewrite_with_ai=true` and Ollama is available, `overview_llm` may differ from `overview_deterministic` and `use_llm_available=true` — the UI should let users toggle the wording they see.
- `viz_payload.charts` contains data series ready for bar charts; `histograms` and `top_ports` are convenience maps.
- `risks` includes items derived from deterministic rules and dataset exposures; `risk_matrix` aggregates counts.
- `query_trace` exposes the derived query and top‑k used by retrieval; this is useful for transparency and tuning UIs.

## 3) End‑to‑end flow in plain English

1. User provides input: either a Censys `hosts` JSON or a flat `records` array.
2. Backend normalizes to `raw_records` → canonicalizes into `Record[]` using `FieldMap` and CVE regex.
3. Insights are computed (top ports, protocols, software, ASNs, countries) and a flattened `insights.records` cache is attached for viz.
4. Retrieval builds a TF‑IDF corpus over all records, derives a query (from NL or seeds), and selects top‑k context.
5. Summarization groups evidence to produce an overview, key risks, recommendations, highlights, viz payload, and optionally rewrites the overview via Ollama.
6. Response includes findings, risks, risk matrix, query trace, next actions, charts, and timings.

## 4) Proposed frontend architecture (React + Vite + TS)

Primary goals:

- Clean separation between pages, feature components, and shared UI primitives.
- Strong typing against backend contracts.
- First‑class UX for loading, empty, error, and large datasets.
- Observability (request id, timings), accessibility, and keyboard navigation.

Recommended libraries:

- Routing/state/data:
  - `react-router-dom` for routes.
  - `@tanstack/react-query` for API fetching/caching/retries.
  - `zustand` for lightweight global UI state (settings/toggles/selection).
- UI/UX:
  - `tailwindcss` + a small component kit (e.g., shadcn/ui) or `@mui/material` — pick one based on team preference.
  - `lucide-react` (already included) for icons.
  - `recharts` or `visx` for charts.
  - `sonner` (toasts) and `react-aria`/`radix-ui` primitives for a11y.
- Utilities: `zod` for client‑side validation; `date-fns` for timestamps; `clsx`.

Proposed folder structure under `frontend/src`:

```
src/
  app/
    AppShell.tsx             # Layout frame (header/nav/footer), theme switcher
    routes.tsx               # Route table
    providers.tsx            # React Query, Theme, i18n, Router providers
  pages/
    UploadPage.tsx           # Start here; dropzone + sample links + config hints
    OverviewPage.tsx         # Executive overview, toggles (deterministic vs LLM), dataset stats
    RisksPage.tsx            # Risk table, filters, RiskMatrix heatmap
    FindingsPage.tsx         # Key findings list; click → explain panel
    RecordsPage.tsx          # Virtualized data table of canonical Records
    SettingsPage.tsx         # Backend config, LLM status, preferences (topk, style)
  components/
    common/
      Button.tsx Card.tsx Modal.tsx Tabs.tsx Skeleton.tsx Tooltip.tsx
      DataTable/ (column defs, pagination, virtualization)
      Chart.tsx  # wrapper around recharts/visx
      Stat.tsx   # labeled KPI number with delta
    summary/
      OverviewToggle.tsx     # switch between overview_deterministic and overview_llm
      KeyFindingsList.tsx    # list with severity chips; onClick → ExplainDrawer
      ExplainDrawer.tsx      # calls GET /explain
      RiskMatrix.tsx         # 3x3 heatmap from risk_matrix
      ChartsPanel.tsx        # renders viz_payload.charts
    upload/
      Dropzone.tsx           # drag‑and‑drop file, parse, preview size
      SampleDataHint.tsx     # links to example JSON
  api/
    client.ts               # fetch wrapper (base url, headers, error mapping)
    endpoints.ts            # typed functions: getConfig, summarize, queryAssistant, explain
    types.ts                # TS types mirrored from backend models
  hooks/
    useConfig.ts            # wraps GET /config
    useSummarize.ts         # wraps POST /summarize
    useQueryAssistant.ts    # wraps POST /query-assistant
    useExplain.ts           # wraps GET /explain
  store/
    settings.ts             # UI prefs (theme, topk, rewrite_with_ai, overview style)
    selection.ts            # selected finding/risk/record ids
  theme/
    ThemeProvider.tsx tokens.ts globals.css  # colors, spacing, dark mode
  i18n/
    index.ts en.json ...    # string tables if multilingual is desired
  utils/
    format.ts redact.ts mapToSeries.ts debounce.ts
  assets/
    logo.svg empty-states/*
  tests/
    components/*.test.tsx pages/*.test.tsx api/*.test.ts
```

How this maps to the backend:

- `api/types.ts` mirrors `CensAIResponse`, `Record`, etc. Keep it authoritative and generated from backend OpenAPI when feasible.
- `api/endpoints.ts` builds exactly the payload shapes the backend expects:
  - Upload page should wrap arrays as `{ hosts }` to leverage the host flattener.
  - Support optional `field_map` and `topk` when advanced users provide them.
  - Support `rewrite_with_ai` query param (on by default from a Settings toggle).
- `pages/OverviewPage.tsx` consumes `overview_deterministic`, `overview_llm`, `use_llm_available` (toggle via `components/summary/OverviewToggle`).
- `pages/RisksPage.tsx` renders `risks` and `risk_matrix`; `components/summary/RiskMatrix` turns counts into a 3×3 heatmap.
- `pages/FindingsPage.tsx` lists `key_findings` and uses `useExplain()` to pull details on demand.
- `pages/RecordsPage.tsx` uses a virtualized grid (10k+ rows) built from canonical `Record[]` if we choose to surface them; minimal stable columns: ip, port, product, version, country.
- Charts panel renders `viz_payload.charts` and falls back to `histograms` maps for simple spark bars.

## 5) UI/UX blueprint (flows, states, a11y)

Core flows:

1) Upload & analyze
   - Drag & drop or file picker → detect size and basic schema → preview count → "Analyze" button.
   - On submit: POST `/summarize?rewrite_with_ai=<toggle>` with `{ hosts }` or `{ raw_records, field_map, topk }`.
   - Show skeletons for overview, charts, and risks while fetching.

2) Overview & toggles
   - Display a compact executive overview with a one‑click toggle between deterministic and LLM variants when `use_llm_available`.
   - Show KPI stats: total records, unique IPs (if available), timings (`meta.timings_ms`) with an info tooltip explaining compute stages.

3) Risks & findings
   - Risks table: severity badge, context, affected assets; column filters (severity, product, country, port keyword).
   - RiskMatrix: three counters rendered as an accessible heatmap with color‑blind safe palette.
   - Key Findings: succinct titles; click reveals Explain drawer (GET `/explain?finding_id=...`).

4) Assistant (optional first iteration)
   - NL input to refine query, piping to `/query-assistant` and showing a diff vs previous overview.

5) Records viewer (optional)
   - Virtualized table of canonical records (ip, port, product, version, country), downloadable as CSV.

Empty/error/loading states:

- Empty: Encouraging copy, sample data link, and a prominent upload CTA.
- Loading: Page-level skeletons (overview box, risk table placeholders, chart shimmer).
- Error: Inline banner (status/message), retry buttons, copy for common failures (413 payload too large, 500 LLM error fallback).

Accessibility:

- Every interactive element keyboard reachable with visible focus.
- `aria-live` regions for async status updates (e.g., "Analyzing…").
- Color contrast AA+; avoid information only by color (badges include text).

Performance:

- Virtualize long tables; memoize chart transforms; avoid re-parsing large JSON after upload.
- Code-split by route; lazy‑load charts for first meaningful paint.
- Utilize React Query caching and background refetches.

Security and privacy:

- Respect backend 5 MB JSON cap. Warn users if file is too large before POST.
- Avoid echoing raw content; render summaries and charts only.
- Surface request id (X-Request-ID) for support when available.

## 6) API wiring details (practical)

Base URL & proxy:

- Dev: Vite proxies `/api` → `http://localhost:8000` (see `vite.config.ts`).
- Wrap `fetch` in `api/client.ts` to attach headers and map errors consistently.

Payload building examples (conceptual TS):

```ts
// Summarize from Censys hosts
await summarize({
  hosts,                  // Host[] from file
  event_id: 'evt-ui',     // optional
  nl: uiQuery ?? '',      // optional
  field_map,              // optional advanced mapping
  topk: settings.topk,    // optional override
}, { rewrite_with_ai: settings.rewriteWithAI });

// Query Assistant
await queryAssistant({ hosts, nl: userQuestion }, { rewrite_with_ai: true });

// Explain a finding on demand
await explain(findingId);
```

Error handling:

- Map 413 → "File too large" with tips to trim sample.
- Map 422 → validation details (limit to 3–5 items); provide a link to docs.
- Map 500 on LLM rewrite → gracefully fallback to deterministic overview and show a non‑blocking toast.

## 7) Migrating the current frontend

Today, `frontend/src/lib/api.ts` posts raw arrays to `/api/summarize` and expects the legacy shape `{ count, summaries, insights }`. The backend’s modern `/summarize` returns `CensAIResponse` instead.

Two migration options:

1) Quick compatibility: call `/api/summarize/legacy` from the current UI to keep it working while we upgrade visuals.
2) Recommended: update the UI to consume `CensAIResponse` and unlock overview toggles, risks, and charts. This requires:
   - Replace `SummaryResponse` types with the `CensAIResponse` types above.
   - Update components: instead of per‑host cards, show Overview, Risks, and Charts sections.
   - Add a small Records viewer only if needed.

## 8) Definition of done (frontend MVP)

- Upload JSON, analyze with `/summarize` (with toggle for LLM rewrite) and render:
  - Executive overview with toggle between deterministic/LLM when available.
  - Risk table + RiskMatrix.
  - Charts: Top Ports, Protocols, Software, Countries.
  - Key Findings list with Explain drawer.
  - Next actions and meta timings.
- Robust empty/loading/error states and dark mode.
- API interactions typed and cached with React Query; components covered by basic tests.

## 9) Follow‑ups and enhancements

- Export: PDF/Markdown report using the summary, risks, and charts.
- Bookmarks: shareable links retaining settings and last result id.
- Advanced filters for risks and records (product/country/port ranges).
- Internationalization: language toggle via `GET /config.language`.
- Telemetry: capture UI timings and surface backend timings for end‑to‑end latency.

---

With this plan, the frontend will reflect the backend’s strengths: transparent analytics, clear risk articulation, and an optional LLM polish that’s always safe to fall back from. The structure keeps growth simple—new rules become new badges and cards, new charts slot into the viz panel, and the assistant can evolve without disturbing the core analysis experience.
