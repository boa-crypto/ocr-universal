"""Pièces justificatives : API multipart réelle, métadonnées et fichiers temporaires."""
import hashlib
import sqlite3
from types import SimpleNamespace

import pytest

from unocr.backup import creer_sauvegarde, restaurer_sauvegarde
from unocr.business_store import BusinessStore
from unocr.models import Justificatif
from unocr.routes import frais


@pytest.fixture
def piece(client_factory):
    with client_factory() as client:
        rep = client.post("/api/frais", json={"dossier_id": "dos_test", "montant": 42})
        assert rep.status_code == 200
        identifiant = rep.json()["id"]
    return identifiant


def upload(client, frais_id, contenu=b"piece test", nom="piece.pdf"):
    return client.post("/api/frais/justificatif/upload", data={"frais_id": frais_id},
                       files={"fichier": (nom, contenu, "application/pdf")})


def test_cycle_reouverture_suppression(client_factory, piece, tmp_path):
    with client_factory() as client:
        rep = upload(client, piece, nom="../../piece.pdf")
        assert rep.status_code == 200, rep.text
        identifiant = rep.json()["id"]
        assert rep.json()["nom_fichier"] == "piece.pdf"
        assert rep.json()["hash"] == hashlib.sha256(b"piece test").hexdigest()
    with client_factory() as client:
        liste = client.get(f"/api/frais/{piece}/justificatifs").json()
        assert [j["id"] for j in liste] == [identifiant]
        assert "chemin_fichier" not in liste[0]
        assert client.get(f"/api/frais/{piece}").json()["justificatifs"] == [identifiant]
        assert client.delete(f"/api/frais/{piece}").status_code == 409
        rep = client.get(f"/api/frais/justificatif/{identifiant}/download")
        assert rep.status_code == 200 and rep.content == b"piece test"
        assert rep.headers["x-content-type-options"] == "nosniff"
        assert client.delete(f"/api/frais/justificatif/{identifiant}").status_code == 200
    with client_factory() as client:
        assert client.get(f"/api/frais/{piece}/justificatifs").json() == []
        assert client.get(f"/api/frais/{piece}").json()["justificatifs"] == []
        assert client.get(f"/api/frais/justificatif/{identifiant}/download").status_code == 404
        assert client.delete(f"/api/frais/{piece}").status_code == 200
    assert list((tmp_path / "justificatifs").iterdir()) == []


@pytest.mark.parametrize("contenu,statut", [(b"", 422), (b"12345", 413)])
def test_limites_sans_fichier_ni_lien(client_factory, piece, tmp_path, monkeypatch, contenu, statut):
    monkeypatch.setattr(frais, "MAX_JUSTIFICATIF", 4)
    with client_factory() as client:
        assert upload(client, piece, contenu).status_code == statut
        assert client.get(f"/api/frais/{piece}").json()["justificatifs"] == []
    assert not (tmp_path / "justificatifs").exists()


def test_frais_absent_pas_de_fichier(client_factory, tmp_path):
    with client_factory() as client:
        assert upload(client, "frais_absent").status_code == 404
    assert list((tmp_path / "justificatifs").glob("*")) == []


@pytest.mark.parametrize("collection", ["justificatif", "frais"])
def test_echec_base_nettoie_fichier(client_factory, piece, tmp_path, monkeypatch, collection):
    original = BusinessStore.__setitem__

    def panne(self, cle, valeur):
        if self.collection == collection:
            raise sqlite3.OperationalError("panne simulée")
        return original(self, cle, valeur)

    monkeypatch.setattr(BusinessStore, "__setitem__", panne)
    with client_factory() as client:
        assert upload(client, piece).status_code == 503
        assert client.get(f"/api/frais/{piece}").json()["justificatifs"] == []
    assert list((tmp_path / "justificatifs").iterdir()) == []


def test_suppression_rollback_restaure_fichier(client_factory, piece, tmp_path, monkeypatch):
    with client_factory() as client:
        identifiant = upload(client, piece).json()["id"]
        original = BusinessStore.__delitem__

        def panne(self, cle):
            if self.collection == "justificatif":
                raise sqlite3.OperationalError("panne simulée")
            return original(self, cle)

        monkeypatch.setattr(BusinessStore, "__delitem__", panne)
        assert client.delete(f"/api/frais/justificatif/{identifiant}").status_code == 503
        assert client.get(f"/api/frais/justificatif/{identifiant}/download").content == b"piece test"
        assert client.get(f"/api/frais/{piece}").json()["justificatifs"] == [identifiant]
    assert len(list((tmp_path / "justificatifs").glob("*.bin"))) == 1


