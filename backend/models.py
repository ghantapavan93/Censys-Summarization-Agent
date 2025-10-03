from pydantic import BaseModel
from pydantic import ConfigDict
from typing import Optional, List, Dict, Any, Union

class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

class Record(_StrictModel):
    id: str
    ip: str
    port: int
    product: Optional[str] = None
    version: Optional[str] = None
    hardware: Optional[str] = None
    country: Optional[str] = None  # Prefer ISO-2
    cve: Optional[List[Dict[str, Any]]] = None  # [{"id": "CVE-2023-12345", "score": 7.5}]
    other: Optional[Dict[str, Any]] = None

class FieldMap(_StrictModel):
    ip: Optional[List[str]] = None
    port: Optional[List[str]] = None
    product: Optional[List[str]] = None
    version: Optional[List[str]] = None
    hardware: Optional[List[str]] = None
    country: Optional[List[str]] = None
    cve: Optional[List[str]] = None
    id: Optional[List[str]] = None

class SummarizeRequest(_StrictModel):
    records: Optional[List[Record]] = None
    raw_records: Optional[List[Dict[str, Any]]] = None
    field_map: Optional[FieldMap] = None
    nl: Optional[str] = None
    event_id: Optional[str] = None
    now_utc: Optional[str] = None

class QueryAssistantRequest(_StrictModel):
    records: Optional[List[Record]] = None
    raw_records: Optional[List[Dict[str, Any]]] = None
    field_map: Optional[FieldMap] = None
    nl: str
    event_id: Optional[str] = None
    now_utc: Optional[str] = None

class KeyFinding(_StrictModel):
    id: str
    title: str
    evidence_ids: List[str]

class RiskItem(_StrictModel):
    id: str
    affected_assets: int
    context: str
    severity: str
    likelihood: str
    impact: str

class VizSeries(_StrictModel):
    type: str
    title: str
    data: List[List[Union[str, int]]]

class VizPayload(_StrictModel):
    charts: List[VizSeries]
    # Optional convenience maps for testing/UI
    histograms: Optional[Dict[str, Dict[str, int]]] = None
    top_ports: Optional[Dict[str, int]] = None

class RiskMatrix(_StrictModel):
    high: int = 0
    medium: int = 0
    low: int = 0

class CensAIResponse(_StrictModel):
    summary: str
    overview_deterministic: Optional[str] = None
    overview_llm: Optional[str] = None
    use_llm_available: Optional[bool] = None
    key_findings: List[KeyFinding]
    risks: List[RiskItem]
    risk_matrix: RiskMatrix
    query_trace: Dict[str, Any]
    viz_payload: VizPayload
    next_actions: List[str]
    meta: Dict[str, Any]

class ExplainResponse(_StrictModel):
    finding_id: str
    evidence: List[Dict[str, Any]]
    scoring: Dict[str, Any]

class ConfigResponse(_StrictModel):
    model_backend: str
    model_name: str
    retrieval_k: int
    language: str
    enable_validation: bool
