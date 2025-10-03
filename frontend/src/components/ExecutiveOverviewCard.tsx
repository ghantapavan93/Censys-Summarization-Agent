import { useMemo, useState } from 'react';

type Props = {
  text?: string;
  deterministic?: string;
  meta?: { used_ai?: boolean; guard_pass?: boolean; guard_reason?: string | null; model?: string; latency_ms?: number; generated_at?: number } | null;
  onRegenerate?: () => void;
};

export default function ExecutiveOverviewCard({ text, deterministic, meta, onRegenerate }: Props) {
  const [compare, setCompare] = useState(false);
  const aiText = (text || '').trim();
  const detText = (deterministic || '').trim();
  const showAI = !!aiText;
  const guardPass = !!meta?.guard_pass;
  const model = meta?.model || '—';
  const when = useMemo(() => {
    try { return meta?.generated_at ? new Date(meta.generated_at).toLocaleString() : '—'; } catch { return '—'; }
  }, [meta?.generated_at]);
  const lockedBadge = guardPass ? (
    <span className="inline-flex items-center gap-1 text-[11px] text-green-700 bg-green-50 border border-green-200 px-2 py-0.5 rounded">facts locked ✓</span>
  ) : (
    <span className="inline-flex items-center gap-1 text-[11px] text-amber-800 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded">facts locked ✕</span>
  );

  const body = compare ? detText : aiText || detText;

  return (
    <div className="rounded-xl border p-4 bg-white">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-lg font-semibold">Executive Overview (AI)</h3>
        <div className="flex items-center gap-2 text-[11px] text-neutral-600">
          <span>Generated at {when}</span>
          <span>•</span>
          <span>{model}</span>
          <span>•</span>
          {lockedBadge}
        </div>
      </div>

      {!guardPass && (
        <div className="mb-3 text-[13px] bg-amber-50 text-amber-900 border border-amber-200 rounded px-3 py-2">
          AI rewrite didn’t pass factual lock; showing validated summary instead.
          {meta?.guard_reason ? <span className="ml-1 opacity-80">({meta.guard_reason})</span> : null}
        </div>
      )}

      <p className="text-sm whitespace-pre-wrap text-neutral-900">
        {body || '—'}
      </p>

      <div className="mt-3 flex flex-wrap gap-2 text-sm">
        <button
          className="px-3 py-1.5 rounded bg-black text-white disabled:opacity-50"
          onClick={onRegenerate}
          disabled={!onRegenerate}
          title="Run AI rewrite again"
        >
          {showAI ? 'Regenerate' : 'Rewrite'}
        </button>
        <button
          className="px-3 py-1.5 rounded border"
          onClick={() => navigator.clipboard.writeText(body)}
        >
          Copy
        </button>
        <button
          className="px-3 py-1.5 rounded border"
          onClick={() => setCompare(v => !v)}
          disabled={!aiText}
        >
          {compare ? 'Show AI' : 'Compare vs deterministic'}
        </button>
      </div>
    </div>
  );
}
