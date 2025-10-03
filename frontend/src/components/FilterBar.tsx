
export type Filter = { type: 'severity'|'country'|'port'; value: string };

export default function FilterBar({ filters, onRemove, onClear }: { filters: Filter[]; onRemove: (idx: number) => void; onClear: () => void; }) {
  if (!filters.length) return null;
  return (
    <div className="flex items-center gap-2 mb-3">
      {filters.map((f, i) => (
        <span key={i} className="inline-flex items-center gap-1 border border-border rounded-full px-2 py-0.5 text-xs bg-[#0b0f14]">
          {f.type}: {f.value}
          <button className="text-neutral-400" onClick={() => onRemove(i)}>×</button>
        </span>
      ))}
      <button className="btn btn-xs" onClick={onClear}>Clear filters</button>
    </div>
  );
}
