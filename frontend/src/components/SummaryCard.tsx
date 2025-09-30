import type { RiskItem } from '../lib/types';
import { FileText, Wand2, ExternalLink, ShieldAlert } from 'lucide-react';

export default function SummaryCard(props: {
	deterministic: string;
	aiRewritten?: string;
	risks: RiskItem[];
	keyFindings: string[];
	nextActions?: string[];
	validJson?: boolean;
	onRewriteClick: () => void;
	onExportClick: () => void;
}) {
	const { deterministic, aiRewritten, risks, keyFindings, nextActions, validJson, onRewriteClick, onExportClick } = props;

	function sevClass(s: RiskItem['severity']) {
		switch (s) {
			case 'CRITICAL': return 'badge badge-red';
			case 'HIGH': return 'badge badge-amber';
			case 'MEDIUM': return 'badge badge-sky';
			default: return 'badge';
		}
	}

	return (
		<div className="card space-y-5">
			<div className="flex items-center justify-between">
				<div className="flex items-center gap-2">
					<FileText size={18}/>
					<h3 className="text-lg font-semibold">Deterministic Summary</h3>
					{validJson ? (
						<span className="badge badge-green">Validated JSON</span>
					) : (
						<span className="badge">Unverified</span>
					)}
				</div>
				<div className="flex items-center gap-2">
					<button className="btn" onClick={onExportClick}><ExternalLink size={16}/> Export</button>
					<button className="btn btn-primary" onClick={onRewriteClick}><Wand2 size={16}/> Rewrite with AI</button>
				</div>
			</div>

			<p className="leading-relaxed whitespace-pre-wrap">{deterministic}</p>

			{aiRewritten && (
				<div className="bg-neutral-950 border border-neutral-800 rounded-xl p-4">
					<div className="flex items-center gap-2 mb-2"><Wand2 size={16}/><span className="font-medium">Latest AI Rewrite (preview)</span></div>
					<p className="text-neutral-300 whitespace-pre-wrap">{aiRewritten}</p>
				</div>
			)}

			{keyFindings?.length > 0 && (
				<div>
					<h4 className="mb-2 font-medium">Key Findings</h4>
					<ul className="list-disc ml-6 space-y-1 text-neutral-300">
						{keyFindings.map((k, i) => <li key={i}>{k}</li>)}
					</ul>
				</div>
			)}

			{risks?.length > 0 && (
				<div>
					<h4 className="mb-2 font-medium flex items-center gap-2"><ShieldAlert size={16}/> Risks</h4>
					<div className="grid md:grid-cols-2 gap-3">
						{risks.map((r, i) => (
							<div key={i} className="bg-neutral-950 border border-neutral-800 rounded-xl p-4">
								<div className="flex items-center justify-between mb-1">
									<div className="font-medium">{r.title}</div>
									<span className={sevClass(r.severity)}>{r.severity}</span>
								</div>
								{r.related_cves?.length > 0 && (
									<div className="text-xs text-neutral-400 mb-1">CVEs: {r.related_cves.join(', ')}</div>
								)}
								<div className="text-sm text-neutral-300 mb-2">{r.why_it_matters}</div>
								{r.evidence?.length > 0 && (
									<ul className="text-xs text-neutral-400 list-disc ml-5">
										{r.evidence.slice(0,4).map((e, j) => <li key={j}>{e}</li>)}
									</ul>
								)}
								{r.recommended_fix && (
									<div className="text-sm mt-2"><span className="text-neutral-400">Fix:</span> {r.recommended_fix}</div>
								)}
							</div>
						))}
					</div>
				</div>
			)}

			{nextActions?.length ? (
				<div>
					<h4 className="mb-2 font-medium">Next Actions</h4>
					<ol className="list-decimal ml-6 space-y-1 text-neutral-300">
						{nextActions.map((a, i) => <li key={i}>{a}</li>)}
					</ol>
				</div>
			) : null}
		</div>
	);
}

