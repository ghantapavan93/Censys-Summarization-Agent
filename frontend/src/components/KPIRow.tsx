type Totals = { hosts?: number; unique_ips?: number; countries?: number; unique_ports?: number };

export default function KPIRow({ totals, topPort, flags }: { totals?: Totals; topPort?: number | null | undefined; flags?: { kev_total?: number; cvss_high_total?: number; honeypot_like?: number } }) {
  const items = [
    { label: 'Hosts', value: totals?.hosts ?? '—' },
    { label: 'Unique IPs', value: totals?.unique_ips ?? '—' },
    { label: 'Countries', value: totals?.countries ?? '—' },
    { label: 'Unique ports', value: totals?.unique_ports ?? '—' },
    { label: 'Top port', value: topPort ?? '—' },
    { label: 'KEV matches', value: flags?.kev_total ?? 0, isBadge: true },
    { label: 'CVSS≥7', value: flags?.cvss_high_total ?? 0, isBadge: true },
    { label: 'Honeypot-like', value: flags?.honeypot_like ?? 0, isBadge: true },
  ];
  return (
    <div className="card">
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
        {items.map((it, idx) => (
          <div key={idx} className="rounded-lg border p-3 text-center">
            <div className="text-[11px] text-neutral-500">{it.label}</div>
            <div className="text-lg font-semibold flex items-center justify-center">
              {it.isBadge ? (
                <span className={`badge ${Number(it.value) === 0 ? 'badge-ok' : ''}`}>{String(it.value)}</span>
              ) : (
                <span>{String(it.value)}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
