import { useEffect, useState } from 'react';
import { getTrends } from '../lib/api';

type Point = [number, number];

function Spark({ data, color }: { data: Point[]; color: string }) {
  if (!data?.length) return <div className="h-8"/>;
  const w = 120, h = 24, pad = 2;
  const xs = data.map(d => d[0]);
  const ys = data.map(d => d[1]);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const sx = (x: number) => pad + (w - 2*pad) * ((x - minX) / Math.max(1, maxX - minX));
  const sy = (y: number) => (h - pad) - (h - 2*pad) * ((y - minY) / Math.max(1, maxY - minY));
  const d = data.map((p, i) => `${i===0 ? 'M' : 'L'} ${sx(p[0])} ${sy(p[1])}`).join(' ');
  return (
    <svg width={w} height={h}>
      <path d={d} fill="none" stroke={color} strokeWidth={1.5} />
    </svg>
  );
}

export default function TrendsRow() {
  const [tr, setTr] = useState<any>(null);
  useEffect(() => { getTrends().then(setTr).catch(()=>{}); }, []);
  const s = (arr?: Point[]) => Array.isArray(arr) ? arr : [];
  return (
    <div className="grid md:grid-cols-3 gap-4">
      <div className="card"><div className="text-xs text-neutral-400 mb-1">Open ports (30d)</div><Spark data={s(tr?.open_ports?.["30"])} color="#22d3ee"/></div>
      <div className="card"><div className="text-xs text-neutral-400 mb-1">Medium+ risks (30d)</div><Spark data={s(tr?.medium_plus?.["30"])} color="#f59e0b"/></div>
      <div className="card"><div className="text-xs text-neutral-400 mb-1">KEV count (30d)</div><Spark data={s(tr?.kev?.["30"])} color="#ef4444"/></div>
    </div>
  );
}
