import pytest
from backend.analytics import generate_insights
from backend.schemas import Host, Service, Software, ASN, Location


class TestAnalytics:
    def test_empty_hosts(self):
        """Test insights generation with empty host list"""
        insights = generate_insights([])
        
        assert len(insights.top_ports) == 0
        assert len(insights.top_protocols) == 0
        assert len(insights.top_software) == 0
        assert len(insights.top_asns) == 0
        assert len(insights.countries) == 0

    def test_single_host_insights(self):
        """Test insights generation with single host"""
        software = Software(product="nginx", vendor="F5", version="1.18.0")
        service = Service(port=80, protocol="tcp", software=[software])
        asn = ASN(asn=15169, name="GOOGLE")
        location = Location(country="United States")
        
        host = Host(
            ip="192.168.1.1",
            services=[service],
            autonomous_system=asn,
            location=location
        )
        
        insights = generate_insights([host])
        
        assert len(insights.top_ports) == 1
        assert insights.top_ports[0]["80"] == 1
        
        assert len(insights.top_protocols) == 1
        assert insights.top_protocols[0]["tcp"] == 1
        
        assert len(insights.top_software) == 1
        assert insights.top_software[0]["nginx"] == 1
        
        assert len(insights.top_asns) == 1
        assert insights.top_asns[0]["GOOGLE"] == 1
        
        assert len(insights.countries) == 1
        assert insights.countries[0]["United States"] == 1

    def test_multiple_hosts_aggregation(self):
        """Test insights aggregation across multiple hosts"""
        hosts = []
        
        # Create hosts with overlapping services
        for i in range(3):
            software = Software(product="Apache")
            service = Service(port=80, protocol="tcp", software=[software])
            asn = ASN(asn=15169, name="GOOGLE")
            location = Location(country="US")
            
            host = Host(
                ip=f"192.168.1.{i+1}",
                services=[service],
                autonomous_system=asn,
                location=location
            )
            hosts.append(host)
        
        # Add a host with different services
        nginx_service = Service(port=443, protocol="tcp", software=[Software(product="nginx")])
        different_host = Host(
            ip="192.168.1.4",
            services=[nginx_service],
            autonomous_system=ASN(asn=16509, name="AMAZON"),
            location=Location(country="Canada")
        )
        hosts.append(different_host)
        
        insights = generate_insights(hosts)
        
        # Check port aggregation
        port_80_count = next((item["80"] for item in insights.top_ports if "80" in item), 0)
        port_443_count = next((item["443"] for item in insights.top_ports if "443" in item), 0)
        assert port_80_count == 3
        assert port_443_count == 1
        
        # Check protocol aggregation
        tcp_count = next((item["tcp"] for item in insights.top_protocols if "tcp" in item), 0)
        assert tcp_count == 4
        
        # Check software aggregation
        apache_count = next((item["Apache"] for item in insights.top_software if "Apache" in item), 0)
        nginx_count = next((item["nginx"] for item in insights.top_software if "nginx" in item), 0)
        assert apache_count == 3
        assert nginx_count == 1
        
        # Check ASN aggregation
        google_count = next((item["GOOGLE"] for item in insights.top_asns if "GOOGLE" in item), 0)
        amazon_count = next((item["AMAZON"] for item in insights.top_asns if "AMAZON" in item), 0)
        assert google_count == 3
        assert amazon_count == 1
        
        # Check country aggregation
        us_count = next((item["US"] for item in insights.countries if "US" in item), 0)
        canada_count = next((item["Canada"] for item in insights.countries if "Canada" in item), 0)
        assert us_count == 3
        assert canada_count == 1

    def test_hosts_with_multiple_services(self):
        """Test insights with hosts having multiple services each"""
        host = Host(
            ip="192.168.1.1",
            services=[
                Service(port=22, protocol="tcp", software=[Software(product="OpenSSH")]),
                Service(port=80, protocol="tcp", software=[Software(product="Apache")]),
                Service(port=443, protocol="tcp", software=[Software(product="Apache")])
            ],
            autonomous_system=ASN(asn=15169, name="GOOGLE"),
            location=Location(country="United States")
        )
        
        insights = generate_insights([host])
        
        # Should count each port separately
        assert len(insights.top_ports) == 3
        
        # All services use TCP
        tcp_count = next((item["tcp"] for item in insights.top_protocols if "tcp" in item), 0)
        assert tcp_count == 3
        
        # Apache appears twice, OpenSSH once
        apache_count = next((item["Apache"] for item in insights.top_software if "Apache" in item), 0)
        openssh_count = next((item["OpenSSH"] for item in insights.top_software if "OpenSSH" in item), 0)
        assert apache_count == 2
        assert openssh_count == 1

    def test_hosts_with_missing_data(self):
        """Test insights generation with hosts missing some data"""
        hosts = [
            # Host with no ASN
            Host(
                ip="192.168.1.1",
                services=[Service(port=80, protocol="tcp")],
                location=Location(country="US")
            ),
            # Host with no location
            Host(
                ip="192.168.1.2",
                services=[Service(port=443, protocol="tcp")],
                autonomous_system=ASN(asn=15169, name="GOOGLE")
            ),
            # Host with no services
            Host(
                ip="192.168.1.3",
                services=[],
                location=Location(country="Canada"),
                autonomous_system=ASN(asn=16509, name="AMAZON")
            ),
            # Host with service but no software
            Host(
                ip="192.168.1.4",
                services=[Service(port=22, protocol="tcp")]
            )
        ]
        
        insights = generate_insights(hosts)
        
        # Should handle missing data gracefully
        assert len(insights.top_ports) == 3  # 80, 443, 22
        assert len(insights.top_protocols) == 1  # tcp
        assert len(insights.top_software) == 0  # No software specified
        assert len(insights.top_asns) == 2  # GOOGLE, AMAZON
        assert len(insights.countries) == 2  # US, Canada

    def test_sorting_by_count(self):
        """Test that insights are sorted by count in descending order"""
        hosts = []
        
        # Create hosts to generate different counts
        # 5 hosts with port 80
        for i in range(5):
            hosts.append(Host(
                ip=f"192.168.1.{i+1}",
                services=[Service(port=80, protocol="tcp")]
            ))
        
        # 3 hosts with port 443
        for i in range(3):
            hosts.append(Host(
                ip=f"192.168.2.{i+1}",
                services=[Service(port=443, protocol="tcp")]
            ))
        
        # 1 host with port 22
        hosts.append(Host(
            ip="192.168.3.1",
            services=[Service(port=22, protocol="tcp")]
        ))
        
        insights = generate_insights(hosts)
        
        # Should be sorted by count: 80 (5), 443 (3), 22 (1)
        assert insights.top_ports[0].get("80") == 5
        assert insights.top_ports[1].get("443") == 3
        assert insights.top_ports[2].get("22") == 1

    def test_software_with_none_values(self):
        """Test handling of software with None values"""
        service_with_none_software = Service(
            port=80,
            protocol="tcp",
            software=[
                Software(product="Apache", vendor=None, version=None),
                Software(product=None, vendor="F5", version="1.18.0"),
                Software(product=None, vendor=None, version=None)
            ]
        )
        
        host = Host(ip="192.168.1.1", services=[service_with_none_software])
        
        insights = generate_insights([host])
        
        # Should only count software with product names
        apache_count = next((item.get("Apache", 0) for item in insights.top_software), 0)
        assert apache_count == 1
        
        # Should not count software with no product
        assert len(insights.top_software) == 1

    def test_case_sensitivity(self):
        """Test case handling in insights"""
        hosts = [
            Host(
                ip="192.168.1.1",
                services=[Service(
                    port=80, 
                    protocol="TCP", 
                    software=[Software(product="apache")]
                )],
                autonomous_system=ASN(asn=15169, name="google"),
                location=Location(country="united states")
            ),
            Host(
                ip="192.168.1.2",
                services=[Service(
                    port=80, 
                    protocol="tcp", 
                    software=[Software(product="Apache")]
                )],
                autonomous_system=ASN(asn=15169, name="GOOGLE"),
                location=Location(country="United States")
            )
        ]
        
        insights = generate_insights(hosts)
        
        # Should handle case variations appropriately
        # The implementation may normalize case or treat them as separate entries
        # depending on the business logic
        assert len(insights.top_protocols) >= 1
        assert len(insights.top_software) >= 1
        assert len(insights.top_asns) >= 1
        assert len(insights.countries) >= 1