export function RiskChip({ score = 0 }: { score?: number }) {
  const tone = score >= 70
    ? "bg-red-100 text-red-700 border-red-300"
    : score >= 30
    ? "bg-amber-100 text-amber-700 border-amber-300"
    : "bg-slate-100 text-slate-700 border-slate-300";
  return (
    <span className={`border px-2 py-0.5 rounded-full text-xs ${tone}`}>Risk {score}</span>
  );
}

export function KevBadge({ show }: { show: boolean }) {
  if (!show) return null;
  return (
    <span className="ml-2 inline-flex items-center gap-1 rounded-full bg-red-600 text-white px-2 py-0.5 text-xs">
      KEV
    </span>
  );
}
