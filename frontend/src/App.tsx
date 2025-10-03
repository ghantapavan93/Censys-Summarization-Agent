import { Suspense, useEffect, useMemo, useState, lazy, startTransition } from 'react';
import { summarize, health } from './lib/api';
import type { CensAIResponse, SummarizeRequest, VizPayload, VizSeries as UIVizSeries } from './lib/types';
import UploadPanel from './components/UploadPanel';
import SummaryCard from './components/SummaryCard';
const RewriteDrawer = lazy(() => import('./components/RewriteDrawer.tsx'));
const ChartsPanel = lazy(() => import('./components/ChartsPanel.tsx'));
const ExportModal = lazy(() => import('./components/ExportModal.tsx'));
import BrandHeader from './components/BrandHeader';
import KPIRow from './components/KPIRow';
import { Callouts, ClustersTable } from './components/Callouts';
import { ToastProvider, useToast } from './components/Toast';
import SettingsModal, { loadSettings, saveSettings, type Settings } from './components/SettingsModal';
import { SAMPLE } from './lib/sample';
import SearchPage from './pages/Search';
import SummaryPage from './pages/Summary';
import FilterBar, { type Filter } from './components/FilterBar';
import TrendsRow from './components/TrendsRow';
import SavedViewsBar from './components/SavedViewsBar';

// Map backend viz payload (list of series) to UI shape
 type BackendVizSeries = { type: string; title: string; data: Array<[string, number]> };
 type BackendVizPayload = { charts: BackendVizSeries[]; histograms?: Record<string, Record<string, number>>; top_ports?: Record<string, number> };

function toUIVizPayload(v?: BackendVizPayload): VizPayload | undefined {
  if (!v) return undefined;
  const out: VizPayload = { charts: {} as any };
  for (const s of v.charts || []) {
    const ui: UIVizSeries = {
      id: s.title.toLowerCase().replace(/\s+/g, '_'),
      label: s.title,
      data: (s.data || []).map(([key, count]) => ({ key, count })),
    };
    const key = ui.label.toLowerCase();
    if (key.includes('port')) (out.charts as any).top_ports = ui;
    else if (key.includes('protocol')) (out.charts as any).top_protocols = ui;
    else if (key.includes('software')) (out.charts as any).top_software = ui;
    else if (key.includes('country')) (out.charts as any).countries = ui;
  }
  return out;
}

