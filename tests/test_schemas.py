import pytest
from pydantic import ValidationError
from backend.schemas import (
    Host, Service, ASN, Location, CertRef, Software,
    HostSummary, DatasetInsights, SummaryResponse
)


class TestHost:
    def test_host_valid_minimal(self):
        """Test Host creation with minimal required data"""
        host = Host(ip="192.168.1.1")
        assert host.ip == "192.168.1.1"
        assert host.services == []
        assert host.location is None
        assert host.autonomous_system is None

    def test_host_valid_full(self):
        """Test Host creation with full data"""
        location = Location(country="US", city="New York", province="NY")
        asn = ASN(asn=12345, name="TEST-AS", description="Test ASN", country_code="US")
        
        software = Software(product="nginx", vendor="F5", version="1.18.0")
        cert = CertRef(fingerprint_sha256="abc123")
        service = Service(
            port=443, 
            protocol="tcp", 
            banner="nginx/1.18.0",
            cert=cert,
            software=[software],
            labels=["https", "web"]
        )
        
        host = Host(
            ip="192.168.1.1",
            location=location,
            autonomous_system=asn,
            services=[service]
        )
        
        assert host.ip == "192.168.1.1"
        assert host.location.country == "US"
        assert host.autonomous_system.asn == 12345
        assert len(host.services) == 1
        assert host.services[0].port == 443

    def test_host_invalid_ip_missing(self):
        """Test Host creation fails without IP"""
        with pytest.raises(ValidationError):
            Host()

    def test_host_invalid_ip_empty(self):
        """Test Host creation fails with empty IP"""
        with pytest.raises(ValidationError):
            Host(ip="")


class TestService:
    def test_service_minimal(self):
        """Test Service creation with no data"""
        service = Service()
        assert service.port is None
        assert service.protocol is None
        assert service.banner is None
        assert service.cert is None
        assert service.software is None
        assert service.labels is None

    def test_service_full(self):
        """Test Service creation with full data"""
        software = Software(product="Apache", vendor="ASF", version="2.4.41")
        cert = CertRef(fingerprint_sha256="def456")
        
        service = Service(
            port=80,
            protocol="tcp",
            banner="Apache/2.4.41",
            cert=cert,
            software=[software],
            labels=["http", "web"]
        )
        
        assert service.port == 80
        assert service.protocol == "tcp"
        assert service.banner == "Apache/2.4.41"
        assert service.cert.fingerprint_sha256 == "def456"
        assert len(service.software) == 1
        assert service.software[0].product == "Apache"
        assert service.labels == ["http", "web"]


class TestSoftware:
    def test_software_minimal(self):
        """Test Software creation with no data"""
        software = Software()
        assert software.product is None
        assert software.vendor is None
        assert software.version is None

    def test_software_full(self):
        """Test Software creation with full data"""
        software = Software(product="MySQL", vendor="Oracle", version="8.0.25")
        assert software.product == "MySQL"
        assert software.vendor == "Oracle"
        assert software.version == "8.0.25"


class TestASN:
    def test_asn_minimal(self):
        """Test ASN creation with no data"""
        asn = ASN()
        assert asn.asn is None
        assert asn.name is None
        assert asn.description is None
        assert asn.country_code is None

    def test_asn_full(self):
        """Test ASN creation with full data"""
        asn = ASN(asn=15169, name="GOOGLE", description="Google LLC", country_code="US")
        assert asn.asn == 15169
        assert asn.name == "GOOGLE"
        assert asn.description == "Google LLC"
        assert asn.country_code == "US"


class TestLocation:
    def test_location_minimal(self):
        """Test Location creation with no data"""
        location = Location()
        assert location.country is None
        assert location.city is None
        assert location.province is None

    def test_location_full(self):
        """Test Location creation with full data"""
        location = Location(country="Canada", city="Toronto", province="Ontario")
        assert location.country == "Canada"
        assert location.city == "Toronto"
        assert location.province == "Ontario"


class TestHostSummary:
    def test_summary_minimal(self):
        """Test HostSummary creation with minimal data"""
        summary = HostSummary(ip="192.168.1.1", summary="Test summary")
        assert summary.ip == "192.168.1.1"
        assert summary.summary == "Test summary"
        assert summary.severity_hint == "UNKNOWN"

    def test_summary_with_severity(self):
        """Test HostSummary creation with severity"""
        summary = HostSummary(
            ip="192.168.1.1", 
            summary="Critical vulnerability", 
            severity_hint="CRITICAL"
        )
        assert summary.ip == "192.168.1.1"
        assert summary.summary == "Critical vulnerability"
        assert summary.severity_hint == "CRITICAL"

    def test_summary_invalid_severity(self):
        """Test HostSummary creation fails with invalid severity"""
        with pytest.raises(ValidationError):
            HostSummary(
                ip="192.168.1.1", 
                summary="Test", 
                severity_hint="INVALID"
            )


class TestDatasetInsights:
    def test_insights_creation(self):
        """Test DatasetInsights creation"""
        insights = DatasetInsights(
            top_ports=[{"80": 10}, {"443": 5}],
            top_protocols=[{"tcp": 15}],
            top_software=[{"nginx": 8}],
            top_asns=[{"GOOGLE": 3}],
            countries=[{"US": 12}]
        )
        
        assert len(insights.top_ports) == 2
        assert insights.top_ports[0]["80"] == 10
        assert insights.top_protocols[0]["tcp"] == 15
        assert insights.countries[0]["US"] == 12


class TestSummaryResponse:
    def test_summary_response_creation(self):
        """Test SummaryResponse creation"""
        summary = HostSummary(ip="192.168.1.1", summary="Test")
        insights = DatasetInsights(
            top_ports=[{"80": 1}],
            top_protocols=[{"tcp": 1}],
            top_software=[{"nginx": 1}],
            top_asns=[{"GOOGLE": 1}],
            countries=[{"US": 1}]
        )
        
        response = SummaryResponse(
            count=1,
            summaries=[summary.dict()],
            insights=insights
        )
        
        assert response.count == 1
        assert len(response.summaries) == 1
        assert response.insights.top_ports[0]["80"] == 1