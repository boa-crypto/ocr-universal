"""Relais local isolé, sans accès aux journaux du poste."""
import json
import os

import pytest

from tests.test_pieces_receipts import creer_recu, instantane
from unocr.cli import main
from unocr.pieces_audit import relayer_suppression


@pytest.fixture
def cas(tmp_path):
    racine = tmp_path / "data"
    creer_recu(racine)
    return racine, tmp_path / "audit.log"


def test_plan_ne_cree_rien(cas):
    racine, journal = cas
    avant = instantane(racine.parent)
    assert relayer_suppression(racine, "just_test", journal)["etat"] == "pret"
    assert instantane(racine.parent) == avant
    assert not journal.exists()


@pytest.mark.skipif(os.name != "posix", reason="Relais verrouillé POSIX")
def test_application_preserve_prefixe_base_et_reprise(cas):
    racine, journal = cas
    prefixe = b'{"event":"autre","cible":"autre"}\n'
    journal.write_bytes(prefixe)
    base = instantane(racine)
    assert relayer_suppression(racine, "just_test", journal, True)["etat"] == "reporte"
    assert journal.read_bytes().startswith(prefixe)
    objets = [json.loads(ligne) for ligne in journal.read_bytes().splitlines()]
    assert len(objets) == 2
    assert objets[1]["recu_id"] == "suppression_justificatif:just_test"
    assert objets[1]["hash_sha256"] == "a" * 64
    assert instantane(racine) == base
    avant = journal.read_bytes()
    assert relayer_suppression(racine, "just_test", journal, True)["etat"] == "deja_present"
    assert journal.read_bytes() == avant


@pytest.mark.parametrize("contenu", [b'{"event":', b'{}', b'pas json\n', b'[]\n', b'{"a":1,"a":2}\n', b'{"a":NaN}\n', b'\xff\n'])
def test_journal_invalide_intact(cas, contenu):
    racine, journal = cas
    journal.write_bytes(contenu)
    avant = instantane(racine.parent)
    for appliquer in (False, True):
        assert relayer_suppression(racine, "just_test", journal, appliquer)["etat"] == "refuse"
    assert instantane(racine.parent) == avant


def test_evenement_historique_pas_de_duplication(cas):
    racine, journal = cas
    journal.write_text('{"event":"justificatif_supprime","cible":"just_test"}\n')
    avant = journal.read_bytes()
    assert relayer_suppression(racine, "just_test", journal)["etat"] == "deja_present"
    assert relayer_suppression(racine, "just_test", journal, True)["etat"] == "deja_present"
    assert journal.read_bytes() == avant


@pytest.mark.parametrize("mode", ["base", "symlink", "parent_absent", "parent_symlink", "repertoire", "fifo"])
def test_cible_refusee(cas, mode):
    racine, journal = cas
    if mode == "base":
        journal = racine / "metier.sqlite3"
    elif mode == "symlink":
        journal.symlink_to(racine / "metier.sqlite3")
    elif mode == "parent_absent":
        journal = journal.parent / "absent/audit.log"
    elif mode == "parent_symlink":
        dossier = journal.parent / "lien"
        dossier.symlink_to(racine, target_is_directory=True)
        journal = dossier / "audit.log"
    elif mode == "repertoire":
        journal.mkdir()
    elif mode == "fifo":
        if os.name != "posix":
            pytest.skip("FIFO POSIX")
        os.mkfifo(journal)
    # Ne pas prendre d'instantané des FIFO (bloquant).
    base = instantane(racine)
    for appliquer in (False, True):
        assert relayer_suppression(racine, "just_test", journal, appliquer)["etat"] == "refuse"
    assert instantane(racine) == base


def test_recu_absent_aucun_journal(cas):
    racine, journal = cas
    assert relayer_suppression(racine, "inconnu", journal, True)["etat"] == "refuse"
    assert not journal.exists()


@pytest.mark.parametrize("champ,valeur", [("frais", "autre"), ("recu_id", "autre"), ("ts", 0)])
def test_conflit_necrit_pas(cas, champ, valeur):
    racine, journal = cas
    assert relayer_suppression(racine, "just_test", journal, True)["etat"] == "reporte"
    objet = json.loads(journal.read_text())
    objet[champ] = valeur
    journal.write_text(json.dumps(objet) + "\n")
    avant = journal.read_bytes()
    assert relayer_suppression(racine, "just_test", journal, True)["etat"] == "refuse"
    assert journal.read_bytes() == avant


def test_application_revalide_plan(cas):
    racine, journal = cas
    assert relayer_suppression(racine, "just_test", journal)["etat"] == "pret"
    journal.write_bytes(b"incomplet")
    assert relayer_suppression(racine, "just_test", journal, True)["etat"] == "refuse"
    assert journal.read_bytes() == b"incomplet"


