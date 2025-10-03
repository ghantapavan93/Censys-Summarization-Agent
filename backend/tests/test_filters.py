from backend.filters import allowed_host


def test_service_cap_filters_noise():
    host = {"service_count": 60}
    assert allowed_host(host, max_services=45, exclude_honeypots=True) is False


def test_allows_normal_host():
    host = {"service_count": 10, "labels": []}
    assert allowed_host(host) is True
