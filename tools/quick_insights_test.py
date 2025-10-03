from backend.analytics import generate_insights
from backend.schemas import Host, Service, Software, ASN, Location

hosts = []
for i in range(3):
    software = Software(product="Apache")
    service = Service(port=80, protocol="tcp", software=[software])
    asn = ASN(asn=15169, name="GOOGLE")
    location = Location(country="US")
    host = Host(ip=f"192.168.1.{i+1}", services=[service], autonomous_system=asn, location=location)
    hosts.append(host)

different_host = Host(
    ip="192.168.1.4",
    services=[Service(port=443, protocol="tcp", software=[Software(product="nginx")])],
    autonomous_system=ASN(asn=16509, name="AMAZON"),
    location=Location(country="Canada")
)
hosts.append(different_host)

insights = generate_insights(hosts)
print('ports:', insights.top_ports)
print('protocols:', insights.top_protocols)
print('software:', insights.top_software)
print('asns:', insights.top_asns)
print('countries:', insights.countries)
