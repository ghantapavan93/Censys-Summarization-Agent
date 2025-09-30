export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export interface RiskItem {
	title: string;
	severity: Severity;
	evidence: string[];
	related_cves: string[];
	why_it_matters: string;
	recommended_fix: string;
}

export interface VizPoint { key: string; count: number }
export interface VizSeries { id: string; label: string; data: VizPoint[] }

export interface VizPayload {
	charts?: {
		top_ports?: VizSeries;
		top_protocols?: VizSeries;
		top_software?: VizSeries;
		countries?: VizSeries;
	};
	histograms?: Record<string, VizSeries>;
}

export interface CensAIResponse {
	summary: string;
	overview_deterministic?: string;
	overview_llm?: string;
	use_llm_available: boolean;
	key_findings: string[];
	risks: RiskItem[];
	risk_matrix?: Record<string, number>;
	viz_payload?: VizPayload;
	next_actions?: string[];
	meta?: { timings_ms?: Record<string, number>; valid_json?: boolean };
	query_trace?: any;
}

export interface SummarizeRequest {
	hosts?: any[];
	records?: any[];
	raw_records?: any[];
	field_map?: any;
}

