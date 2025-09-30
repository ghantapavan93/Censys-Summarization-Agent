import { X, Copy } from 'lucide-react';
import { useMemo } from 'react';

function wordDiff(a: string, b: string) {
	// naive diff: highlight words present in b but not in a
	const A = new Set(a.split(/\s+/));
	return b.split(/(\s+)/).map((w, i) =>
		A.has(w) || w.trim()==='' ? <span key={i}>{w}</span> : <mark key={i} className="bg-indigo-700/40 px-0.5 rounded">{w}</mark>
	);
}

export default function RewriteDrawer({ open, onClose, original, rewritten }: { open: boolean; onClose: () => void; original: string; rewritten?: string }) {
	if (!open) return null;
	const canCopy = !!rewritten;
	const diff = useMemo(() => (rewritten ? wordDiff(original, rewritten) : null), [original, rewritten]);

	return (
		<div className="fixed inset-0 z-50">
			<div className="absolute inset-0 bg-black/60" onClick={onClose} />
			<div className="absolute right-0 top-0 h-full w-full md:w-[720px] bg-neutral-950 border-l border-neutral-800 p-5 overflow-y-auto">
				<div className="flex items-center justify-between mb-4">
					<h3 className="text-lg font-semibold">Rewrite with AI</h3>
					<button className="btn" onClick={onClose}><X size={16}/> Close</button>
				</div>

				<div className="grid md:grid-cols-2 gap-4">
					<div className="card">
						<div className="text-sm text-neutral-400 mb-2">Original (deterministic)</div>
						<pre className="whitespace-pre-wrap text-neutral-200">{original}</pre>
					</div>
					<div className="card">
						<div className="flex items-center justify-between mb-2">
							<span className="text-sm text-neutral-400">AI Rewrite</span>
							<button className="btn disabled:opacity-50" disabled={!canCopy} onClick={() => navigator.clipboard.writeText(rewritten || '')}><Copy size={16}/> Copy</button>
						</div>
						{rewritten ? (
							<pre className="whitespace-pre-wrap text-neutral-200">{diff}</pre>
						) : (
							<div className="text-neutral-400">No rewrite yet. Close and click “Rewrite with AI” on the summary card.</div>
						)}
					</div>
				</div>
			</div>
		</div>
	);
}

