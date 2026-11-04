"""Tests vague 3 : authentification optionnelle (D3), PWA (C4), typage de zones (E2)."""

import pytest
from fastapi.testclient import TestClient

from unocr import api
from unocr.api import app


@pytest.fixture()
def client(tmp_cfg, fixtures_dir):
    api._watch.stop()
    api._watch.reset()
    yield TestClient(app)
    api._watch.stop()
    api._watch.reset()


# ─────────────────────────── D3 · authentification ───────────────────────────

def test_auth_disabled_by_default(client):
    """Sans UNIOCR_TOKEN, rien ne change : l'API reste ouverte."""
    body = client.get("/api/auth/status").json()
    assert body["required"] is False
    assert client.get("/api/jobs").status_code == 200


def test_auth_required_when_token_set(client, monkeypatch):
    """Avec UNIOCR_TOKEN, les routes /api/* exigent le jeton."""
    monkeypatch.setattr(api, "_AUTH_TOKEN", "secret-de-test")
    try:
        assert client.get("/api/jobs").status_code == 401
        assert client.get("/api/stats").status_code == 401
        assert client.get("/api/profiles").status_code == 401

        # routes exemptées : toujours accessibles
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/auth/status").status_code == 200

        # avec le bon jeton
        h = {"Authorization": "Bearer secret-de-test"}
        assert client.get("/api/jobs", headers=h).status_code == 200

        # avec un mauvais jeton
        assert client.get("/api/jobs",
                          headers={"Authorization": "Bearer faux"}).status_code == 401
    finally:
        monkeypatch.setattr(api, "_AUTH_TOKEN", "")


def test_auth_rejects_query_token(client, monkeypatch):
    """Les jetons ne transitent pas dans l'URL où ils peuvent être journalisés."""
    monkeypatch.setattr(api, "_AUTH_TOKEN", "abc123")
    try:
        assert client.get("/api/jobs?token=abc123").status_code == 401
        assert client.get("/api/jobs", headers={
            "Authorization": "Bearer abc123"}).status_code == 200
    finally:
        monkeypatch.setattr(api, "_AUTH_TOKEN", "")


def test_auth_status_reports_header(client, monkeypatch):
    monkeypatch.setattr(api, "_AUTH_TOKEN", "x")
    try:
        body = client.get("/api/auth/status").json()
        assert body["required"] is True
        assert body["header"].startswith("Authorization")
    finally:
        monkeypatch.setattr(api, "_AUTH_TOKEN", "")


# ─────────────────────────── C4 · PWA ───────────────────────────

def test_manifest_is_served(client):
    r = client.get("/manifest.webmanifest")
    assert r.status_code == 200
    body = r.json()
    assert body["name"]
    assert body["start_url"] == "/"
    assert any(i["sizes"] for i in body["icons"])


def test_service_worker_is_served(client):
    r = client.get("/sw.js")
    assert r.status_code == 200
    assert "caches" in r.text


# ─────────────────────────── E2 · typage de zones ───────────────────────────

def test_zone_typing_detects_checkbox(client, fixtures_dir):
    """Une case à cocher est repérée comme zone typée, pas comme texte."""
    from unocr.zone_typing import classify_zones

    zones = classify_zones(fixtures_dir / "text_pdf.pdf")
    assert isinstance(zones, list)
    for z in zones:
        assert z["kind"] in ("checkbox", "signature", "handwritten", "table", "text")
        assert 0.0 <= z["confidence"] <= 1.0
        assert z["page"] >= 1


def test_zone_typing_on_photo(client, fixtures_dir):
    from unocr.zone_typing import classify_zones

    zones = classify_zones(fixtures_dir / "photo_carte_grise.png")
    assert isinstance(zones, list)


def test_zone_typing_missing_file(client, tmp_path):
    from unocr.zone_typing import classify_zones

    assert classify_zones(tmp_path / "absent.png") == []
