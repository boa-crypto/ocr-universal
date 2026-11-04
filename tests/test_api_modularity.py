from fastapi.testclient import TestClient

from unocr.api import app
from unocr.routes.system import router as system_router
from unocr.services.security import _configured_allowed_hosts, _configured_cors_origins


def test_api_exposes_modular_security_and_health_routes():
    client = TestClient(app)
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    system_paths = {route.path for route in system_router.routes}
    assert "/api/health" in system_paths
    assert "/api/engines" in system_paths
    assert "/api/languages" in system_paths

    allowed_hosts = _configured_allowed_hosts({"api.allowed_hosts": ["localhost", "127.0.0.1"]})
    cors_origins = _configured_cors_origins({"api.cors_origins": ["http://127.0.0.1:8000"]})

    assert "localhost" in allowed_hosts
    assert "http://127.0.0.1:8000" in cors_origins


def test_i18n_module_is_served_from_web_assets():
    response = TestClient(app).get("/modules/i18n-controls.js")

    assert response.status_code == 200
    assert "function setUILang(lang)" in response.text
