import type { VizPayload, VizSeries } from '../lib/types';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

function SeriesCard({ title, series }: { title: string; series?: VizSeries }) {
	if (!series || !series.data?.length) return null;
	const data = series.data.slice(0, 10).map(d => ({ name: d.key, count: d.count }));
	return (
		<div className="card">
			<div className="mb-2 font-medium">{title}</div>
			<div className="h-60">
				<ResponsiveContainer width="100%" height="100%">
					<BarChart data={data}>
						<XAxis dataKey="name" interval={0} tick={{ fill: '#a3a3a3', fontSize: 12 }} angle={-20} textAnchor="end" height={60} />
						<YAxis tick={{ fill: '#a3a3a3', fontSize: 12 }} />
						<Tooltip contentStyle={{ background: '#111', border: '1px solid #333', color: '#ddd' }} />
						<Bar dataKey="count" />
					</BarChart>
				</ResponsiveContainer>
			</div>
		</div>
	);
}

export default function ChartsPanel({ viz }: { viz?: VizPayload }) {
	if (!viz || !viz.charts) return null;
	const { top_ports, top_protocols, top_software, countries } = viz.charts;
	return (
		<div className="grid md:grid-cols-2 gap-4">
			<SeriesCard title="Top Ports" series={top_ports} />
			<SeriesCard title="Top Protocols" series={top_protocols} />
			<SeriesCard title="Top Software" series={top_software} />
			<SeriesCard title="Countries" series={countries} />
		</div>
	);
}

