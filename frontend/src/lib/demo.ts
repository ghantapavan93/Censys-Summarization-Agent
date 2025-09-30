import type { CensAIResponse, SummarizeRequest, VizSeries } from './types';

const ports: VizSeries = {
	id: 'ports',
	label: 'Top Ports',
	data: [
		{ key: '443', count: 182 },
		{ key: '80', count: 171 },
		{ key: '22', count: 96 },
		{ key: '25', count: 24 },
		{ key: '3389', count: 12 },
	],
};

const protocols: VizSeries = {
	id: 'protocols',
	label: 'Top Protocols',
	data: [
		{ key: 'HTTP', count: 175 },
		{ key: 'TLS', count: 160 },
		{ key: 'SSH', count: 96 },
		{ key: 'SMTP', count: 24 },
	],
};

const software: VizSeries = {
	id: 'software',
	label: 'Top Software',
	data: [
		{ key: 'nginx', count: 104 },
		{ key: 'OpenSSH', count: 96 },
		{ key: 'Apache httpd', count: 46 },
		{ key: 'Microsoft IIS', count: 18 },
	],
};

const countries: VizSeries = {
	id: 'countries',
	label: 'Countries',
	data: [
		{ key: 'US', count: 210 },
		{ key: 'DE', count: 40 },
		{ key: 'NL', count: 28 },
		{ key: 'GB', count: 20 },
	],
};

export function getDemoData(): { raw: SummarizeRequest; resp: CensAIResponse } {
	const raw: SummarizeRequest = {
		hosts: [{ ip: '203.0.113.10' }, { ip: '198.51.100.22' }],
	};

	const resp: CensAIResponse = {
		summary:
			"Environment exposes common web and SSH services across multiple regions. Several services present version drift and default configurations that increase attack surface.",
		overview_deterministic:
			"The dataset consists primarily of HTTPS (443/tcp) and HTTP (80/tcp) endpoints, with SSH (22/tcp) widely deployed. Software indicates a mix of nginx and Apache, with OpenSSH variants. Exposure is global but concentrated in US and DE. Risks stem from outdated TLS, banner leakage, and open admin panels.",
		overview_llm:
			"Most assets are classic web stacks (nginx/Apache) with SSH management exposed. A handful show outdated TLS and default banners. Focus on hardening TLS, closing public admin paths, and consolidating versions to reduce risk.",
		use_llm_available: true,
		key_findings: [
			"High concentration of 443/80 with mixed TLS configurations",
			"SSH is broadly exposed on 22/tcp",
			"Visible server banners reveal software and versions",
		],
		risks: [
			{
				title: 'Public Admin Interfaces Exposed',
				severity: 'HIGH',
				related_cves: [],
				evidence: ['/admin on 203.0.113.10', 'wp-admin on 198.51.100.22'],
				why_it_matters: 'Increases risk of brute force and exploitation of known admin weaknesses.',
				recommended_fix: 'Restrict by IP/VPN; enable MFA; move behind SSO proxy.',
			},
			{
				title: 'Outdated TLS Configurations',
				severity: 'MEDIUM',
				related_cves: [],
				evidence: ['TLS1.0 enabled on 203.0.113.10:443', 'Weak ciphers observed'],
				why_it_matters: 'Weak TLS allows downgrade or disclosure of sensitive data under certain conditions.',
				recommended_fix: 'Disable legacy TLS; adopt modern cipher suites; enforce HSTS.',
			},
			{
				title: 'Banner Disclosure',
				severity: 'LOW',
				related_cves: [],
				evidence: ['Server: nginx/1.18.0', 'OpenSSH_7.4'],
				why_it_matters: 'Reveals fingerprinting details that aid targeted exploitation.',
				recommended_fix: 'Hide version banners; apply header hardening.',
			},
		],
		risk_matrix: { CRITICAL: 0, HIGH: 1, MEDIUM: 1, LOW: 1 },
		viz_payload: { charts: { top_ports: ports, top_protocols: protocols, top_software: software, countries } },
		next_actions: [
			"Enforce modern TLS and remove legacy protocols",
			"Restrict admin interfaces by IP/VPN; enable MFA",
			"Standardize server versions and hide banners",
		],
		meta: { valid_json: true, timings_ms: { total: 120 } },
		query_trace: { query: 'services.service_name: (HTTP OR TLS) AND location.country_code: (US OR DE)' },
	};

	return { raw, resp };
}

