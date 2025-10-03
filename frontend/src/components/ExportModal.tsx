import { useMemo, useState } from 'react';
import type { CensAIResponse } from '../lib/types';
import { X, Copy } from 'lucide-react';
import api from '../lib/api';
import { useToast } from './Toast';

export default function ExportModal({ open, onClose, lastResponse }: { open: boolean; onClose: () => void; lastResponse: CensAIResponse | null; }) {
  const [tab, setTab] = useState<'cli'|'pythonv2'|'platform'|'asm'>('cli');
  const exampleQuery = useMemo(() => (lastResponse as any)?.query_trace?.query || "services.service_name: HTTP", [lastResponse]);
  const toast = useToast();

  if (!open) return null;

  // Wrap snippets as strings to avoid JSX parsing issues with { ... }
  const cli = `# CLI search (all pages)
censys search '${exampleQuery}' --pages -1 | jq -c '.[] | {ip: .ip}'

# View a host
censys view 8.8.8.8 -o host.json
cat host.json | jq '[.services[] | {port: .port, protocol: .service_name}]'`;

  const pyv2 = `from censys.search import CensysHosts

h = CensysHosts()
q = h.search("${exampleQuery}", per_page=5, pages=2)
print(q.view_all())`;

  const platform = `# pip install censys-platform
from censys.platform import Hosts

h = Hosts()
report = h.aggregate("${exampleQuery}", "services.port", num_buckets=5)
print(report)`;

  const asm = `# Add seeds
censys asm add-seeds -j '["1.1.1.1"]'
# List seeds (CSV)
censys asm list-seeds --csv`;

  function currentSnippet() {
    switch (tab) {
      case 'cli': return cli;
      case 'pythonv2': return pyv2;
      case 'platform': return platform;
      case 'asm': return asm;
    }
  }

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[95vw] max-w-3xl bg-canvas border border-border rounded-2xl p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold">Export Snippets</h3>
          <div className="flex items-center gap-2">
            <button className="btn" onClick={async () => {
              try {
                const data = lastResponse || ({} as any);
                const body = {
                  overview: (data as any).overview_llm || data.overview_deterministic || data.overview,
                  overview_deterministic: data.overview_deterministic || data.overview,
                  key_risks: (data as any).risks || (data as any).key_risks || [],
                  recommendations: (data as any).next_actions || (data as any).recommendations || [],
                  flags: data.flags,
                  totals: data.totals,
                  severity_matrix: data.severity_matrix,
                };
                const result = await api.exportPDF(body);
                if (result.success) {
                  toast.push('success', `PDF brief downloaded: ${result.filename}`, { timeoutMs: 3000 });
                } else {
                  toast.push('error', 'Failed to generate PDF brief', { timeoutMs: 3000 });
                }
              } catch (e) { 
                console.error(e); 
                toast.push('error', 'Failed to export PDF', { timeoutMs: 3000 });
              }
            }}>PDF Brief</button>
            <button className="btn" onClick={() => navigator.clipboard.writeText(currentSnippet())}><Copy size={16}/> Copy</button>
            <button className="btn" onClick={onClose}><X size={16}/> Close</button>
          </div>
        </div>
        <div className="flex gap-2 mb-3">
          {(['cli','pythonv2','platform','asm'] as const).map(t => (
            <button key={t} className={`btn ${tab===t ? 'btn-primary' : ''}`} onClick={() => setTab(t)}>{t.toUpperCase()}</button>
          ))}
        </div>
        <pre className="bg-[#0b0f14] border border-border rounded-xl p-4 overflow-auto text-sm">
{tab==='cli' && cli}
{tab==='pythonv2' && pyv2}
{tab==='platform' && platform}
{tab==='asm' && asm}
        </pre>
      </div>
    </div>
  );
}
