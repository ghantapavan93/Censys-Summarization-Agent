import type { CensAIResponse, SummarizeRequest } from './types';

const base = '/api';

export async function summarize(
	body: SummarizeRequest,
	opts?: { rewriteWithAI?: boolean }
): Promise<CensAIResponse> {
	const qs = new URLSearchParams();
	if (opts?.rewriteWithAI) qs.set('rewrite_with_ai', 'true');

	const res = await fetch(`${base}/summarize?${qs.toString()}`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body),
	});
	if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
	return res.json();
}

export async function health(): Promise<boolean> {
	try {
		const r = await fetch(`${base}/health`);
		return r.ok;
	} catch { return false; }
}

