import { useState } from 'react';
import type { CensAIResponse, SummarizeRequest } from '../lib/types';
import { X } from 'lucide-react';

export default function ExportModal({ open, onClose, lastRaw, lastResponse }: { open: boolean; onClose: () => void; lastRaw: SummarizeRequest | null; lastResponse: CensAIResponse | null; }) {
	const [tab, setTab] = useState<'cli'|'pythonv2'|'platform'|'asm'>('cli');
	if (!open) return null;

	const exampleQuery = lastResponse?.query_trace?.query || "services.service_name: HTTP";

	const cli = `# CLI search (all pages)\ncensys search '${exampleQuery}' --pages -1 | jq -c '.[] | {ip: .ip}'\n\n# View a host\ncensys view 8.8.8.8 -o host.json\ncat host.json | jq '[.services[] | {port: .port, protocol: .service_name}]'\n\n# Subdomains\ncensys subdomains example.com --json`;

	const pyv2 = `from censys.search import CensysHosts\n\nh = CensysHosts()\nq = h.search("${exampleQuery}", per_page=5, pages=2)\nprint(q.view_all())`;

	const platform = `# pip install censys-platform\nfrom censys.platform import Hosts\n\nh = Hosts()\nreport = h.aggregate("${exampleQuery}", "services.port", num_buckets=5)\nprint(report)`;

	const asm = `# Add seeds\ncensys asm add-seeds -j '["1.1.1.1"]'\n# List seeds (CSV)\ncensys asm list-seeds --csv`;

	return (
		<div className="fixed inset-0 z-50">
			<div className="absolute inset-0 bg-black/60" onClick={onClose} />
			<div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[95vw] max-w-3xl bg-neutral-950 border border-neutral-800 rounded-2xl p-5">
				<div className="flex items-center justify-between mb-3">
					<h3 className="text-lg font-semibold">Export Snippets</h3>
					<button className="btn" onClick={onClose}><X size={16}/> Close</button>
				</div>
				<div className="flex gap-2 mb-3">
					{(['cli','pythonv2','platform','asm'] as const).map(t => (
						<button key={t} className={`btn ${tab===t ? 'btn-primary' : ''}`} onClick={() => setTab(t)}>{t.toUpperCase()}</button>
					))}
				</div>
				<pre className="bg-neutral-900 border border-neutral-800 rounded-xl p-4 overflow-auto text-sm">
{tab==='cli' && cli}
{tab==='pythonv2' && pyv2}
{tab==='platform' && platform}
{tab==='asm' && asm}
				</pre>
			</div>
		</div>
	);
}

