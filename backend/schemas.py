from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal

class CertRef(BaseModel):
    fingerprint_sha256: Optional[str] = None

class Software(BaseModel):
    product: Optional[str] = None
    vendor: Optional[str] = None
    version: Optional[str] = None

class Service(BaseModel):
    port: Optional[int] = None
    protocol: Optional[str] = None
    banner: Optional[str] = None
    cert: Optional[CertRef] = None
    software: Optional[List[Software]] = None
    labels: Optional[List[str]] = None

class ASN(BaseModel):
    asn: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    country_code: Optional[str] = None

class Location(BaseModel):
    country: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None

class Host(BaseModel):
    ip: str
    location: Optional[Location] = None
    autonomous_system: Optional[ASN] = None
    services: Optional[List[Service]] = Field(default_factory=list)

class DatasetInsights(BaseModel):
    top_ports: List[Dict[str, int]]
    top_protocols: List[Dict[str, int]]
    top_software: List[Dict[str, int]]
    top_asns: List[Dict[str, int]]
    countries: List[Dict[str, int]]

class HostSummary(BaseModel):
    ip: str
    summary: str
    severity_hint: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO", "UNKNOWN"] = "UNKNOWN"

# Backward-compat alias for modules that import `Summary`
Summary = HostSummary

class SummaryResponse(BaseModel):
    count: int
    summaries: List[Dict[str, Any]]
    insights: DatasetInsights
