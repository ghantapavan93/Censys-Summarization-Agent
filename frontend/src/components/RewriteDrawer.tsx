import { X, Copy, Repeat2 } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';

function wordDiff(a: string, b: string) {
  const A = new Set(a.split(/\s+/));
  return b.split(/(\s+)/).map((w, i) =>
    A.has(w) || w.trim()==='' ? <span key={i}>{w}</span> : <mark key={i} className="bg-accent/30 px-0.5 rounded">{w}</mark>
  );
}

type Meta = { used_ai?: boolean; guard_pass?: boolean; guard_reason?: string | null; model?: string; latency_ms?: number; generated_at?: number };

export default function RewriteDrawer({ open, onClose, original, rewritten, meta, onRegenerate, raw }: { open: boolean; onClose: () => void; original: string; rewritten?: string; meta?: Meta; onRegenerate?: (opts?: { style?: string; language?: string }) => void; raw?: string }) {
  if (!open) return null;
  const canCopy = !!rewritten;
  const guardPass = !!meta?.guard_pass;
  const rightText = guardPass ? (rewritten || '') : (raw || '');
  const diff = useMemo(() => (rightText ? wordDiff(original, rightText) : null), [original, rightText]);
  const [showDiff, setShowDiff] = useState(true);
  const [style, setStyle] = useState<string>('executive');
  const [language, setLanguage] = useState<string>('en');
  const model = meta?.model || '—';
  const when = useMemo(() => { try { return meta?.generated_at ? new Date(meta.generated_at).toLocaleString() : '—'; } catch { return '—'; } }, [meta?.generated_at]);
  // Auto-regenerate on style/language change if a rewrite already exists
  const debRef = useRef<number | null>(null);
  useEffect(() => {
    if (!onRegenerate || !rewritten) return;
    if (debRef.current) window.clearTimeout(debRef.current);
    debRef.current = window.setTimeout(() => {
      onRegenerate({ style, language });
    }, 250);
    return () => { if (debRef.current) window.clearTimeout(debRef.current); };
  }, [style, language]);

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="absolute right-0 top-0 h-full w-full md:w-[720px] bg-canvas border-l border-border p-5 overflow-y-auto">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-semibold">Rewrite with AI</h3>
            <span className="text-[11px] text-neutral-500">Generated at {when} • {model} • {guardPass ? <span className="text-green-700">facts locked ✓</span> : <span className="text-amber-700">facts locked ✕</span>}</span>
          </div>
          <button className="btn" onClick={onClose}><X size={16}/> Close</button>
        </div>

        {!guardPass && (
          <div className="mb-3 text-[13px] bg-amber-50 text-amber-900 border border-amber-200 rounded px-3 py-2">
            AI rewrite didn’t pass factual lock; showing validated summary instead.
            {meta?.guard_reason ? <span className="ml-1 opacity-80">({meta.guard_reason})</span> : null}
          </div>
        )}

        <div className="mb-3 flex items-center gap-2 flex-wrap">
          <label className="text-xs text-neutral-500">Style</label>
          <select className="border rounded px-2 py-1 text-sm" value={style} onChange={e => setStyle(e.target.value)}>
            <option value="executive">executive</option>
            <option value="bulleted">bulleted</option>
            <option value="ticket">ticket</option>
          </select>
          <label className="text-xs text-neutral-500 ml-2">Language</label>
          <select className="border rounded px-2 py-1 text-sm" value={language} onChange={e => setLanguage(e.target.value)}>
            <option value="en">en</option>
          </select>
          <span className="flex-1" />
          <button className="btn btn-primary" disabled={!onRegenerate} onClick={() => onRegenerate && onRegenerate({ style, language })}><Repeat2 size={16}/> {rewritten ? 'Regenerate' : 'Rewrite'}</button>
          <button className="btn" disabled={!canCopy} onClick={() => navigator.clipboard.writeText((showDiff ? rightText : rightText))}><Copy size={16}/> Copy</button>
          <button className="btn" disabled={!rewritten} onClick={() => setShowDiff(v => !v)}>{showDiff ? 'Show AI only' : 'Compare vs deterministic'}</button>
        </div>

        {/* Optional pills: Delta and SLA guidance (shown if meta indicates fields exist) */}
        <div className="mb-3 flex items-center gap-2 text-xs">
          {((meta as any)?.delta_counts) ? (
            <span className="inline-flex items-center rounded-full bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5">
              Delta: New {((meta as any).delta_counts.new ?? 0)} • Resolved {((meta as any).delta_counts.resolved ?? 0)} • Changed {((meta as any).delta_counts.changed ?? 0)}
            </span>
          ) : null}
          <span className="inline-flex items-center rounded-full bg-amber-50 text-amber-700 border border-amber-200 px-2 py-0.5">
            SLA: KEV ≤ 72h • CVSS≥7 ≤ 14d
          </span>
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          <div className="card">
            <div className="text-sm text-neutral-400 mb-2">Original (deterministic)</div>
            <pre className="whitespace-pre-wrap text-neutral-200">{original}</pre>
          </div>
          <div className="card">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-neutral-400">AI Rewrite</span>
            </div>
            {rightText ? (
              showDiff ? (
                <pre className="whitespace-pre-wrap text-neutral-200">{diff}</pre>
              ) : (
                <pre className="whitespace-pre-wrap text-neutral-200">{rightText}</pre>
              )
            ) : (
              <div className="text-neutral-400">No rewrite yet. Click “Rewrite” above.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
