"""
Test configuration and fixtures for the Censys Summarization Agent test suite.
"""

import pytest
import sys
import os

# Add repository root to Python path so 'backend' package resolves
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Pytest configuration
pytest_plugins = []

def pytest_configure(config):
    """Configure pytest with custom settings."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )

@pytest.fixture(scope="session")
def sample_host_data():
    """Fixture providing sample host data for tests."""
    from backend.schemas import Host, Service, Software, ASN, Location
    
    return [
        Host(
            ip="192.168.1.100",
            location=Location(
                country="United States",
                city="Mountain View",
                province="California"
            ),
            autonomous_system=ASN(
                asn=15169,
                name="GOOGLE",
                description="Google LLC",
                country_code="US"
            ),
            services=[
                Service(
                    port=22,
                    protocol="tcp",
                    banner="SSH-2.0-OpenSSH_8.0",
                    software=[
                        Software(
                            product="OpenSSH",
                            vendor="OpenBSD",
                            version="8.0"
                        )
                    ],
                    labels=["ssh", "remote_access"]
                ),
                Service(
                    port=80,
                    protocol="tcp",
                    banner="Apache/2.4.41 (Ubuntu)",
                    software=[
                        Software(
                            product="Apache HTTP Server",
                            vendor="Apache Software Foundation",
                            version="2.4.41"
                        )
                    ],
                    labels=["http", "web_server"]
                ),
                Service(
                    port=443,
                    protocol="tcp",
                    banner="nginx/1.18.0",
                    software=[
                        Software(
                            product="nginx",
                            vendor="F5 Inc.",
                            version="1.18.0"
                        )
                    ],
                    labels=["https", "web_server", "ssl"]
                )
            ]
        ),
        Host(
            ip="10.0.0.50",
            location=Location(
                country="Germany",
                city="Frankfurt",
                province="Hesse"
            ),
            autonomous_system=ASN(
                asn=16509,
                name="AMAZON-02",
                description="Amazon.com, Inc.",
                country_code="US"
            ),
            services=[
                Service(
                    port=3306,
                    protocol="tcp",
                    banner="MySQL 5.7.30",
                    software=[
                        Software(
                            product="MySQL",
                            vendor="Oracle Corporation",
                            version="5.7.30"
                        )
                    ],
                    labels=["mysql", "database"]
                )
            ]
        )
    ]

@pytest.fixture
def mock_openai_response():
    """Fixture providing mock OpenAI API response."""
    return {
        "choices": [
            {
                "message": {
                    "content": '{"ip": "192.168.1.1", "summary": "Test summary", "severity_hint": "MEDIUM"}'
                }
            }
        ]
    }

@pytest.fixture
def temp_json_file(tmp_path):
    """Fixture providing a temporary JSON file for testing."""
    sample_data = {
        "ip": "192.168.1.1",
        "services": [
            {"port": 80, "protocol": "tcp", "banner": "Apache/2.4.41"}
        ]
    }
    
    import json
    temp_file = tmp_path / "test_data.json"
    temp_file.write_text(json.dumps(sample_data, indent=2))
    return str(temp_file)