from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

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
    # Require non-empty IP string
    ip: str = Field(..., min_length=1)
    location: Optional[Location] = None
    autonomous_system: Optional[ASN] = None
    services: Optional[List[Service]] = Field(default_factory=list)

class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"
    UNKNOWN = "UNKNOWN"

class HostSummary(BaseModel):
    ip: str
    summary: str
    # Constrain to a fixed set of values; default to UNKNOWN when not provided
    severity_hint: Severity = Severity.UNKNOWN

class DatasetInsights(BaseModel):
    # Each list item is a single-key dictionary mapping label -> count
    top_ports: List[Dict[str, int]]
    top_protocols: List[Dict[str, int]]
    top_software: List[Dict[str, int]]
    top_asns: List[Dict[str, int]]
    countries: List[Dict[str, int]]

class SummaryResponse(BaseModel):
    count: int
    summaries: List[Dict[str, Any]]
    insights: DatasetInsights
