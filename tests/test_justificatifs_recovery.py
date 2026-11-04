"""Récupération ciblée, opt-in et sans écrasement ; données temporaires uniquement."""
import hashlib
import json

import pytest

from unocr.business_store import BusinessStore
from unocr.cli import main
from unocr.justificatifs_diagnostic import diagnostiquer_pieces
from unocr.justificatifs_recovery import RecuperationRefusee, recuperer_piece
from unocr.models import Frais, Justificatif


@pytest.fixture
def cas(tmp_path):
    repertoire = tmp_path / "justificatifs"
    repertoire.mkdir()
    cible = repertoire / ("a" * 32 + ".bin")
    quarantaine = repertoire / ("." + cible.name + ".deleted.tmp")
    quarantaine.write_bytes(b"preuve")
    frais = BusinessStore(tmp_path / "metier.sqlite3", "frais", Frais)
    frais["frais_test"] = Frais(id="frais_test", justificatifs=["just_test"])
    pieces = BusinessStore(tmp_path / "metier.sqlite3", "justificatif", Justificatif)
    pieces["just_test"] = Justificatif(id="just_test", frais_id="frais_test",
        chemin_fichier="justificatifs/" + cible.name, taille_octets=6,
        hash_sha256=hashlib.sha256(b"preuve").hexdigest())
    return tmp_path, cible, quarantaine, frais, pieces


def instantane(racine):
    return {str(p.relative_to(racine)): (p.stat().st_mtime_ns, p.read_bytes())
            for p in racine.rglob("*") if p.is_file() and not p.is_symlink()}


def test_plan_sans_mutation(cas):
    racine, cible, _, _, _ = cas
    avant = instantane(racine)
    plan = recuperer_piece(racine, "just_test")
    assert plan["etat"] == "pret" and plan["applique"] is False
    assert not cible.exists()
    assert instantane(racine) == avant


def test_application_copie_preserve_preuve_et_base(cas):
    racine, cible, quarantaine, _, pieces = cas
    base_avant = (racine / "metier.sqlite3").read_bytes()
    rep = recuperer_piece(racine, "just_test", appliquer=True)
    assert rep["etat"] == "restaure" and rep["quarantaine_conservee"] is True
    assert cible.read_bytes() == quarantaine.read_bytes() == b"preuve"
    assert cible.stat().st_ino != quarantaine.stat().st_ino
    assert (racine / "metier.sqlite3").read_bytes() == base_avant
    assert pieces["just_test"].frais_id == "frais_test"
    assert "fichier_absent" not in {a["categorie"] for a in diagnostiquer_pieces(racine)["anomalies"]}
    assert list(cible.parent.glob(".restore-*.tmp")) == []
    with pytest.raises(RecuperationRefusee, match="déjà présente"):
        recuperer_piece(racine, "just_test", appliquer=True)


@pytest.mark.parametrize("contenu", [b"fausse", b"trop long", b""])
def test_empreinte_ou_taille_incorrecte_refusee(cas, contenu):
    racine, cible, quarantaine, _, _ = cas
    quarantaine.write_bytes(contenu)
    avant = instantane(racine)
    with pytest.raises(RecuperationRefusee, match="empreinte"):
        recuperer_piece(racine, "just_test", appliquer=True)
    assert not cible.exists() and instantane(racine) == avant


@pytest.mark.parametrize("anomalie", ["parent_absent", "lien_absent", "autre_frais", "chemin_partage"])
def test_liens_ambigus_refuses(cas, anomalie):
    racine, cible, _, frais, pieces = cas
    if anomalie == "parent_absent":
        del frais["frais_test"]
    elif anomalie == "lien_absent":
        frais["frais_test"] = Frais(id="frais_test")
    elif anomalie == "autre_frais":
        frais["frais_autre"] = Frais(id="frais_autre", justificatifs=["just_test"])
    else:
        copie = pieces["just_test"].model_copy(update={"id": "just_autre"})
        pieces[copie.id] = copie
    avant = instantane(racine)
    with pytest.raises(RecuperationRefusee):
        recuperer_piece(racine, "just_test", appliquer=True)
    assert not cible.exists() and instantane(racine) == avant


def test_symlink_source_et_destination_refuses(cas):
    racine, cible, quarantaine, _, _ = cas
    secret = racine / "secret"
    secret.write_bytes(b"preuve")
    quarantaine.unlink()
    quarantaine.symlink_to(secret)
    with pytest.raises(RecuperationRefusee, match="symbolique"):
        recuperer_piece(racine, "just_test", appliquer=True)
    quarantaine.unlink()
    quarantaine.write_bytes(b"preuve")
    cible.symlink_to(racine / "cible_absente")
    with pytest.raises(RecuperationRefusee, match="déjà présente"):
        recuperer_piece(racine, "just_test", appliquer=True)
    assert secret.read_bytes() == b"preuve" and cible.is_symlink()


def test_course_publication_necrase_pas(cas, monkeypatch):
    from unocr import justificatifs_recovery

    racine, cible, quarantaine, _, _ = cas
    def course(source, destination):
        destination.write_bytes(b"autre fichier")
        raise FileExistsError("publication concurrente")
    monkeypatch.setattr(justificatifs_recovery.os, "link", course)
    with pytest.raises(RecuperationRefusee, match="apparue"):
        recuperer_piece(racine, "just_test", appliquer=True)
    assert cible.read_bytes() == b"autre fichier"
    assert quarantaine.read_bytes() == b"preuve"
    assert list(cible.parent.glob(".restore-*.tmp")) == []


def test_erreur_publication_pas_de_faux_succes(cas, monkeypatch):
    from unocr import justificatifs_recovery

    racine, cible, quarantaine, _, _ = cas
    def panne(*args):
        raise OSError("disque indisponible")
    monkeypatch.setattr(justificatifs_recovery.os, "link", panne)
    with pytest.raises(RecuperationRefusee):
        recuperer_piece(racine, "just_test", appliquer=True)
    assert not cible.exists() and quarantaine.read_bytes() == b"preuve"
    assert list(cible.parent.glob(".restore-*.tmp")) == []


def test_cli_plan_application_et_refus(cas, capsys):
    racine, cible, _, _, _ = cas
    args = ["pieces-recover", "just_test", "--data-dir", str(racine), "--json"]
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)["etat"] == "pret"
    assert not cible.exists()
    assert main(args + ["--apply"]) == 0
    assert json.loads(capsys.readouterr().out)["etat"] == "restaure"
    assert main(args + ["--apply"]) == 2
    assert json.loads(capsys.readouterr().out)["etat"] == "refuse"


def test_magasin_absent_ne_cree_rien(tmp_path):
    absent = tmp_path / "absent"
    with pytest.raises(RecuperationRefusee):
        recuperer_piece(absent, "just_test", appliquer=True)
    assert not absent.exists()


def test_residu_de_nettoyage_signale(cas, monkeypatch):
    from pathlib import Path

    racine, cible, _, _, _ = cas
    original = Path.unlink
    def echec_temp(self, *args, **kwargs):
        if self.name.startswith(".restore-"):
            raise PermissionError("nettoyage refusé")
        return original(self, *args, **kwargs)
    monkeypatch.setattr(Path, "unlink", echec_temp)
    rapport = recuperer_piece(racine, "just_test", appliquer=True)
    assert rapport["etat"] == "restaure"
    assert rapport["residu_temporaire"].startswith("justificatifs/.restore-")
    assert cible.read_bytes() == b"preuve"