@pytest.mark.parametrize("panne", ["partielle", "fsync"])
def test_panne_apres_tentative_pas_de_faux_succes(cas, monkeypatch, panne):
    from unocr import pieces_audit

    racine, journal = cas
    original = os.write
    def ecriture(fd, contenu):
        original(fd, contenu[:5])
        raise OSError("panne écriture")
    def fsync(fd):
        raise OSError("synchronisation impossible")
    monkeypatch.setattr(pieces_audit.os, "write" if panne == "partielle" else "fsync", ecriture if panne == "partielle" else fsync)
    rapport = relayer_suppression(racine, "just_test", journal, True)
    assert rapport["etat"] == "indetermine" and rapport["applique"] is None
    assert "possiblement effectuée" in rapport["detail"]
    assert journal.stat().st_size > 0
    monkeypatch.undo()
    avant = journal.read_bytes()
    assert relayer_suppression(racine, "just_test", journal, True)["etat"] == ("refuse" if panne == "partielle" else "deja_present")
    assert journal.read_bytes() == avant


def test_cli_plan_application_et_refus(cas, capsys):
    racine, journal = cas
    args = ["pieces-audit", "just_test", "--data-dir", str(racine), "--audit-file", str(journal), "--json"]
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)["etat"] == "pret"
    assert not journal.exists()
    assert main(args + ["--apply"]) == 0
    assert json.loads(capsys.readouterr().out)["etat"] == "reporte"
    journal.write_bytes(b"incomplet")
    assert main(args + ["--apply"]) == 2
    assert json.loads(capsys.readouterr().out)["etat"] == "refuse"


def test_verrou_occupe_refus_sans_attente(cas):
    fcntl = pytest.importorskip("fcntl")
    racine, journal = cas
    journal.write_bytes(b"{}\n")
    with journal.open("rb") as fichier:
        fcntl.flock(fichier.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert relayer_suppression(racine, "just_test", journal, True)["etat"] == "refuse"
    assert journal.read_bytes() == b"{}\n"


@pytest.mark.parametrize("limite", ["MAX_JOURNAL", "MAX_LIGNE"])
def test_limites_pas_de_mutation(cas, monkeypatch, limite):
    from unocr import pieces_audit

    racine, journal = cas
    journal.write_bytes(b"{}\n")
    monkeypatch.setattr(pieces_audit, limite, 2)
    avant = instantane(racine.parent)
    assert relayer_suppression(racine, "just_test", journal, True)["etat"] == "refuse"
    assert instantane(racine.parent) == avant


def test_ecritures_courtes_completees(cas, monkeypatch):
    from unocr import pieces_audit

    racine, journal = cas
    original = os.write
    monkeypatch.setattr(pieces_audit.os, "write", lambda fd, contenu: original(fd, contenu[:3]))
    assert relayer_suppression(racine, "just_test", journal, True)["etat"] == "reporte"
    assert json.loads(journal.read_text())["cible"] == "just_test"
    assert relayer_suppression(racine, "just_test", journal, True)["etat"] == "deja_present"


@pytest.mark.parametrize("phase", ["avant_ecriture", "ecriture_partielle", "apres_ecriture", "apres_fsync"])
def test_sigkill_relais_reprise_sans_faux_succes(cas, tmp_path_factory, phase):
    from tests._crash_isole import tuer_a_barriere
    from unocr.pieces_receipts import consulter_suppression

    fcntl = pytest.importorskip("fcntl")
    racine, journal = cas
    prefixe = b'{"event":"autre","cible":"ancienne"}\n'
    journal.write_bytes(prefixe)
    base_avant = instantane(racine)
    recu_avant = consulter_suppression(racine, "just_test")
    marqueur = tmp_path_factory.mktemp("barriere_relais") / "pret"
    tuer_a_barriere("_pieces_audit_crash_worker.py", racine, marqueur, phase, str(journal))
    assert instantane(racine) == base_avant
    assert consulter_suppression(racine, "just_test") == recu_avant
    apres_crash = journal.read_bytes()
    assert apres_crash.startswith(prefixe)
    # Le noyau doit avoir libéré flock malgré l'absence de finally dans l'enfant.
    with journal.open("rb") as fichier:
        fcntl.flock(fichier.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(fichier.fileno(), fcntl.LOCK_UN)

    if phase == "avant_ecriture":
        assert apres_crash == prefixe
        etat_plan, etat_reprise = "pret", "reporte"
    elif phase == "ecriture_partielle":
        assert len(apres_crash) == len(prefixe) + 5
        assert not apres_crash.endswith(b"\n")
        etat_plan = etat_reprise = "refuse"
    else:
        lignes = apres_crash.splitlines()
        assert len(lignes) == 2 and apres_crash.endswith(b"\n")
        objet = json.loads(lignes[1])
        assert objet["recu_id"] == "suppression_justificatif:just_test"
        assert objet["hash_sha256"] == recu_avant["recu"]["hash_sha256"]
        assert objet["frais"] == recu_avant["recu"]["frais_id"]
        etat_plan = etat_reprise = "deja_present"
    avant_plan = instantane(racine.parent)
    assert relayer_suppression(racine, "just_test", journal)["etat"] == etat_plan
    assert instantane(racine.parent) == avant_plan
    assert relayer_suppression(racine, "just_test", journal, True)["etat"] == etat_reprise
    if phase == "avant_ecriture":
        assert len(journal.read_bytes().splitlines()) == 2
        assert relayer_suppression(racine, "just_test", journal, True)["etat"] == "deja_present"
    else:
        assert journal.read_bytes() == apres_crash
    assert instantane(racine) == base_avant
    assert consulter_suppression(racine, "just_test") == recu_avant
