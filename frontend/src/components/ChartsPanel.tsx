import type { VizPayload, VizSeries } from '../lib/types';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';

function SeriesCard({ title, series, onClick }: { title: string; series?: VizSeries; onClick?: (label: string) => void }) {
  if (!series || !series.data?.length) return null;
  // Sort by count desc for clearer ranking and limit to top 10
  const data = [...series.data]
    .sort((a, b) => (b.count || 0) - (a.count || 0))
    .slice(0, 10)
    .map(d => ({ name: d.key, count: d.count }));
  return (
    <div className="card">
      <div className="mb-2 font-medium">{title}</div>
      <div className="h-60">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <XAxis dataKey="name" interval={0} tick={{ fill: '#a3a3a3', fontSize: 11 }} angle={-30} textAnchor="end" height={70} />
            <YAxis tick={{ fill: '#a3a3a3', fontSize: 12 }} allowDecimals={false} />
            <Tooltip
              contentStyle={{ background: '#0b0f14', border: '1px solid #2b2f36', color: '#ddd' }}
              labelStyle={{ color: '#ddd' }}
              formatter={(value: any) => [value, 'Count']}
            />
            <Bar dataKey="count" fill="#22d3ee" onClick={(d: any) => onClick?.(d.name)} cursor={onClick ? 'pointer' : 'default'} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default function ChartsPanel({ viz, severity, topPorts, countries: countryAgg, onFilter }: { viz?: VizPayload; severity?: { HIGH: number; MEDIUM: number; LOW: number }; topPorts?: Array<{ port: number; count: number }>; countries?: Array<{ country: string; count: number }>; onFilter?: (f: { type: 'severity'|'country'|'port'; value: string }) => void; }) {
  const charts = viz?.charts || {} as any;
  const portsSeries: VizSeries | undefined = charts.top_ports || (topPorts ? {
    id: 'top_ports',
    label: 'Top Ports',
    data: topPorts.map(p => ({ key: `Port ${String(p.port)}`, count: p.count }))
  } : undefined);
  const countriesSeries: VizSeries | undefined = charts.countries || (countryAgg ? { id: 'countries', label: 'Countries', data: countryAgg.map(c => ({ key: c.country, count: c.count })) } : undefined);

  const SEV_COLORS: Record<string, string> = { HIGH: '#ef4444', MEDIUM: '#f59e0b', LOW: '#22c55e' };
  const sevData = severity ? [
    { name: 'HIGH', value: severity.HIGH },
    { name: 'MEDIUM', value: severity.MEDIUM },
    { name: 'LOW', value: severity.LOW },
  ] : [];

  return (
    <div className="grid md:grid-cols-3 gap-4">
      {/* Severity donut */}
      {severity && (
        <div className="card">
          <div className="mb-2 font-medium">Severity</div>
          <div className="h-60">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={sevData} dataKey="value" nameKey="name" innerRadius={40} outerRadius={60} onClick={(p: any) => onFilter?.({ type: 'severity', value: p?.name })} cursor={onFilter ? 'pointer' : 'default'}>
                  {sevData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={SEV_COLORS[entry.name] || '#94a3b8'} />
                  ))}
                </Pie>
                <Legend verticalAlign="bottom" height={24} />
                <Tooltip contentStyle={{ background: '#0b0f14', border: '1px solid #2b2f36', color: '#ddd' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Top Ports */}
      <SeriesCard title="Top Ports" series={portsSeries} onClick={(label) => {
        const m = label.match(/\b(\d+)$/); if (m) onFilter?.({ type: 'port', value: m[1] });
      }} />
      {/* Countries */}
      <SeriesCard title="Assets by Country" series={countriesSeries} onClick={(label) => onFilter?.({ type: 'country', value: label })} />
    </div>
  );
}
