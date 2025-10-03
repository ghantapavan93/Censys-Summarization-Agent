import pytest
from backend.summarizer_rule import RuleSummarizer
from backend.schemas import Host, Service, Software, ASN, Location


class TestRuleSummarizer:
    def setup_method(self):
        """Setup for each test method"""
        self.summarizer = RuleSummarizer()

    def test_empty_host_list(self):
        """Test summarizing empty host list"""
        result = self.summarizer.summarize([])
        
        assert result.count == 0
        assert len(result.summaries) == 0
        assert len(result.insights.top_ports) == 0
        assert len(result.insights.top_protocols) == 0
        assert len(result.insights.top_software) == 0

    def test_single_host_basic(self):
        """Test summarizing single host with basic service"""
        host = Host(
            ip="192.168.1.1",
            services=[
                Service(port=80, protocol="tcp", banner="Apache/2.4.41")
            ]
        )
        
        result = self.summarizer.summarize([host])
        
        assert result.count == 1
        assert len(result.summaries) == 1
        
        summary = result.summaries[0]
        assert summary["ip"] == "192.168.1.1"
        assert "80" in summary["summary"]
        assert "tcp" in summary["summary"]

    def test_single_host_with_software(self):
        """Test summarizing host with software information"""
        software = Software(product="nginx", vendor="F5", version="1.18.0")
        service = Service(
            port=443, 
            protocol="tcp", 
            banner="nginx/1.18.0",
            software=[software]
        )
        host = Host(ip="10.0.0.1", services=[service])
        
        result = self.summarizer.summarize([host])
        
        summary = result.summaries[0]
        assert summary["ip"] == "10.0.0.1"
        assert "443" in summary["summary"]
        assert "nginx" in summary["summary"]

    def test_host_with_location_and_asn(self):
        """Test summarizing host with location and ASN info"""
        location = Location(country="United States", city="New York")
        asn = ASN(asn=15169, name="GOOGLE", description="Google LLC")
        
        host = Host(
            ip="8.8.8.8",
            location=location,
            autonomous_system=asn,
            services=[Service(port=53, protocol="udp")]
        )
        
        result = self.summarizer.summarize([host])
        
        summary = result.summaries[0]
        assert summary["ip"] == "8.8.8.8"
        assert "United States" in summary["summary"] or "GOOGLE" in summary["summary"]

    def test_multiple_hosts(self):
        """Test summarizing multiple hosts"""
        hosts = [
            Host(ip="192.168.1.1", services=[Service(port=80, protocol="tcp")]),
            Host(ip="192.168.1.2", services=[Service(port=443, protocol="tcp")]),
            Host(ip="192.168.1.3", services=[Service(port=22, protocol="tcp")])
        ]
        
        result = self.summarizer.summarize(hosts)
        
        assert result.count == 3
        assert len(result.summaries) == 3
        
        ips = [s["ip"] for s in result.summaries]
        assert "192.168.1.1" in ips
        assert "192.168.1.2" in ips
        assert "192.168.1.3" in ips

    def test_insights_generation(self):
        """Test that insights are properly generated"""
        hosts = [
            Host(
                ip="192.168.1.1",
                location=Location(country="US"),
                autonomous_system=ASN(asn=15169, name="GOOGLE"),
                services=[
                    Service(
                        port=80, 
                        protocol="tcp", 
                        software=[Software(product="Apache")]
                    )
                ]
            ),
            Host(
                ip="192.168.1.2",
                location=Location(country="US"),
                autonomous_system=ASN(asn=16509, name="AMAZON"),
                services=[
                    Service(
                        port=80, 
                        protocol="tcp", 
                        software=[Software(product="nginx")]
                    )
                ]
            )
        ]
        
        result = self.summarizer.summarize(hosts)
        
        # Check insights
        assert len(result.insights.top_ports) > 0
        assert len(result.insights.top_protocols) > 0
        assert len(result.insights.top_software) > 0
        assert len(result.insights.top_asns) > 0
        assert len(result.insights.countries) > 0
        
        # Verify specific counts
        port_80_count = next((item.get("80", 0) for item in result.insights.top_ports), 0)
        assert port_80_count == 2
        
        tcp_count = next((item.get("tcp", 0) for item in result.insights.top_protocols), 0)
        assert tcp_count == 2
        
        us_count = next((item.get("US", 0) for item in result.insights.countries), 0)
        assert us_count == 2

    def test_severity_assignment(self):
        """Test that severity hints are assigned"""
        # High-risk service (SSH on non-standard port)
        high_risk_host = Host(
            ip="192.168.1.1",
            services=[Service(port=22, protocol="tcp", banner="SSH-2.0")]
        )
        
        # Low-risk service (HTTP)
        low_risk_host = Host(
            ip="192.168.1.2",
            services=[Service(port=80, protocol="tcp")]
        )
        
        result = self.summarizer.summarize([high_risk_host, low_risk_host])
        
        # All summaries should have severity hints assigned
        for summary in result.summaries:
            assert "severity_hint" in summary
            assert summary["severity_hint"] in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO", "UNKNOWN"]

    def test_host_with_no_services(self):
        """Test summarizing host with no services"""
        host = Host(ip="192.168.1.1", services=[])
        
        result = self.summarizer.summarize([host])
        
        assert result.count == 1
        summary = result.summaries[0]
        assert summary["ip"] == "192.168.1.1"
        assert "no services" in summary["summary"].lower() or "no open ports" in summary["summary"].lower()

    def test_host_with_multiple_services(self):
        """Test summarizing host with multiple services"""
        host = Host(
            ip="192.168.1.1",
            services=[
                Service(port=22, protocol="tcp", banner="SSH-2.0"),
                Service(port=80, protocol="tcp", banner="Apache/2.4"),
                Service(port=443, protocol="tcp", banner="nginx/1.18"),
                Service(port=3306, protocol="tcp", banner="MySQL 5.7")
            ]
        )
        
        result = self.summarizer.summarize([host])
        
        summary = result.summaries[0]
        assert summary["ip"] == "192.168.1.1"
        
        # Should mention multiple services
        summary_text = summary["summary"].lower()
        assert "22" in summary["summary"] or "ssh" in summary_text
        assert "80" in summary["summary"] or "http" in summary_text
        assert "443" in summary["summary"] or "https" in summary_text
        assert "3306" in summary["summary"] or "mysql" in summary_text

    def test_duplicate_software_handling(self):
        """Test that duplicate software entries are handled correctly in insights"""
        hosts = [
            Host(
                ip="192.168.1.1",
                services=[
                    Service(port=80, software=[Software(product="Apache")]),
                    Service(port=8080, software=[Software(product="Apache")])
                ]
            ),
            Host(
                ip="192.168.1.2",
                services=[Service(port=80, software=[Software(product="Apache")])]
            )
        ]
        
        result = self.summarizer.summarize(hosts)
        
        # Apache should appear only once in top_software with correct count
        apache_count = next((item.get("Apache", 0) for item in result.insights.top_software), 0)
        assert apache_count == 3  # 2 from first host + 1 from second host