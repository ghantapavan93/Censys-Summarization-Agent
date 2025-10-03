import { useEffect, useMemo, useState, useCallback, useRef } from 'react';
import type { SummarizeRequest } from '../lib/types';
import { validateSummarizeText } from '../lib/validate';
import { postTelemetry } from '../lib/api';
import ConfirmModal from './ConfirmModal';
import { useToast } from './Toast';
import { Upload, Play, HelpCircle, Download } from 'lucide-react';
import { loadSettings } from './SettingsModal';
import sampleJson from '../assets/sample.json';
const PENDING_SAMPLE_KEY = 'censys_pending_sample_json';
// Feature flags (default off). Configure in frontend/.env.local
const RESTORE = import.meta.env.VITE_RESTORE_DATASET === '1';

export default function UploadPanel({ onSubmit, loading }: { onSubmit: (body: SummarizeRequest) => void; loading: boolean; }) {
  const [text, setText] = useState('');
  const [parsed, setParsed] = useState<any | null>(null);
  const [err, setErr] = useState<string>('');
  const [warnings, setWarnings] = useState<string[]>([]);
  const [stats, setStats] = useState<{ items: number; approxBytes: number } | null>(null);
  const [progress, setProgress] = useState<number>(0);
  const [hasFixed, setHasFixed] = useState<boolean>(false);
  const [dontSaveFixed, setDontSaveFixed] = useState<boolean>(() => {
    try { return localStorage.getItem('censys_fixed_nosave') === '1'; } catch { return false; }
  });
  const settings = useMemo(() => loadSettings(), []);
  const debounceRef = useRef<number | null>(null);
  const taRef = useRef<HTMLTextAreaElement | null>(null);
  const POLICY = (() => { try { return (localStorage.getItem('validation_policy') || (import.meta as any).env?.VITE_VALIDATION_POLICY || 'lenient').toLowerCase(); } catch { return (import.meta as any).env?.VITE_VALIDATION_POLICY || 'lenient'; } })() as 'lenient' | 'strict' | 'off';
  const { push: toast } = useToast();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const pendingActionRef = useRef<null | (() => void)>(null);

  // On first mount, if Use Sample queued a JSON before reload, hydrate it
  useEffect(() => {
    try {
      const pending = localStorage.getItem(PENDING_SAMPLE_KEY);
      if (pending) {
        setText(pending);
        try { setParsed(JSON.parse(pending)); } catch {}
        localStorage.removeItem(PENDING_SAMPLE_KEY);
      }
      // Prune expired fixed copy (TTL default 1h)
      const metaRaw = localStorage.getItem('censys_fixed_meta');
      const copy = localStorage.getItem('censys_fixed_copy');
      if (metaRaw && copy) {
        try {
          const meta = JSON.parse(metaRaw);
          const exp = Number(meta?.expires_at || 0);
          if (exp && Date.now() > exp) {
            localStorage.removeItem('censys_fixed_copy');
            localStorage.removeItem('censys_fixed_meta');
          }
        } catch {}
      }
      setHasFixed(!!localStorage.getItem('censys_fixed_copy'));
    } catch {}
  }, []);

  useEffect(() => {
    // Only restore previous raw input when explicitly enabled via env flag AND setting
    if (!RESTORE || !settings.persistInput) return;
    try {
      const s = localStorage.getItem('censys_last_input_raw');
      // Only restore if we didn’t just hydrate from a pending sample
      if (s && !text) setText(s);
    } catch {}
  }, [settings.persistInput]);

  const parseText = useCallback(() => {
    const result = validateSummarizeText(text);
    setWarnings(result.warnings);
    setStats({ items: result.stats.items, approxBytes: result.stats.approxBytes });
    const policy = (window as any)._VALIDATION_POLICY || POLICY;
    const fatal = (result.fatalErrors || []).length;
    const strictBlocks = (result.strictBlockers || []).length;
    const errorsCt = result.errors.length;
    const warnsCt = result.warnings.length;

    // Show status pill via toast aligned to policy
    if (policy === 'off') {
      toast('success', '✅ Parsed OK (validation skipped)');
    } else if (policy === 'strict') {
      const msg = `❌ ${errorsCt + strictBlocks + fatal} errors • ${warnsCt} warnings (blocks)`;
      if (errorsCt + strictBlocks + fatal > 0) toast('error', msg); else toast('success', '✅ No blocking issues');
    } else {
      const msg = `⚠️ ${errorsCt} errors • ${warnsCt} warnings (autofix available)`;
  toast(errorsCt ? 'info' : 'success', errorsCt ? msg : '✅ No errors • Warnings allowed');
    }

    // Post telemetry best-effort
    try {
      void postTelemetry({
        policy: policy as any,
        errors_count: errorsCt + fatal + (policy === 'strict' ? strictBlocks : 0),
        warnings_count: warnsCt,
        fixed_fields: result.telemetry || {},
        blocked: policy === 'strict' ? (errorsCt + fatal + strictBlocks) > 0 : fatal > 0,
        request_id: null,
      });
    } catch {}

    if (result.valid && result.payload) {
      setParsed(result.payload.hosts || result.payload.records || result.payload.raw_records || result.payload);
      setErr('');
      if (!dontSaveFixed && result.autofixApplied && result.fixed) {
        try {
          localStorage.setItem('censys_fixed_copy', JSON.stringify(result.fixed));
          localStorage.setItem('censys_fixed_meta', JSON.stringify({ saved_at: Date.now(), expires_at: Date.now() + 60 * 60 * 1000 }));
        } catch {}
      }
      setHasFixed(!!result.fixed && !dontSaveFixed);
    } else {
      setParsed(null);
      setErr(result.errors[0] || 'Invalid JSON');
    }
  }, [text, POLICY, dontSaveFixed]);

  function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setErr('');
    setProgress(0);
    const reader = new FileReader();
    reader.onloadstart = () => setProgress(0);
    reader.onload = () => {
      const s = String(reader.result || '');
      setText(s);
      try {
        setParsed(JSON.parse(s));
        setErr('');
      } catch (e: any) {
        setParsed(null);
        setErr(`Invalid JSON in file: ${e?.message || 'unknown parse error'}`);
      }
      setProgress(100);
      setTimeout(() => setProgress(0), 600);
      e.currentTarget.value = '';
    };
    reader.onprogress = (ev) => {
      if (ev.lengthComputable) setProgress(Math.round((ev.loaded / ev.total) * 100));
    };
    reader.onerror = () => {
      setErr('Failed to read file.');
      setProgress(0);
      e.currentTarget.value = '';
    };
    reader.readAsText(file);
  }

  function buildPayload(): SummarizeRequest | null {
    if (!parsed) return null;
    if (Array.isArray(parsed)) return { hosts: parsed };
    if (parsed.hosts || parsed.records || parsed.raw_records) return parsed;
    return { hosts: [parsed] };
  }

  const payload = buildPayload();
  const ready = !!payload && !loading;
  function handleSummarizeClick() {
    // Quick parse gate: ensure JSON parses; otherwise stop early
    const quick = (() => {
      try {
        if (!text?.trim()) return { ok: false };
        JSON.parse(text);
        return { ok: true };
      } catch { return { ok: false }; }
    })();
    if (!quick.ok) { toast('error', 'JSON does not parse yet. Fix parse errors and try again.'); return; }

    // Policy-controlled validation
    const policy = (window as any)._VALIDATION_POLICY || POLICY;
    if (policy !== 'off') {
      const full = validateSummarizeText(text);
      const hasErrors = full.errors.length > 0;
      const warnCt = full.warnings.length;
      const kev = full.stats.kevCount || 0; const cvssHi = full.stats.cvssHighCount || 0;
      if ((window as any)._VALIDATION_POLICY === 'lenient' && (kev > 0 || cvssHi > 0)) {
        toast('info', 'High-risk content found (KEV/CVSS≥7). Strict is recommended.');
      }
      // Blocking-lite rails in lenient: stop on fatal shape issues
      const fErrs = (full as any).fatalErrors as string[] | undefined;
      const strictBlocks = (full as any).strictBlockers as string[] | undefined;
      if (Array.isArray(fErrs) && fErrs.length > 0) {
        setErr(fErrs[0]);
        setWarnings(full.warnings);
        setStats({ items: full.stats.items, approxBytes: full.stats.approxBytes });
        toast('error', `Found ${fErrs.length} fatal issue(s). Please fix and retry.`);
        return;
      }
      if (hasErrors || (policy === 'strict' && Array.isArray(strictBlocks) && strictBlocks.length > 0)) {
        if (policy === 'strict') {
          const total = full.errors.length + (strictBlocks?.length || 0);
          toast('error', `Found ${total} blocking validation error(s).`);
          setErr(full.errors[0]); setWarnings(full.warnings);
          setStats({ items: full.stats.items, approxBytes: full.stats.approxBytes });
          try { void postTelemetry({ policy: 'strict', errors_count: total, warnings_count: warnCt, fixed_fields: full.telemetry || {}, blocked: true, request_id: null }); } catch {}
          return;
        } else {
          // Lenient: ask with modal and save fixed copy
          setErr(full.errors[0]); setWarnings(full.warnings);
          setStats({ items: full.stats.items, approxBytes: full.stats.approxBytes });
          pendingActionRef.current = () => {
            try {
              if (!dontSaveFixed && full.autofixApplied && full.fixed) {
                localStorage.setItem('censys_fixed_copy', JSON.stringify(full.fixed));
                localStorage.setItem('censys_fixed_meta', JSON.stringify({ saved_at: Date.now(), expires_at: Date.now() + 60 * 60 * 1000 }));
              }
            } catch {}
            try { void postTelemetry({ policy: 'lenient', errors_count: full.errors.length, warnings_count: warnCt, fixed_fields: full.telemetry || {}, blocked: false, request_id: null }); } catch {}
            const p2 = buildPayload(); if (p2 && !loading) onSubmit(p2);
          };
          setConfirmOpen(true);
          return;
        }
      }
      // Show warnings inline for visibility even if proceeding
      setWarnings(full.warnings);
      setStats({ items: full.stats.items, approxBytes: full.stats.approxBytes });
      if (warnCt) toast('info', `Proceeding with ${warnCt} warning(s)…`);
      try { void postTelemetry({ policy: policy as any, errors_count: 0, warnings_count: warnCt, fixed_fields: full.telemetry || {}, blocked: false, request_id: null }); } catch {}
    }

    const p = buildPayload();
    if (p && !loading) onSubmit(p);
  }
  const parsedCount = Array.isArray(parsed) ? parsed.length : (parsed?.hosts?.length || parsed?.records?.length || parsed?.raw_records?.length || (parsed ? 1 : 0));

  useEffect(() => {
    if (!settings.persistInput) return;
    try { localStorage.setItem('censys_last_input_raw', text); } catch {}
  }, [text, settings.persistInput]);

  function handleUseSample() {
    try {
      const pretty = JSON.stringify(sampleJson, null, 2);
      setText(pretty);
      setParsed(sampleJson as any);
      // Focus textarea for immediate UX feedback
      requestAnimationFrame(() => taRef.current?.focus());

      // Defer to next tick so state is committed before building payload
      setTimeout(() => {
        // Build payload deterministically from sampleJson (avoid racing parsed state)
        const src: any = sampleJson as any;
        const p: SummarizeRequest | null = Array.isArray(src)
          ? { hosts: src }
          : (src?.hosts || src?.records || src?.raw_records ? src : { hosts: [src] });
        // Always run summarize on sample to avoid blank UI confusion
        if (p && (settings.autoRunOnUseSample ?? true)) onSubmit(p);
      }, 0);
    } catch {
      // Silent fallback
    }
  }

  async function handleUseLatest() {
    try {
      setErr('');
      const res = await fetch('/datasets/latest.json', { cache: 'no-store' });
      if (!res.ok) {
        toast('error', `Latest dataset not found (${res.status}). Run the Publish task first.`);
        return;
      }
      const json = await res.json();
      const pretty = JSON.stringify(json, null, 2);
      setText(pretty);
      setParsed(json as any);
      toast('success', 'Loaded latest dataset');
      // Optional auto-run like Use Sample
      setTimeout(() => {
        const src: any = json as any;
        const p: SummarizeRequest | null = Array.isArray(src)
          ? { hosts: src }
          : (src?.hosts || src?.records || src?.raw_records ? src : { hosts: [src] });
        if (p && (settings.autoRunOnUseSample ?? true)) onSubmit(p);
      }, 0);
    } catch (e: any) {
      toast('error', `Failed to load latest dataset: ${e?.message || 'unknown error'}`);
    }
  }

  // Debounced auto-parse on typing so the "Parsed OK" pill stays in sync
  useEffect(() => {
    if (debounceRef.current) window.clearTimeout(debounceRef.current);
    debounceRef.current = window.setTimeout(() => {
      try {
        if (text?.trim()) {
          const r = validateSummarizeText(text);
          setWarnings(r.warnings);
          setStats({ items: r.stats.items, approxBytes: r.stats.approxBytes });
          if (r.valid) {
            setParsed(r.payload?.hosts || r.payload?.records || r.payload?.raw_records || r.payload);
            setErr('');
          } else {
            setParsed(null);
          }
        } else {
          setParsed(null);
          setWarnings([]);
          setStats(null);
        }
      } catch {}
    }, 250);
    return () => { if (debounceRef.current) window.clearTimeout(debounceRef.current); };
  }, [text]);

  // A11y/keyboard: press '/' to focus textarea when not in an input
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (document.activeElement as HTMLElement | null)?.tagName;
      if (e.key === '/' && tag !== 'INPUT' && tag !== 'TEXTAREA') {
        e.preventDefault();
        const el = document.getElementById('dataset-textarea') as HTMLTextAreaElement | null;
        el?.focus();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <div className="card">
      <ConfirmModal
        open={confirmOpen}
        title="Proceed with fixes?"
        body={
          <div className="text-sm">
            We found validation issues. We can coerce numbers/booleans, normalize severity (CRITICAL→HIGH), title-case countries,
            trim strings, and dedupe CVEs. A fixed copy will be saved for download/export.
          </div>
        }
        confirmText="Apply fixes & continue"
        cancelText="Review"
        onConfirm={() => { setConfirmOpen(false); pendingActionRef.current?.(); pendingActionRef.current = null; }}
        onCancel={() => { setConfirmOpen(false); }}
      />
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-medium">Upload / Paste Dataset</h2>
        <label className="btn cursor-pointer">
          <Upload size={16}/><span>Choose JSON</span>
          <input type="file" accept=".json,application/json,text/json,application/*+json" className="hidden" onChange={onFile} />
        </label>
      </div>

      <textarea
        id="dataset-textarea"
        ref={taRef}
        className="input w-full h-48 p-3"
        placeholder='Paste JSON here (e.g., { "hosts": [...] })'
        value={text}
        onChange={e => setText(e.target.value)}
        onKeyDown={(e) => {
          const isMeta = (e as any).metaKey || (e as any).ctrlKey;
          if (isMeta && e.key === 'Enter') {
            e.preventDefault();
            handleSummarizeClick();
          } else if (e.key === 'Escape') {
            (e.currentTarget as HTMLTextAreaElement).blur();
          }
        }}
      />

      {progress > 0 && progress < 100 && (
        <div className="mt-2 text-xs text-neutral-400">Reading file… {progress}%</div>
      )}

      {err && (
        <div className="mt-2 text-xs text-red-300 border border-red-500/30 bg-red-500/10 rounded-md px-2 py-1">
          {err}
        </div>
      )}
      {!err && warnings?.length > 0 && (
        <div className="mt-2 text-xs text-amber-300 border border-amber-500/30 bg-amber-500/10 rounded-md px-2 py-1">
          <div className="font-medium">Warnings:</div>
          <ul className="list-disc ml-4">
            {warnings.slice(0,3).map((w, i) => (<li key={i}>{w}</li>))}
          </ul>
        </div>
      )}
      {!err && stats && (
        <div className="mt-2 text-xs text-neutral-400">
          Size: ~{Math.round(stats.approxBytes/1024)} KB • Items: {stats.items}
        </div>
      )}

  <div className="mt-3 flex flex-wrap items-center gap-3">
        <button type="button" className="btn" onClick={parseText} disabled={loading}>Validate JSON</button>
        <button type="button" title={!payload ? 'Paste valid JSON first' : ''} className="btn btn-primary disabled:opacity-50" disabled={!ready} onClick={handleSummarizeClick}>
          <Play size={16}/> Summarize
        </button>
        <button type="button" className="btn" onClick={handleUseSample} disabled={loading}>Use Sample</button>
        <button type="button" className="btn" onClick={handleUseLatest} disabled={loading}>
          <Download size={16}/> Use Latest
        </button>
        {hasFixed && (
          <button type="button" className="btn" onClick={() => {
            try {
              const s = localStorage.getItem('censys_fixed_copy');
              if (!s) { setHasFixed(false); return; }
              const metaRaw = localStorage.getItem('censys_fixed_meta');
              if (metaRaw) {
                try { const meta = JSON.parse(metaRaw); if (meta.expires_at && Date.now() > Number(meta.expires_at)) { localStorage.removeItem('censys_fixed_copy'); localStorage.removeItem('censys_fixed_meta'); setHasFixed(false); return; } } catch {}
              }
              const blob = new Blob([s], { type: 'application/json' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url; a.download = 'fixed_dataset.json'; a.click();
              setTimeout(() => URL.revokeObjectURL(url), 1500);
            } catch {}
          }}>Download fixed JSON</button>
        )}
        {hasFixed && (
          <button type="button" className="btn" onClick={() => {
            try { localStorage.removeItem('censys_fixed_copy'); localStorage.removeItem('censys_fixed_meta'); setHasFixed(false); toast('info', 'Cleared fixed data'); } catch {}
          }}>Clear fixed data</button>
        )}
        {/* Runtime policy switch for demos */}
        <label className="text-xs flex items-center gap-2 ml-auto">
          Policy:
          <select
            defaultValue={POLICY}
            onChange={(e) => {
              (window as any)._VALIDATION_POLICY = e.target.value;
              try { localStorage.setItem('validation_policy', e.target.value); } catch {}
              toast('info', `Validation policy: ${e.target.value}`);
            }}
            className="input px-2 py-1 text-xs h-7"
          >
            <option value="lenient">lenient</option>
            <option value="strict">strict</option>
            <option value="off">off</option>
          </select>
          <span title={'Policy:\n• Lenient (default) — validates and autofixes common issues; warnings don’t block.\n• Strict — enforces the schema; errors (and selected warnings) block. Also enforced server-side.\n• Off — skips validation before submit (parse only).'}>
            <HelpCircle size={14} className="text-neutral-400" />
          </span>
        </label>
        <label className="text-xs flex items-center gap-2">
          <input type="checkbox" checked={dontSaveFixed} onChange={(e) => {
            const v = e.target.checked; setDontSaveFixed(v);
            try { localStorage.setItem('censys_fixed_nosave', v ? '1' : '0'); } catch {}
            if (v) { try { localStorage.removeItem('censys_fixed_copy'); localStorage.removeItem('censys_fixed_meta'); setHasFixed(false); } catch {} }
          }} />
          Don’t save fixed copy
        </label>
        {/* Helper banner */}
        <div className="text-xs text-gray-600 bg-gray-50 border border-gray-200 rounded px-2 py-1">
          <span className="font-medium">Policy:</span>
          <span className="ml-1">Lenient — validates and autofixes; warnings don’t block.</span>
          <span className="ml-2">Strict — enforces schema; blocking errors stop submit.</span>
          <span className="ml-2">Off — parses only; skips validation.</span>
        </div>
        <button type="button" className="btn" onClick={() => {
          try {
            const source = parsed ?? JSON.parse(text);
            const pretty = JSON.stringify(source, null, 2);
            setText(pretty);
            setErr('');
          } catch (e: any) {
            setErr(`Invalid JSON: ${e?.message || 'unknown parse error'}`);
          }
        }} disabled={!text}>Prettify</button>
        <button type="button" className="btn" onClick={() => { setText(''); setParsed(null); setErr(''); setProgress(0); }} disabled={!text}>Clear</button>
        {parsed && !err && (
          <span className="text-xs text-neutral-400" aria-live="polite">Parsed OK • items: {parsedCount} • keys: {Array.isArray(parsed) ? `Array[${parsed.length}]` : (Object.keys(parsed).slice(0,5).join(', ') + (Object.keys(parsed).length>5 ? '…' : ''))}</span>
        )}
      </div>
    </div>
  );
}