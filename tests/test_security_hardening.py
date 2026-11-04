from fastapi.testclient import TestClient

from unocr import api


def test_security_headers_are_present() -> None:
    client = TestClient(api.app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "permissions-policy" in response.headers


def test_default_cors_is_not_wildcard() -> None:
    origins = api._configured_cors_origins()
    assert isinstance(origins, list)
    assert origins != ["*"]
    assert any("localhost" in origin or "127.0.0.1" in origin for origin in origins)


def test_security_status_endpoint_exposes_hardening() -> None:
    client = TestClient(api.app)
    response = client.get("/api/security")
    assert response.status_code == 200
    payload = response.json()
    assert "auth_required" in payload
    assert "cors_origins" in payload
    assert "headers" in payload
    assert payload["headers"]["x_frame_options"] == "DENY"


def test_trusted_hosts_are_restricted() -> None:
    hosts = api._configured_allowed_hosts()
    assert isinstance(hosts, list)
    assert hosts
    assert all(h not in ("*", "") for h in hosts)
    assert "localhost" in hosts or "127.0.0.1" in hosts


def test_content_security_policy_is_set() -> None:
    client = TestClient(api.app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert "content-security-policy" in response.headers
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_hsts_is_added_when_enabled() -> None:
    api.cfg = type("Cfg", (), {"get": lambda self, key, default=None: {"api.hsts": True}.get(key, default)})()
    try:
        client = TestClient(api.app)
        response = client.get("/api/health")
        assert response.status_code == 200
        assert "strict-transport-security" in response.headers
        assert "max-age=31536000" in response.headers["strict-transport-security"]
    finally:
        api.cfg = api.get_config() if hasattr(api, "get_config") else api.cfg


def test_server_and_x_powered_by_headers_are_hidden() -> None:
    client = TestClient(api.app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert "server" not in response.headers
    assert "x-powered-by" not in response.headers


def test_security_policy_helper_controls_headers_consistently() -> None:
    policy = api._default_security_headers()
    assert policy["x_frame_options"] == "DENY"
    assert policy["content_security_policy"].startswith("default-src 'self'")
    assert policy["referrer_policy"] == "no-referrer"
