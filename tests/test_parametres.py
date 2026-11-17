"""Paramètres généraux : écriture validée, persistée et réellement appliquée.

Ce que ces tests protègent : une page de paramètres qui accepte une saisie
sans l'appliquer. Chaque cas vérifie donc l'**effet**, pas seulement le code
HTTP — la limite de taille change le comportement de l'import, la rétention
change celui de la purge.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from unocr.api import app
from unocr.config import Config, load_config


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Client API avec un répertoire de données isolé."""
    monkeypatch.setenv("UNOCR_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("UNOCR_LOG_DIR", str(tmp_path / "logs"))
    cfg = app.state.cfg
    anciennes = dict(getattr(cfg, "surcharges", {}))
    ancienne_data = cfg.data
    yield TestClient(app)
    # rien ne doit rester d'un test à l'autre
    cfg.surcharges = anciennes
    cfg.data = ancienne_data


def test_catalogue_ne_propose_que_des_reglages_appliques(client):
    """Chaque réglage annoncé doit être lu par le code, pas décoratif."""
    corps = client.get("/api/parametres").json()
    assert corps["total"] == len(corps["parametres"]) >= 5
    cles = {p["cle"] for p in corps["parametres"]}
    assert {"max_file_size_mb", "max_pages", "security.retention_days"} <= cles
    for parametre in corps["parametres"]:
        assert parametre["effet"], parametre["cle"]
        assert parametre["valeur"] != "", parametre["cle"]


def test_ecriture_appliquee_et_persistee(client, tmp_path):
    reponse = client.put("/api/parametres/max_file_size_mb", json={"valeur": "7"})
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["valeur"] == "7"
    assert corps["modifie"] is True and corps["etat"] == "modifié"

    # effet immédiat : le serveur lit la nouvelle valeur
    assert app.state.cfg.get("max_file_size_mb") == 7

    # persistance : le fichier existe et sera relu au démarrage
    fichier = tmp_path / "data" / "parametres.json"
    assert json.loads(fichier.read_text())["max_file_size_mb"] == 7

    client.delete("/api/parametres/max_file_size_mb")
    assert app.state.cfg.get("max_file_size_mb") == 50


def test_valeur_hors_bornes_refusee_en_nommant_le_champ(client):
    reponse = client.put("/api/parametres/max_file_size_mb", json={"valeur": 9999})
    assert reponse.status_code == 422
    detail = reponse.json()["detail"]
    assert detail["champ"] == "max_file_size_mb"
    assert "maximum 500" in detail["message"]
    # rien n'a bougé
    assert app.state.cfg.get("max_file_size_mb") == 50


def test_valeur_non_numerique_refusee(client):
    reponse = client.put("/api/parametres/max_pages", json={"valeur": "beaucoup"})
    assert reponse.status_code == 422
    assert reponse.json()["detail"]["champ"] == "max_pages"


def test_langues_ocr_validees_et_normalisees(client):
    ok = client.put("/api/parametres/default_languages", json={"valeur": "FRA, eng"})
    assert ok.status_code == 200
    assert ok.json()["valeur"] == "fra, eng"
    assert app.state.cfg.get("default_languages") == ["fra", "eng"]

    trop_long = client.put("/api/parametres/default_languages",
                           json={"valeur": "français"})
    assert trop_long.status_code == 422
    assert "trois lettres" in trop_long.json()["detail"]["message"]
    client.delete("/api/parametres/default_languages")


def test_cle_inconnue_renvoie_404(client):
    assert client.get("/api/parametres/inconnu").status_code == 404
    assert client.put("/api/parametres/inconnu", json={"valeur": 1}).status_code == 404
    assert client.delete("/api/parametres/inconnu").status_code == 404


def test_reinitialisation_et_double_reinitialisation(client):
    client.put("/api/parametres/max_batch_size_mb", json={"valeur": 300})
    assert app.state.cfg.get("max_batch_size_mb") == 300
    assert client.delete("/api/parametres/max_batch_size_mb").status_code == 200
    assert app.state.cfg.get("max_batch_size_mb") == 200
    # déjà au défaut : 409 explicite plutôt qu'un faux succès
    encore = client.delete("/api/parametres/max_batch_size_mb")
    assert encore.status_code == 409
    assert "valeur par défaut" in encore.json()["detail"]


def test_limite_de_taille_change_le_comportement_de_l_import(client):
    """La preuve par l'effet : 1 Mo refusé, 50 Mo accepté."""
    import io

    gros = b"%PDF-1.4\n" + b"0" * (2 * 1024 * 1024)
    client.put("/api/parametres/max_file_size_mb", json={"valeur": 1})
    refuse = client.post("/api/documents",
                         files={"file": ("gros.pdf", io.BytesIO(gros), "application/pdf")})
    assert refuse.status_code == 413
    assert "volumineux" in refuse.json()["detail"]

    client.delete("/api/parametres/max_file_size_mb")
    accepte = client.post("/api/documents",
                          files={"file": ("gros2.pdf", io.BytesIO(gros), "application/pdf")})
    assert accepte.status_code == 200
    assert accepte.json()["job_id"].startswith("job_")


def test_surcharges_relues_au_demarrage(tmp_path, monkeypatch):
    """Un réglage écrit survit à un redémarrage du serveur."""
    data = tmp_path / "data"
    data.mkdir()
    (data / "parametres.json").write_text(
        json.dumps({"max_pages": 1234, "default_languages": ["deu"]}), encoding="utf-8")
    monkeypatch.setenv("UNOCR_DATA_DIR", str(data))
    cfg = load_config()
    assert cfg.get("max_pages") == 1234
    assert cfg.get("default_languages") == ["deu"]
    assert isinstance(cfg, Config)


def test_fichier_illisible_ne_casse_pas_le_demarrage(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    (data / "parametres.json").write_text("{ pas du json", encoding="utf-8")
    monkeypatch.setenv("UNOCR_DATA_DIR", str(data))
    cfg = load_config()
    assert cfg.get("max_pages") == 500
