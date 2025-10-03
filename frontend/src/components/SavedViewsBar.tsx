import { useEffect, useState } from 'react';
import { listViews, saveView, saveAlert } from '../lib/api';
import type { Filter } from './FilterBar';

function toDSL(filters: Filter[]): string {
  const parts = filters.map((f) => {
    if (f.type === 'port') return `port:${f.value}`;
    if (f.type === 'country') return `country:${JSON.stringify(f.value)}`;
    if (f.type === 'severity') return `severity:${f.value}`;
    return '';
  }).filter(Boolean);
  return parts.join(' AND ');
}

export default function SavedViewsBar({ filters }: { filters: Filter[] }) {
  const [views, setViews] = useState<any[]>([]);
  const [name, setName] = useState('My View');
  const dsl = toDSL(filters);
  useEffect(() => { listViews().then((r: any) => setViews(r.views || [])).catch(()=>{}); }, []);
  return (
    <div className="flex items-center gap-2 mb-3">
      <input className="px-2 py-1 bg-[#0b0f14] border border-border rounded text-xs" value={name} onChange={e=>setName(e.target.value)} placeholder="View name" />
      <button className="btn btn-xs" disabled={!dsl} onClick={async()=>{ await saveView(name, dsl); const r:any = await listViews(); setViews(r.views||[]); }}>Save view</button>
      <button className="btn btn-xs" disabled={!dsl} onClick={async()=>{ await saveAlert(`${name} alert`, dsl); }}>Alert me</button>
      <span className="text-xs text-neutral-400">Views: {Array.isArray(views)? views.length:0}</span>
      {dsl ? (<span className="text-xs text-neutral-400">DSL: {dsl}</span>): null}
    </div>
  );
}
