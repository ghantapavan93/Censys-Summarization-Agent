import { useEffect, useMemo, useState } from "react";
import type { Host } from "../lib/types";
import CompactToolbar from "../components/CompactToolbar";
import { summarize } from "../api";

type Summary = {
  counts: { hosts: number; kev_hosts: number; high_risk_hosts: number };
  top_asn: [string, number][];
  top_ports: [number, number][];
  top_countries: [string, number][];
  notes?: any;
};

export default function SummaryPage({ hosts }: { hosts: Host[] }) {
  const [sum, setSum] = useState<Summary | null>(null);
  const [showLegend, setShowLegend] = useState(false);
  const [rewriteWithAI, setRewriteWithAI] = useState(false);
  const [llm, setLlm] = useState('qwen2.5:7b');
  const [result, setResult] = useState<any | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    // Compute simple stats locally from the provided hosts array
    const counts = {
      hosts: hosts.length,
      kev_hosts: hosts.filter(h => h.kev_present).length,
      high_risk_hosts: hosts.filter(h => (h.risk_score ?? 0) >= 70).length,
    };

    const asnMap = new Map<string, number>();
    const countryMap = new Map<string, number>();
    const portMap = new Map<number, number>();

    for (const h of hosts) {
      const asnName = h.autonomous_system?.name;
      if (asnName) asnMap.set(asnName, (asnMap.get(asnName) || 0) + 1);

      const cc = h.location?.country_code || h.location?.country;
      if (cc) countryMap.set(cc, (countryMap.get(cc) || 0) + 1);

      for (const s of h.services || []) {
        if (typeof s.port === "number") {
          portMap.set(s.port, (portMap.get(s.port) || 0) + 1);
        }
      }
    }

    const top_asn = [...asnMap.entries()].sort((a,b)=>b[1]-a[1]).slice(0,10) as [string, number][];
    const top_countries = [...countryMap.entries()].sort((a,b)=>b[1]-a[1]).slice(0,10) as [string, number][];
    const top_ports = [...portMap.entries()].sort((a,b)=>b[1]-a[1]).slice(0,10) as [number, number][];

    setSum({ counts, top_asn, top_ports, top_countries });
  }, [hosts]);

  if (!sum) return null;

  async function onRun() {
    setBusy(true); setErr(null);
    try {
      const out = await summarize({ records: hosts as any[], rewrite_with_ai: rewriteWithAI, llm_preference: llm });
      setResult(out);
    } catch (e: any) {
      setErr(e?.message || String(e));
    } finally { setBusy(false); }
  }

  function nav(clause: string) {
    const u = new URL(window.location.origin + "/search");
    u.searchParams.set("q", clause);
    window.location.assign(u.toString());
  }

  const kpis = useMemo(() => {
    // Top country and ASN from server summary when available
    const topCountry = (sum?.top_countries?.[0]?.[0]) ?? (() => {
      const m = new Map<string, number>();
      hosts.forEach(h => { const c = h.location?.country_code; if (c) m.set(c, (m.get(c)||0)+1); });
      const top = [...m.entries()].sort((a,b)=>b[1]-a[1])[0];
      return top?.[0];
    })();
    const topAsn = (sum?.top_asn?.[0]?.[0]) ?? (() => {
      const m = new Map<string, number>();
      hosts.forEach(h => { const a = h.autonomous_system?.name; if (a) m.set(a, (m.get(a)||0)+1); });
      const top = [...m.entries()].sort((a,b)=>b[1]-a[1])[0];
      return top?.[0];
    })();
    const topPort = (() => {
      const counts = new Map<number,number>();
      hosts.forEach(h => (h.services||[]).forEach(s => s.port && counts.set(s.port, (counts.get(s.port)||0)+1)));
      const t = [...counts.entries()].sort((a,b)=>b[1]-a[1])[0];
      return t?.[0];
    })();
    return [
      { label: "Hosts", value: hosts.length, onClick: () => nav("") },
      { label: "Countries", value: new Set(hosts.map(h => h.location?.country)).size, onClick: () => topCountry && nav(`host.location.country_code="${topCountry}"`) },
      { label: "ASNs", value: new Set(hosts.map(h => h.autonomous_system?.asn)).size, onClick: () => topAsn && nav(`host.autonomous_system.name="${topAsn}"`) },
      { label: "Services", value: hosts.reduce((a,h)=>a+(h.services?.length||0),0), onClick: () => nav("") },
      { label: "KEV Affected", value: `${Math.round(100*hosts.filter(h=>h.kev_present).length/Math.max(1,hosts.length))}%`, onClick: () => nav("host.services.vulns.kev:*") },
      { label: "Top Port", value: topPort ?? "—", onClick: (port?: number) => port && nav(`host.services.port = ${port}`) },
    ];
  }, [hosts, sum]);

  return (
    <div className="grid gap-4">
      <CompactToolbar
        rewriteWithAI={rewriteWithAI}
        setRewriteWithAI={setRewriteWithAI}
        llm={llm}
        setLlm={setLlm}
        onRun={onRun}
      />
      {/* KPI Grid (client-side) */}
      <div className="rounded-xl border p-4 bg-white">
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
          {kpis.map((kpi, i) => (
            <button
              key={i}
              className="rounded-xl border p-3 text-center hover:bg-neutral-50"
              onClick={() => {
                if (kpi.label === 'Top Port' && typeof kpi.value === 'number') {
                  (kpi as any).onClick(kpi.value);
                } else if (typeof (kpi as any).onClick === 'function') {
                  (kpi as any).onClick();
                }
              }}
            >
              <div className="text-xs text-neutral-500">{kpi.label}</div>
              <div className="text-lg font-semibold">{kpi.value as any}</div>
            </button>
          ))}
        </div>
        <div className="mt-2 flex items-center justify-between">
          <p className="text-[11px] text-neutral-500">
            Risk scoring: +40 (KEV), +25 (CVSS ≥ 7), +5 (HTTP on non-std port); WAF slightly reduces score.
          </p>
          <button className="text-[11px] underline" onClick={() => setShowLegend(true)}>About scoring</button>
        </div>
      </div>
      <Modal open={showLegend} onClose={() => setShowLegend(false)}>
        <ul className="list-disc ml-5">
          <li>+40: Known Exploited Vulnerability (KEV) present</li>
          <li>+25: CVSS v3.1 or v4.0 score ≥ 7</li>
          <li>+5: HTTP service on non-standard port</li>
          <li>-5: WAF or protective control detected</li>
        </ul>
        <p className="text-xs text-neutral-500 mt-2">These hints guide triage; adjust weights per environment as needed.</p>
      </Modal>
      <div className="rounded-xl border p-4 bg-white">
        <h3 className="text-lg font-semibold">Overview</h3>
        <div className="mt-2 grid grid-cols-3 gap-3 text-sm">
          <Stat label="Hosts" value={sum.counts.hosts} />
          <Stat label="KEV Hosts" value={sum.counts.kev_hosts} />
          <Stat label="High-Risk (≥70)" value={sum.counts.high_risk_hosts} />
        </div>
      </div>
      <div className="rounded-xl border p-4 bg-white">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">LLM Summary</h3>
          <button className="px-3 py-1 rounded bg-black text-white disabled:opacity-50" onClick={onRun} disabled={busy}>
            {busy ? 'Generating…' : 'Generate Summary'}
          </button>
        </div>
        {err && <div className="text-red-500 text-sm mt-2">Error: {err}</div>}
        <pre className="text-xs bg-neutral-900 text-neutral-100 p-3 rounded overflow-auto mt-3">
          {result ? JSON.stringify(result, null, 2) : 'No result yet.'}
        </pre>
      </div>
      <BarList title="Top ASNs" rows={sum.top_asn} onClick={(k) => nav(`host.autonomous_system.name="${k}"`)} />
      <BarList
        title="Top Ports"
        rows={sum.top_ports.map(([p, c]) => [String(p), c])}
        onClick={(k) => nav(`host.services.port = ${k}`)}
      />
      <BarList
        title="Top Countries"
        rows={sum.top_countries}
        onClick={(k) => nav(`host.location.country_code="${k}"`)}
      />
      <div className="rounded-xl border p-4 bg-white">
        <h4 className="font-semibold">Recommendations</h4>
        <ul className="mt-2 list-disc ml-6 text-sm">
          <li>Prioritize KEV-positive assets for immediate remediation.</li>
          <li>Normalize Ollama exposure: allow only 11434 internally; block non-11434 externally.</li>
          <li>Cull noisy AMZ-02 nodes with very high service counts (likely honeypots).</li>
        </ul>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="p-3 rounded-lg bg-slate-50 border">
      <div className="text-slate-600">{label}</div>
      <div className="text-xl font-semibold">{value.toLocaleString()}</div>
    </div>
  );
}

