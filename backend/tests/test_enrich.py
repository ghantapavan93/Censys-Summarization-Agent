from backend.enrich import score_host, set_kev_ids


def test_kev_and_cvss_scoring():
    set_kev_ids({"CVE-2023-44487"})
    host = {
        "ip": "1.2.3.4",
        "services": [
            {
                "protocol": "HTTP",
                "port": 8080,
                "vulns": [
                    {"id": "CVE-2023-44487", "metrics": {"cvss_v31": {"score": 7.5}}}
                ],
            }
        ],
    }
    out = score_host(host)
    assert out["risk_score"] >= 40 + 25  # kev + cvss
    assert out["kev_present"] is True
    assert out["cvss_high_present"] is True
