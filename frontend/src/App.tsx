import { useEffect, useState } from 'react';
import { summarize } from './lib/api';
import type { CensAIResponse, SummarizeRequest } from './lib/types';
import UploadPanel from './components/UploadPanel';
import SummaryCard from './components/SummaryCard';
import RewriteDrawer from './components/RewriteDrawer';
import ChartsPanel from './components/ChartsPanel';
import ExportModal from './components/ExportModal';
import { CheckCircle, CircleAlert } from 'lucide-react';
import { getDemoData } from './lib/demo';

export default function App() {
	const [resp, setResp] = useState<CensAIResponse | null>(null);
	const [raw, setRaw] = useState<SummarizeRequest | null>(null);
	const [loading, setLoading] = useState(false);
	const [showRewrite, setShowRewrite] = useState(false);
	const [showExport, setShowExport] = useState(false);
	const [healthy, setHealthy] = useState<boolean | null>(null);

	useEffect(() => {
		fetch('/api/health').then(r => setHealthy(r.ok)).catch(() => setHealthy(false));
    const url = new URL(window.location.href);
    if (url.searchParams.get('demo') === '1') {
      activateDemo();
    }
	}, []);

	async function onSummarize(input: SummarizeRequest) {
		setLoading(true);
		try {
			const r = await summarize(input, { rewriteWithAI: false });
			setResp(r); setRaw(input);
		} catch (e) {
			console.error(e);
			alert('Summarize failed. Check backend logs.');
		} finally { setLoading(false); }
	}

	async function onRewrite() {
		if (!raw) return;
		setLoading(true);
		try {
			const r = await summarize(raw, { rewriteWithAI: true });
			setResp(r); setShowRewrite(true);
		} catch (e) {
			console.error(e);
			alert('Rewrite failed.');
		} finally { setLoading(false); }
	}

	function activateDemo() {
		const { raw, resp } = getDemoData();
		setRaw(raw);
		setResp(resp);
	}

	return (
		<div className="mx-auto max-w-7xl p-6 space-y-6 text-neutral-200">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Censys Summarizer</h1>
        <div className="flex items-center gap-2">
          {healthy === true ? (
            <span className="badge badge-green"><CheckCircle size={16}/> Backend OK</span>
          ) : healthy === false ? (
            <span className="badge badge-red"><CircleAlert size={16}/> Backend Unreachable</span>
          ) : null}
          <button className="btn" onClick={activateDemo}>Demo Preview</button>
        </div>
      </header>

			<UploadPanel onSubmit={onSummarize} loading={loading} />

			{resp && (
				<>
					<SummaryCard
						deterministic={resp.overview_deterministic ?? resp.summary}
						aiRewritten={resp.overview_llm}
						risks={resp.risks}
						keyFindings={resp.key_findings}
						nextActions={resp.next_actions}
						validJson={resp.meta?.valid_json}
						onRewriteClick={onRewrite}
						onExportClick={() => setShowExport(true)}
					/>

					<ChartsPanel viz={resp.viz_payload} />

					<RewriteDrawer
						open={showRewrite}
						onClose={() => setShowRewrite(false)}
						original={resp.overview_deterministic ?? resp.summary}
						rewritten={resp.overview_llm}
					/>

					<ExportModal
						open={showExport}
						onClose={() => setShowExport(false)}
						lastRaw={raw}
						lastResponse={resp}
					/>
				</>
			)}

			<footer className="text-xs text-neutral-500 pt-4">© {new Date().getFullYear()} Censys Summarization Agent Demo</footer>
		</div>
	);
}