function BarList({
  title,
  rows,
  onClick,
}: {
  title: string;
  rows: [string, number][];
  onClick: (k: string) => void;
}) {
  const max = Math.max(...rows.map(([, n]) => n), 1);
  return (
    <div className="rounded-xl border p-4 bg-white">
      <h4 className="font-semibold">{title}</h4>
      <ul className="mt-3 space-y-2">
        {rows.map(([k, v]) => (
          <li key={k}>
            <button onClick={() => onClick(k)} className="w-full text-left">
              <div className="flex justify-between text-sm">
                <span className="truncate">{k}</span>
                <span>{v.toLocaleString()}</span>
              </div>
              <div className="h-2 bg-slate-100 rounded">
                <div className="h-2 bg-slate-700/70 rounded" style={{ width: `${(v / max) * 100}%` }} />
              </div>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

// Lightweight modal for scoring legend
function Modal({ open, onClose, children }: { open: boolean; onClose: () => void; children: any }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-white border rounded-xl p-4 w-[90vw] max-w-md">
        <div className="flex items-center justify-between mb-2">
          <div className="font-semibold">About risk scoring</div>
          <button className="text-sm" onClick={onClose}>Close</button>
        </div>
        <div className="text-sm text-neutral-700 space-y-2">{children}</div>
      </div>
    </div>
  );
}
