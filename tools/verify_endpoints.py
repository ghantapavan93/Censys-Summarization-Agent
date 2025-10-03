import json
from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)

print('--- /api/health ---')
health = client.get('/api/health')
print(health.status_code)
print(json.dumps(health.json(), indent=2))

print('\n--- /api/enrich/vulns ---')
payload = {
    'hosts': [
        {
            'ip': '1.2.3.4',
            'services': [{'port': 80}, {'port': 443}],
            'vulns': [
                {'id': 'CVE-2021-1234', 'cvss': 7.5, 'kev': True},
                {'id': 'CVE-2020-9999', 'cvss': 5.0}
            ]
        },
        {
            'ip': '5.6.7.8',
            'vulnerabilities': [{'id': 'CVE-2022-1111', 'cvss_v3': 8.2}],
            'services': []
        }
    ]
}

r = client.post('/api/enrich/vulns', json=payload)
print(r.status_code)
print(json.dumps(r.json(), indent=2))

print('\n--- /api/export/csv ---')
rows = [
    {'ip': '1.2.3.4', 'risk_score': 82, 'kev_present': True},
    {'ip': '5.6.7.8', 'risk_score': 30, 'cvss_high_present': True}
]
rcsv = client.post('/api/export/csv', json={'rows': rows})
print(rcsv.status_code)
print(rcsv.headers.get('content-type'))
print(rcsv.text.splitlines()[0])