function AppInner() {
  const [resp, setResp] = useState<CensAIResponse | null>(null);
  const [raw, setRaw] = useState<SummarizeRequest | null>(null);
  const [loading, setLoading] = useState(false);
  const [showRewrite, setShowRewrite] = useState(false);
  const [showExport, setShowExport] = useState(false);
  const [healthy, setHealthy] = useState<boolean | null>(null);
  const toast = useToast();
  const [settings, setSettings] = useState<Settings>(loadSettings());
  const [showSettings, setShowSettings] = useState(false);
  const [filters, setFilters] = useState<Filter[]>([]);

  useEffect(() => {
    health().then(setHealthy).catch(() => setHealthy(false));
  }, [settings.backendBase]);

  const uiResp = useMemo(() => {
    if (!resp) return null;
    // Map backend to UI-friendly shape where needed
    // Prefer pipeline-style risks; fall back to deterministic key_risks
    const rawRisks = (resp as any).risks || (resp as any).key_risks || [];
    let risks = (rawRisks as any[]).map((r: any) => ({
      id: r.id || r.title || r.context || '',
      title: r.title || r.context || r.id || '',
      severity: String(r.severity || 'LOW').toUpperCase(),
      evidence: r.evidence || [],
      related_cves: r.related_cves || [],
      why_it_matters: r.why_it_matters || r.context || '',
      recommended_fix: r.recommended_fix || '',
      kev: !!r.kev,
      cvss: typeof r.cvss === 'number' ? r.cvss : undefined,
      epss: typeof r.epss === 'number' ? r.epss : undefined,
      details: r.details,
    }));
    // Consolidate low-severity port noise into a single card as per spec
    try {
      const portRx = /Service exposed on port\s+(\d+)/i;
      const lows = risks.filter(r => r.severity === 'LOW' && portRx.test(r.title || ''));
      if (lows.length >= 2) {
        const ports: number[] = [];
        for (const r of lows) {
          const m = (r.title || '').match(portRx); if (m) ports.push(parseInt(m[1], 10));
        }
        // Exclude standard/common ports from this aggregation
        const STANDARD_PORTS = new Set([80, 443, 22, 21, 3306]);
        const uniq = Array.from(new Set(ports)).filter(p => !STANDARD_PORTS.has(p)).sort((a,b)=>a-b);
        // Remove individual
        risks = risks.filter(r => !(r.severity === 'LOW' && portRx.test(r.title || '')));
        // Add consolidated
        if (uniq.length) risks.push({
          id: 'risk:uncommon-web-admin-ports',
          title: 'Uncommon web/admin ports',
          severity: 'LOW' as const,
          evidence: uniq.map(p => `port ${p}`),
          related_cves: [],
          why_it_matters: 'Uncommon ports increase scan and exposure surface; often unauthenticated admin UIs.',
          recommended_fix: 'Restrict by IP, require auth, put behind reverse proxy/Web Application Firewall.',
          kev: false,
          cvss: undefined,
          epss: undefined,
          details: undefined,
        } as any);
      }
      // Helper to compute highest severity among items as a typed union
      const sevLevels: Array<'LOW'|'MEDIUM'|'HIGH'|'CRITICAL'> = ['LOW','MEDIUM','HIGH','CRITICAL'];
      const highestSev = (arr: any[]): 'LOW'|'MEDIUM'|'HIGH'|'CRITICAL' => {
        let maxIdx = 0;
        for (const r of arr) {
          const s = String(r.severity || 'LOW').toUpperCase();
          const idx = sevLevels.indexOf((['LOW','MEDIUM','HIGH','CRITICAL'].includes(s) ? s : 'LOW') as any);
          if (idx > maxIdx) maxIdx = idx;
        }
        return sevLevels[maxIdx];
      };

      // Merge SSH exposures into one card
      const ssh = risks.filter(r => (r.title || '').toLowerCase().includes('openssh exposure'));
      if (ssh.length > 1) {
        const merged = {
          id: 'risk:ssh-exposure:merged',
          title: 'OpenSSH exposure',
          severity: highestSev(ssh),
          evidence: ssh.flatMap(r => Array.isArray(r.evidence) ? r.evidence : []).slice(0, 6),
          related_cves: Array.from(new Set(ssh.flatMap(r => r.related_cves || []))),
          why_it_matters: ssh.find(r => r.why_it_matters)?.why_it_matters || 'Common brute-force surface; outdated versions carry critical CVEs.',
          recommended_fix: ssh.find(r => r.recommended_fix)?.recommended_fix || 'Keys+MFA, fail2ban; patch to latest LTS; restrict via bastion.',
          kev: ssh.some(r => (r as any).kev),
          cvss: Math.max(...ssh.map(r => (r as any).cvss || 0)),
          epss: Math.max(...ssh.map(r => (r as any).epss || 0)),
          details: undefined,
        } as any;
        risks = risks.filter(r => !(r.title || '').toLowerCase().includes('openssh exposure'));
        risks.unshift(merged as any);
      }
      // Merge FTP detections into one card
      const ftp = risks.filter(r => (r.title || '').toLowerCase().includes('ftp service detected'));
      if (ftp.length > 1) {
        const merged = {
          id: 'risk:ftp-detected:merged',
          title: 'FTP service detected',
          severity: highestSev(ftp),
          evidence: ftp.flatMap(r => Array.isArray(r.evidence) ? r.evidence : []).slice(0, 6),
          related_cves: Array.from(new Set(ftp.flatMap(r => r.related_cves || []))),
          why_it_matters: ftp.find(r => r.why_it_matters)?.why_it_matters || 'Legacy protocol; cleartext creds/files common.',
          recommended_fix: ftp.find(r => r.recommended_fix)?.recommended_fix || 'Disable or migrate to SFTP/FTPS; scope to internal.',
          kev: ftp.some(r => (r as any).kev),
          cvss: Math.max(...ftp.map(r => (r as any).cvss || 0)),
          epss: Math.max(...ftp.map(r => (r as any).epss || 0)),
          details: undefined,
        } as any;
        risks = risks.filter(r => !(r.title || '').toLowerCase().includes('ftp service detected'));
        risks.unshift(merged as any);
      }
      // Keep grouped cards but do not trim away other risks (e.g., MySQL)
    } catch {}
    const key_findings = Array.isArray((resp as any).key_findings)
      ? (resp as any).key_findings.map((k: any) => (typeof k === 'string' ? k : (k.title || k.id)))
      : [];
    const viz_payload = toUIVizPayload(((resp as any).viz_payload) as BackendVizPayload);
    // Also map deterministic recommendations to next_actions if pipeline didn't supply them
    const next_actions = (resp as any).next_actions || (resp as any).recommendations || [];
  return { ...resp, risks, key_findings, viz_payload, next_actions } as CensAIResponse;
  }, [resp]);

  // Low-priority, frame-aligned updates improve responsiveness on big payloads
  function updateRespLowPri(next: CensAIResponse, nextRaw?: SummarizeRequest | null) {
    requestAnimationFrame(() => {
      startTransition(() => {
        setResp(next);
        if (typeof nextRaw !== 'undefined') setRaw(nextRaw);
      });
    });
  }

  async function onSummarize(input: SummarizeRequest) {
    setLoading(true);
    try {
  const r = await summarize(input, { rewriteWithAI: false });
      updateRespLowPri(r, input);
      // Proactively prefetch AI rewrite in the background so it's ready when the user clicks
      // This keeps the initial summarize responsive while preparing overview_llm.
      // If the LLM/model isn't available, we fail-soft and keep the deterministic overview.
      try {
        void summarize(input, { rewriteWithAI: true })
          .then((rr) => {
            // Merge by replacing response with LLM-enriched version
            updateRespLowPri(rr);
          })
          .catch(() => {/* ignore background rewrite errors */});
      } catch {}
      if (settings.persistInput) try { localStorage.setItem('censys_last_input', JSON.stringify(input)); } catch {}
    } catch (e: any) {
      console.error(e);
      const detail = e?.detail;
      if (detail && e?.message?.includes('strict validation failed')) {
        const errs = Array.isArray(detail?.errors) ? detail.errors.length : 0;
        const warns = Array.isArray(detail?.warnings) ? detail.warnings.length : 0;
        toast.push('error', `Strict validation blocked: ${errs} errors • ${warns} warnings`);
      } else {
        toast.push('error', 'Summarize failed — using sample data');
        updateRespLowPri(SAMPLE);
      }
    } finally { setLoading(false); }
  }

  async function onRewrite(opts?: { style?: string; language?: string }) {
    if (!raw) return setShowRewrite(true); // open drawer, show current (maybe sample)
    setLoading(true);
    try {
  const r = await summarize(raw, { rewriteWithAI: true, style: opts?.style, language: opts?.language });
      updateRespLowPri(r);
      setShowRewrite(true);
    } catch (e) {
      console.error(e);
  toast.push('error', 'Rewrite failed — showing previous');
      setShowRewrite(true);
    } finally { setLoading(false); }
  }

  // Load last input on mount if enabled
  useEffect(() => {
    if (!settings.persistInput) return;
    try {
      const s = localStorage.getItem('censys_last_input');
      if (s) setRaw(JSON.parse(s));
    } catch {}
  }, [settings.persistInput]);

  return (
    <>
      <BrandHeader healthy={healthy} onOpenSettings={() => setShowSettings(true)} />
      <main className="app-wrap">
  <UploadPanel onSubmit={onSummarize} loading={loading} />

        {!uiResp && (
          <div className="text-center text-neutral-400 py-10">
            <div className="text-sm">Paste or upload a dataset to get started. Or try the sample to explore the UI.</div>
          </div>
        )}

        {uiResp && (
          <>
            {/* KPI stat row (first) */}
            <KPIRow totals={uiResp.totals} topPort={(uiResp.top_ports && uiResp.top_ports[0]?.port) || undefined} flags={uiResp.flags} />

            {/* Trends row (30d sparklines) */}
            <TrendsRow />

            {/* Graphs above text */}
            <Suspense fallback={<div className="card">Loading charts…</div>}>
              <ChartsPanel
                viz={uiResp.viz_payload}
                severity={uiResp.severity_matrix}
                topPorts={uiResp.top_ports}
                countries={uiResp.assets_by_country}
                onFilter={(f) => setFilters(prev => [...prev, f])}
              />
            </Suspense>

            <SavedViewsBar filters={filters} />
            <FilterBar
              filters={filters}
              onRemove={(idx) => setFilters(prev => prev.filter((_, i) => i !== idx))}
              onClear={() => setFilters([])}
            />

            {/* AI overview is shown in the Rewrite drawer only (no inline card) */}

            {(() => {
              // Executive Overview (AI Rewrite + deterministic)
              const data: any = resp;
              const deterministic = ((data?.overview ?? uiResp.overview_deterministic ?? uiResp.summary) ?? '').toString();
              // AI overview is rendered by ExecutiveOverviewCard
              // Apply filters to risks client-side
              const filteredRisks = (uiResp.risks || []).filter((r: any) => {
                return filters.every((f) => {
                  if (f.type === 'severity') return String(r.severity).toUpperCase() === String(f.value).toUpperCase();
                  if (f.type === 'port') return (r.evidence || []).some((e: string) => new RegExp(`:${f.value}(\\s|$)`).test(String(e)) || /port\s+\d+/.test(String(e)) && e.includes(String(f.value)));
                  if (f.type === 'country') return (r.evidence || []).some((e: string) => e.toLowerCase().includes(f.value.toLowerCase()));
                  return true;
                });
              });
              // Enhance uncommon ports card title with count if present
              for (const rr of filteredRisks) {
                if ((rr.title || '').toLowerCase() === 'uncommon web/admin ports' && Array.isArray(rr.evidence)) {
                  const ports = rr.evidence.filter((e: string) => /^port\s+\d+$/.test(String(e))).length;
                  if (ports > 0) rr.title = `Uncommon web/admin ports (${ports})`;
                }
              }
              return (
                <SummaryCard
                  deterministic={deterministic}
                  aiRewritten={undefined /* avoid duplicate preview; AI card now owns it */}
                  risks={filteredRisks}
                  keyFindings={uiResp.key_findings || []}
                  nextActions={uiResp.next_actions}
                  validJson={uiResp.meta?.valid_json}
                  meta={uiResp.meta}
                  rawJson={raw || null}
                  rawResponse={resp}
                  onRewriteClick={onRewrite}
                  onExportClick={() => setShowExport(true)}
                  delta={(uiResp as any).delta}
                />
              );
            })()}

            {/* KEV/CVSS callouts after overview */}
            <Callouts kev={uiResp.flags?.kev_total} cvss={uiResp.flags?.cvss_high_total} />

            {/* Clusters */}
            <ClustersTable rows={uiResp.clusters} />

            <Suspense>
              <RewriteDrawer
                open={showRewrite}
                onClose={() => setShowRewrite(false)}
                original={(((resp as any)?.overview ?? uiResp.overview_deterministic ?? uiResp.summary) ?? '').toString()}
                rewritten={uiResp.overview_llm}
                meta={(uiResp as any).ai_overview}
                onRegenerate={onRewrite}
                raw={(uiResp as any).overview_llm_raw}
              />
            </Suspense>

            <Suspense>
              <ExportModal
                open={showExport}
                onClose={() => setShowExport(false)}
                lastResponse={{...uiResp, risks: (uiResp.risks || [])}}
              />
            </Suspense>
          </>
        )}

  <footer className="text-xs text-neutral-500 pt-4">© {new Date().getFullYear()} Censys Summarization Agent Demo{uiResp?.meta?.request_id ? ` • request_id: ${uiResp.meta.request_id}` : ''}</footer>
      </main>

      {loading && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40">
          <div className="bg-canvas border border-border rounded-xl px-4 py-2 text-sm text-neutral-300">Working…</div>
        </div>
      )}

      <SettingsModal
        open={showSettings}
        onClose={() => setShowSettings(false)}
        onSave={(s) => { setSettings(s); saveSettings(s); setShowSettings(false); toast.push('success', 'Settings saved'); }}
      />
    </>
  );
}

export default function App() {
  return (
    <ToastProvider>
      {/* Fingerprint banner: proves which frontend build and API base are used */}
      <div style={{position:'fixed', top: 0, right: 0, zIndex: 50, padding: '2px 6px', fontSize: 10, color: '#94a3b8'}}>
        API_BASE: {import.meta.env.VITE_API_BASE || '(proxy /api)'} • BuildTS: {new Date().toISOString()}
      </div>
      {(() => {
        const path = typeof window !== 'undefined' ? window.location.pathname : '/';
        if (path.startsWith('/search')) return <SearchPage />;
        // Summary page expects hosts prop; keep demo: use sample hosts if none
        if (path.startsWith('/summary')) return <SummaryPage hosts={(SAMPLE as any).meta?.hosts_sample || []} />;
        return <AppInner />;
      })()}
    </ToastProvider>
  );
}