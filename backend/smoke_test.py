from fastapi.testclient import TestClient
from backend.app import app


def main() -> int:
    c = TestClient(app)
    h = c.get('/health')
    print('HEALTH', h.status_code, h.json())

    payload = {
        'records': [
            {'id': '1', 'ip': '1.1.1.1', 'port': 22, 'product': 'OpenSSH', 'version': '8.9', 'country': 'US'},
            {'id': '2', 'ip': '2.2.2.2', 'port': 443, 'product': 'nginx', 'version': '1.24', 'country': 'DE'},
        ],
        'nl': 'show risks and summary',
        'event_id': 'evt-smoke'
    }
    r = c.post('/summarize', json=payload)
    print('SUM', r.status_code)
    if r.status_code != 200:
        print('Body:', r.text[:400])
        return 1
    data = r.json()
    print('Keys:', sorted(list(data.keys())))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
