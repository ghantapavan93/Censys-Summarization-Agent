export function Callouts({ kev, cvss }: { kev?: number; cvss?: number }) {
  const kevZero = (kev ?? 0) === 0;
  const cvssZero = (cvss ?? 0) === 0;
  return (
    <div className="grid sm:grid-cols-2 gap-3">
      {/* KEV callout */}
      <div className={`rounded-xl border p-4 ${kevZero ? 'border-emerald-400/60 bg-emerald-50' : 'border-red-400/70 bg-red-50'}`}>
        <div className="flex items-center justify-between">
          <div className="text-[13px] font-semibold text-neutral-700">KEV (Known Exploited Vulnerabilities)</div>
          <span className={`px-2 py-0.5 rounded-full text-xs ${kevZero ? 'bg-emerald-200 text-emerald-900' : 'bg-red-200 text-red-900'}`}>{kevZero ? 'OK' : 'Action'}</span>
        </div>
        <div className={`mt-1 text-sm ${kevZero ? 'text-emerald-800' : 'text-red-800'} font-medium`}>
          {kevZero ? 'None detected' : <>Patch now <span className="font-bold">({kev})</span></>}
        </div>
      </div>

      {/* CVSS callout */}
      <div className={`rounded-xl border p-4 ${cvssZero ? 'border-emerald-400/60 bg-emerald-50' : 'border-amber-400/70 bg-amber-50'}`}>
        <div className="flex items-center justify-between">
          <div className="text-[13px] font-semibold text-neutral-700">CVSS≥7</div>
          <span className={`px-2 py-0.5 rounded-full text-xs ${cvssZero ? 'bg-emerald-200 text-emerald-900' : 'bg-amber-200 text-amber-900'}`}>{cvssZero ? 'OK' : 'Review'}</span>
        </div>
        <div className={`mt-1 text-sm ${cvssZero ? 'text-emerald-800' : 'text-amber-900'} font-medium`}>
          {cvssZero ? 'None detected' : <>Prioritize remediation <span className="font-bold">({cvss})</span></>}
        </div>
      </div>
    </div>
  );
}

export function ClustersTable({ rows }: { rows?: Array<{ product: string; version: string; country: string; count: number; ports: number[] }> }) {
  const top = (rows || []).slice(0, 5);
  if (top.length === 0) return null;
  return (
    <div className="card">
      <div className="mb-2 font-medium">Clusters (top 5)</div>
      <div className="overflow-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-neutral-500">
              <th className="py-1">Product</th>
              <th className="py-1">Version</th>
              <th className="py-1">Country</th>
              <th className="py-1">Hosts</th>
              <th className="py-1">Ports</th>
            </tr>
          </thead>
          <tbody>
            {top.map((r, i) => (
              <tr key={i} className="border-t">
                <td className="py-1">{r.product}</td>
                <td className="py-1">{r.version}</td>
                <td className="py-1">{r.country}</td>
                <td className="py-1">{r.count}</td>
                <td className="py-1">{r.ports?.join(', ')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
