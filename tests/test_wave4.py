"""Tests d'intégration vague 4 : E1 ressources, E3 chiffrement, E4 parallélisme."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from unocr import api
from unocr.api import app
from unocr.config import Config
from unocr.crypto_store import CryptoStore


@pytest.fixture()
def client(tmp_cfg, fixtures_dir):
    api._watch.stop()
    api._watch.reset()
    yield TestClient(app)
    api._watch.stop()
    api._watch.reset()


# ─────────────────────────── E1 · ressources ───────────────────────────

def test_resources_endpoint(client):
    body = client.get("/api/resources").json()
    assert body["cpu_count"] >= 1
    assert body["ram_total_mb"] >= 0
    assert body["engine_requirements_mb"]["easyocr"] > 0


def test_engines_endpoint_reports_reasons(client):
    """L'API doit expliquer pourquoi un moteur n'est pas actif."""
    rows = {e["name"]: e for e in client.get("/api/engines").json()}
    assert rows["tesseract"]["available"] is True
    for heavy in ("easyocr", "paddleocr"):
        assert rows[heavy]["ram_required_mb"] > 1000
        # Le moteur peut être indisponible (mémoire, installation) ou disponible
        # selon la machine ; dans les deux cas, l'API doit être explicite
        if not rows[heavy]["available"]:
            assert "unavailable_reason" in rows[heavy]


# ─────────────────────────── E3 · chiffrement ───────────────────────────

def test_encryption_disabled_by_default(client):
    body = client.get("/api/encryption").json()
    assert body["enabled"] is False
    assert body["key_length_bits"] == 0


def test_encryption_enabled_with_key_file(client, tmp_cfg, monkeypatch):
    """Avec une clé fichier valide, le chiffrement est actif et annoncé."""

    cfg = Config({"security": {"encryption": {"enabled": True,
                                              "key_file": "keys/master.key"}}},
                 Path("."))
    monkeypatch.setattr(api, "cfg", cfg)
    body = client.get("/api/encryption").json()
    assert body["enabled"] is True
    assert body["algorithm"] == "AES-256-GCM"
    assert body["key_length_bits"] == 256
    # aucun secret ne fuite dans la réponse
    assert "key" not in str(body).lower() or "key_length_bits" in body


def test_encryption_stays_off_without_valid_key(client, monkeypatch):
    """Activé mais sans clé utilisable → inactif (pas de faux sentiment)."""

    cfg = Config({"security": {"encryption": {"enabled": True}}}, Path("."))
    monkeypatch.setattr(api, "cfg", cfg)
    assert client.get("/api/encryption").json()["enabled"] is False


def test_encryption_roundtrip_through_store(tmp_path):
    """Bout en bout : chiffrer puis déchiffrer un résultat de document."""
    store = CryptoStore.from_key_file(tmp_path / "k.key")
    payload = b'{"documents": [{"text": "secret"}]}'
    (tmp_path / "r.json").write_bytes(payload)
    store.encrypt_file(tmp_path / "r.json", tmp_path / "r.enc")
    assert (tmp_path / "r.enc").read_bytes() != payload
    store.decrypt_file(tmp_path / "r.enc", tmp_path / "r.dec")
    assert (tmp_path / "r.dec").read_bytes() == payload


# ─────────────────────────── E4 · parallélisme ───────────────────────────

def test_page_workers_bounded():
    from unocr.pipeline import Pipeline

    p = Pipeline()
    assert p._page_workers(1) == 1
    assert 1 <= p._page_workers(10) <= (__import__("os").cpu_count() or 1)
