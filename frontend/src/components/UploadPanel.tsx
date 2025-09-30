import { useState } from 'react';
import type React from 'react';
import type { SummarizeRequest } from '../lib/types';
import { Upload, Play } from 'lucide-react';

export default function UploadPanel({ onSubmit, loading }: { onSubmit: (body: SummarizeRequest) => void; loading: boolean }) {
	const [text, setText] = useState('');
	const [parsed, setParsed] = useState<any | null>(null);

	function parseText() {
		try {
			const obj = JSON.parse(text);
			setParsed(obj);
		} catch (e) {
			alert('Invalid JSON');
		}
	}

	function onFile(e: React.ChangeEvent<HTMLInputElement>) {
		const file = e.target.files?.[0];
		if (!file) return;
		const reader = new FileReader();
		reader.onload = () => {
			setText(String(reader.result || ''));
			try { setParsed(JSON.parse(String(reader.result || ''))); } catch { /* ignore */ }
		};
		reader.readAsText(file);
	}

	function buildPayload(): SummarizeRequest | null {
		if (!parsed) return null;
		// Accept {hosts}, {records}, or raw array
		if (Array.isArray(parsed)) return { hosts: parsed };
		if (parsed.hosts || parsed.records || parsed.raw_records) return parsed;
		return { hosts: [parsed] }; // best-effort
	}

	const payload = buildPayload();
	const ready = !!payload && !loading;

	return (
		<div className="card">
			<div className="flex items-center justify-between mb-3">
				<h2 className="text-lg font-medium">Upload / Paste Dataset</h2>
				<label className="btn cursor-pointer">
					<Upload size={16}/><span>Choose JSON</span>
					<input type="file" accept="application/json" className="hidden" onChange={onFile} />
				</label>
			</div>

			<textarea
				className="w-full h-48 p-3 rounded-xl bg-neutral-950 border border-neutral-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
				placeholder='Paste JSON here (e.g., { "hosts": [...] })'
				value={text}
				onChange={e => setText(e.target.value)}
			/>

			<div className="mt-3 flex items-center gap-3">
				<button className="btn" onClick={parseText}>Validate JSON</button>
				<button className="btn btn-primary disabled:opacity-50" disabled={!ready} onClick={() => payload && onSubmit(payload)}>
					<Play size={16}/> Summarize
				</button>
				{parsed && (
					<span className="text-xs text-neutral-400">Parsed OK • keys: {Object.keys(parsed).slice(0,5).join(', ')}{Object.keys(parsed).length>5 ? '…' : ''}</span>
				)}
			</div>
		</div>
	);
}