@pytest.mark.parametrize("chemin", ["../secret", "/tmp/secret", "justificatifs/../secret"])
def test_chemin_stocke_hostile_refuse(client_factory, piece, tmp_path, chemin):
    magasin = BusinessStore(tmp_path / "metier.sqlite3", "justificatif", Justificatif)
    magasin["just_hostile"] = Justificatif(id="just_hostile", frais_id=piece, chemin_fichier=chemin)
    with client_factory() as client:
        assert client.get("/api/frais/justificatif/just_hostile/download").status_code == 403
        assert client.delete("/api/frais/justificatif/just_hostile").status_code == 403
    assert magasin["just_hostile"].chemin_fichier == chemin


def test_fichier_altere_detecte(client_factory, piece, tmp_path):
    with client_factory() as client:
        identifiant = upload(client, piece).json()["id"]
        fichier = next((tmp_path / "justificatifs").glob("*.bin"))
        fichier.write_bytes(b"alteration")
        assert client.get(f"/api/frais/justificatif/{identifiant}/download").status_code == 409


def test_sauvegarde_restauree_autre_emplacement(client_factory, piece, tmp_path, monkeypatch):
    with client_factory() as client:
        identifiant = upload(client, piece).json()["id"]
    cfg = frais.cfg
    sauvegarde = creer_sauvegarde(cfg, destination=tmp_path / "archives")
    autre = SimpleNamespace(data_dir=tmp_path / "restaure", log_dir=tmp_path / "logs_restaures")
    restaurer_sauvegarde(autre, sauvegarde.chemin)
    monkeypatch.setattr(frais, "cfg", autre)
    with client_factory() as client:
        rep = client.get(f"/api/frais/justificatif/{identifiant}/download")
        assert rep.status_code == 200, rep.text
        assert rep.content == b"piece test"


def test_fichier_absent_reste_nettoyable(client_factory, piece, tmp_path):
    with client_factory() as client:
        identifiant = upload(client, piece).json()["id"]
        next((tmp_path / "justificatifs").glob("*.bin")).unlink()
        assert client.get(f"/api/frais/justificatif/{identifiant}/download").status_code == 404
        assert client.delete(f"/api/frais/justificatif/{identifiant}").status_code == 200
        assert client.get(f"/api/frais/{piece}").json()["justificatifs"] == []


def test_symlink_fichier_refuse(client_factory, piece, tmp_path):
    with client_factory() as client:
        identifiant = upload(client, piece).json()["id"]
        fichier = next((tmp_path / "justificatifs").glob("*.bin"))
        fichier.unlink()
        secret = tmp_path / "secret"
        secret.write_bytes(b"secret")
        fichier.symlink_to(secret)
        assert client.get(f"/api/frais/justificatif/{identifiant}/download").status_code == 403
        assert client.delete(f"/api/frais/justificatif/{identifiant}").status_code == 403
        assert secret.read_bytes() == b"secret"


def test_sauvegarde_coordonne_suppression(client_factory, piece, tmp_path, monkeypatch):
    import zipfile
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    with client_factory() as client:
        identifiant = upload(client, piece).json()["id"]
    debut = Event()
    original = zipfile.ZipFile.write
    travail = []

    def supprimer():
        with client_factory() as client:
            debut.set()
            return client.delete(f"/api/frais/justificatif/{identifiant}").status_code

    with ThreadPoolExecutor(max_workers=1) as pool:
        def copie(self, fichier, *args, **kwargs):
            if str(fichier).endswith(".bin") and not travail:
                travail.append(pool.submit(supprimer))
                assert debut.wait(timeout=5)
                assert not travail[0].done(), "Suppression non bloquée par le verrou de sauvegarde"
            return original(self, fichier, *args, **kwargs)
        monkeypatch.setattr(zipfile.ZipFile, "write", copie)
        sauvegarde = creer_sauvegarde(frais.cfg, destination=tmp_path / "archives")
        assert travail[0].result(timeout=15) == 200
    autre = SimpleNamespace(data_dir=tmp_path / "restaure", log_dir=tmp_path / "autres_logs")
    restaurer_sauvegarde(autre, sauvegarde.chemin)
    monkeypatch.setattr(frais, "cfg", autre)
    with client_factory() as client:
        rep = client.get(f"/api/frais/justificatif/{identifiant}/download")
        assert rep.status_code == 200 and rep.content == b"piece test"


@pytest.mark.parametrize("repertoire", [True, False])
def test_sauvegarde_refuse_symlink_justificatif(client_factory, piece, tmp_path, repertoire):
    from unocr.backup import BackupError

    cible = tmp_path / "secret_test"
    cible.mkdir()
    (cible / "secret.bin").write_bytes(b"secret")
    racine = tmp_path / "justificatifs"
    if repertoire:
        racine.symlink_to(cible, target_is_directory=True)
    else:
        racine.mkdir()
        (racine / ("a" * 32 + ".bin")).symlink_to(cible / "secret.bin")
    with pytest.raises(BackupError, match="symbolique"):
        creer_sauvegarde(frais.cfg, destination=tmp_path / "archives")
