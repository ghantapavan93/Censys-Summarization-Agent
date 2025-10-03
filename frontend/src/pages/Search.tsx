import { useEffect, useState } from "react";
import { api } from "../api";
import { Host } from "../lib/types";
import { HostCard } from "../components/HostCard";
import DevTools from "../components/DevTools";
import { useToast } from "../components/Toast";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Host[]>([]);
  const [excludeHoneypots, setExcludeHoneypots] = useState(true);
  const [maxServices, setMaxServices] = useState(45);
  const [kevOnly, setKevOnly] = useState(false);
  const { push } = useToast();

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "/" && (e.target as HTMLElement).tagName !== "INPUT") {
        e.preventDefault();
        (document.getElementById("searchBox") as HTMLInputElement | null)?.focus();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  function addClause(c: string) {
    setQuery((q) => (q ? `${q} and ${c}` : c));
  }

  async function run() {
    try {
      const data = await api.search(query, excludeHoneypots, maxServices);
      setResults((data as any).results as Host[]);
    } catch (e: any) {
      push("error", e.message || "Search failed");
    }
  }

  async function exportCSV() {
    try {
      const visible = kevOnly ? results.filter(h => h.kev_present) : results;
      const csv = await api.exportCSV(visible);
      const blob = new Blob([csv], { type: "text/csv" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "results.csv";
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (e: any) {
      push("error", e.message || "Export failed");
    }
  }

  async function copyJSON() {
    try {
      const visible = kevOnly ? results.filter(h => h.kev_present) : results;
      const text = JSON.stringify(visible, null, 2);
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
      } else {
        const ta = document.createElement('textarea');
        ta.value = text; document.body.appendChild(ta); ta.select();
        document.execCommand('copy'); document.body.removeChild(ta);
      }
      push("success", `Copied ${visible.length} host(s) to clipboard`);
    } catch (e: any) {
      push("error", e.message || "Copy failed");
    }
  }

  const noVulnData =
    results.length > 0 &&
    results.every((h) => (h.services || []).every((s) => !s.vulns || !s.vulns.length));

  return (
    <div className="grid grid-cols-12 gap-4">
      {/* DevTools (gated) */}
      {import.meta.env.VITE_SHOW_DEVTOOLS === '1' && (
        <div className="col-span-12">
          <DevTools hosts={results as any[]} />
        </div>
      )}
  <aside className="col-span-12 lg:col-span-3 lg:sticky lg:top-16 space-y-3">
        <div className="rounded-xl border p-3 bg-white">
          <div className="font-semibold">Filters</div>
          <label className="inline-flex items-center gap-2 mt-2 text-xs">
            <input type="checkbox" checked={kevOnly} onChange={(e) => setKevOnly(e.target.checked)} />
            Show KEV-only
          </label>
          <label className="flex items-center gap-2 mt-2 text-sm">
            <input
              type="checkbox"
              checked={excludeHoneypots}
              onChange={(e) => setExcludeHoneypots(e.target.checked)}
            />
            Exclude honeypots & noisy hosts
          </label>
          <label className="flex items-center gap-2 mt-2 text-sm">
            Max services
            <input
              className="w-20"
              type="number"
              min={1}
              value={maxServices}
              onChange={(e) => setMaxServices(+e.target.value)}
            />
          </label>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <button className="btn" onClick={() => addClause("host.services.vulns.kev:*")}>KEV only</button>
            <button
              className="btn"
              onClick={() =>
                addClause(
                  "(host.services.vulns.metrics.cvss_v31.score >= 7 or host.services.vulns.metrics.cvss_v40.score >= 7)"
                )
              }
            >
              CVSS ≥ 7
            </button>
            <button className="btn" onClick={() => addClause("host.services.port = 11434")}>
              Ollama 11434
            </button>
            <button
              className="btn"
              onClick={() => addClause('(host.services.protocol = "HTTP" and not host.services.port = 11434)')}
            >
              Non-11434 HTTP
            </button>
          </div>
        </div>
        <div className="rounded-xl border p-3 bg-white">
          <div className="font-semibold">Actions</div>
          <button className="btn mt-2 w-full" onClick={run}>
            Search
          </button>
          <button className="btn mt-2 w-full" onClick={exportCSV}>
            Export CSV
          </button>
          <button className="btn mt-2 w-full" onClick={copyJSON}>
            Copy JSON (visible)
          </button>
        </div>
      </aside>

  <main className="col-span-12 lg:col-span-9 space-y-3">
        <div className="rounded-xl border p-3 bg-white sticky top-16 z-10">
          <input
            id="searchBox"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter Censys query…"
            className="w-full outline-none"
          />
        </div>

        {/* Guardrail pill */}
        <div className="flex items-center gap-2">
          <div className="inline-flex items-center gap-1 text-xs text-neutral-600">
            <span className="inline-flex items-center rounded-full border border-emerald-300 bg-emerald-50 px-2 py-0.5 text-[11px] text-emerald-700">
              Honeypot guard: {excludeHoneypots ? 'ON' : 'OFF'}
            </span>
            <span
              className="cursor-help"
              title="Filters probable honeypots/noise (e.g., Amazon-02 hosts with very high service counts). Toggle OFF to see raw."
            >ⓘ</span>
          </div>
          {kevOnly && (
            <span className="inline-flex items-center rounded-full border border-red-300 bg-red-50 px-2 py-0.5 text-[11px] text-red-700">
              KEV-only view
            </span>
          )}
        </div>

        {noVulnData && (
          <div className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm">
            Limited vulnerability details in this view. Upgrade tier to see enriched CVE / CVSS / KEV insights.
          </div>
        )}

        {kevOnly && (kevOnly ? results.filter(h => h.kev_present).length === 0 : false) && (
          <div className="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm">
            No hosts with KEV in this view. Try turning off filters.
          </div>
        )}

        <div className="grid md:grid-cols-2 gap-3">
          {(kevOnly ? results.filter(h => h.kev_present) : results).map((h, i) => (
            <HostCard
              key={i}
              h={h}
              onClickPort={(p) => addClause(`host.services.port = ${p}`)}
            />
          ))}
        </div>
      </main>
    </div>
  );
}
