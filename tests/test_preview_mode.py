"""Mode aperçu navigateur (UNOCR_PREVIEW) — assouplissement strictement borné.

Le déploiement réel doit rester verrouillé ; l'aperçu distant n'ouvre que
l'hôte du bac à sable et l'affichage en iframe.
"""
from fastapi.testclient import TestClient

from unocr.api import app
from unocr.config import get_config
from unocr.services import security as sec

HOTE_APERCU = "8000-demo.e2b.app"


def test_defaut_verrouille(monkeypatch) -> None:
    monkeypatch.delenv("UNOCR_PREVIEW", raising=False)
    cfg = get_config()

    hosts = sec._configured_allowed_hosts(cfg)
    assert sec.PREVIEW_HOST_PATTERN not in hosts

    policy = sec.default_security_headers(cfg)
    assert policy["x_frame_options"] == "DENY"
    assert "frame-ancestors 'none'" in policy["content_security_policy"]


def test_apercu_autorise_hote_et_iframe(monkeypatch) -> None:
    monkeypatch.setenv("UNOCR_PREVIEW", "1")
    cfg = get_config()

    hosts = sec._configured_allowed_hosts(cfg)
    assert sec.PREVIEW_HOST_PATTERN in hosts
    # Les hôtes locaux restent acceptés en aperçu.
    assert "127.0.0.1" in hosts and "localhost" in hosts

    policy = sec.default_security_headers(cfg)
    assert policy["x_frame_options"] == ""  # en-tête omis
    assert "frame-ancestors *" in policy["content_security_policy"]


def test_apercu_omet_x_frame_options_mais_garde_les_autres_entetes(monkeypatch) -> None:
    monkeypatch.setenv("UNOCR_PREVIEW", "1")
    client = TestClient(app)

    reponse = client.get("/api/health")
    assert reponse.status_code == 200
    assert "x-frame-options" not in reponse.headers
    assert reponse.headers["x-content-type-options"] == "nosniff"
    assert "content-security-policy" in reponse.headers
