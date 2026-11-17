"""Audit local obligatoire de succès, tests isolés NON OFFICIELS."""
import json
import os
from concurrent.futures import ThreadPoolExecutor

import pytest

from tests import test_customs_review
from tests.test_customs_reference import snapshot
from unocr import logging_setup
from unocr.logging_setup import AuditIndisponible, audit_obligatoire

revue = test_customs_review.revue
ADMIN, BASE = test_customs_review.ADMIN, test_customs_review.BASE


def test_append_synchronise_sans_effacer_prefixe(tmp_path, monkeypatch):
    dossier = tmp_path / "logs"
    dossier.mkdir()
    chemin = dossier / "audit.log"
    prefixe = b'{"event":"historique_legacy"}\n'
    chemin.write_bytes(prefixe)
    synchronisations = []
    reel = os.fsync
    def synchroniser(fd):
        synchronisations.append(fd)
        reel(fd)
    monkeypatch.setattr(logging_setup.os, "fsync", synchroniser)
    audit_obligatoire(dossier, "revue_douaniere", acteur="TEST", lots=["lot"], statut=200)
    assert chemin.read_bytes().startswith(prefixe)
    assert len(synchronisations) == 1
    assert json.loads(chemin.read_text().splitlines()[1])["acteur"] == "TEST"


def test_nouveaux_fichiers_permissions_et_evenements_concurrents(tmp_path):
    dossier = tmp_path / "logs"
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(lambda i: audit_obligatoire(dossier, "TEST", numero=i), range(30)))
    valeurs = [json.loads(v) for v in (dossier / "audit.log").read_text().splitlines()]
    assert sorted(v["numero"] for v in valeurs) == list(range(30))
    if os.name == "posix":
        assert dossier.stat().st_mode & 0o777 == 0o700
        assert (dossier / "audit.log").stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("defaut", ["repertoire_symlink", "fichier_symlink", "hardlink", "repertoire", "fin_partielle", "fifo"])
def test_cibles_refusees_sans_reparation(tmp_path, defaut):
    dossier = tmp_path / "logs"
    dossier.mkdir()
    chemin = dossier / "audit.log"
    cible = tmp_path / "cible"
    cible.write_bytes(b"NE PAS MODIFIER\n")
    if defaut == "repertoire_symlink":
        dossier.rmdir()
        dossier.symlink_to(tmp_path, target_is_directory=True)
    elif defaut == "fichier_symlink":
        chemin.symlink_to(cible)
    elif defaut == "hardlink":
        os.link(cible, chemin)
    elif defaut == "repertoire":
        chemin.mkdir()
    elif defaut == "fin_partielle":
        chemin.write_bytes(b'{"incomplet":')
    elif defaut == "fifo":
        if not hasattr(os, "mkfifo"):
            pytest.skip("FIFO POSIX requis")
        os.mkfifo(chemin)
    with pytest.raises(AuditIndisponible):
        audit_obligatoire(dossier, "TEST")
    assert cible.read_bytes() == b"NE PAS MODIFIER\n"
    if defaut == "fin_partielle":
        assert chemin.read_bytes() == b'{"incomplet":'


@pytest.mark.parametrize("operation", ["open", "write", "fsync"])
def test_erreurs_os_remontees(tmp_path, monkeypatch, operation):
    def refuser(*args):
        raise OSError("CHEMIN_INTERNE_TEST_NE_PAS_EXPOSER")
    monkeypatch.setattr(logging_setup.os, operation, refuser)
    with pytest.raises(AuditIndisponible, match="Journal de revue indisponible"):
        audit_obligatoire(tmp_path / "logs", "TEST")


def test_ecriture_partielle_conservee_et_refusee_ensuite(tmp_path, monkeypatch):
    reel = os.write
    with monkeypatch.context() as m:
        m.setattr(logging_setup.os, "write", lambda fd, contenu: reel(fd, contenu[:7]))
        with pytest.raises(AuditIndisponible):
            audit_obligatoire(tmp_path / "logs", "TEST")
    chemin = tmp_path / "logs/audit.log"
    avant = chemin.read_bytes()
    assert len(avant) == 7
    with pytest.raises(AuditIndisponible):
        audit_obligatoire(tmp_path / "logs", "TEST")
    assert chemin.read_bytes() == avant


@pytest.mark.parametrize("valeur", [float("nan"), object(), "x" * 17000])
def test_evenements_invalides_sans_creation(tmp_path, valeur):
    with pytest.raises(AuditIndisponible):
        audit_obligatoire(tmp_path / "logs", "TEST", valeur=valeur)
    assert not (tmp_path / "logs").exists()


ENDPOINTS = ["/lots", "/lots/code_a/check", "/lots/code_a/search?article=5%20bis",
             "/lots/code_a/history?article=5%20bis", "/lots/tarif_a/tariff/0101000000",
             "/lots/tarif_a/tree", "/lots/code_a/coverage", "/lots/code_a/article?article_id=TEST_O_A",
             "/diff?avant=tarif_a&apres=tarif_b"]


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_succes_bloque_si_audit_indisponible(revue, monkeypatch, endpoint):
    from unocr import api
    client, racine, registre, cfg = revue
    avant = snapshot(racine)
    def refuser(*args, **kwargs):
        raise AuditIndisponible("CHEMIN_INTERNE_TEST_NE_PAS_EXPOSER")
    monkeypatch.setattr(api, "audit_obligatoire", refuser)
    r = client.get(BASE + endpoint, headers=ADMIN)
    assert r.status_code == 503
    assert r.headers["cache-control"] == "no-store"
    assert r.json()["detail"]["code"] == "audit_revue_indisponible"
    assert "resultat" not in r.json() and "CHEMIN_INTERNE" not in r.text
    assert snapshot(racine) == avant


def test_evenement_succes_contient_epingles_pas_requete_texte_jeton(revue):
    client, racine, registre, cfg = revue
    assert client.get(BASE + "/lots/code_a/search?q=CONFIDENTIEL_TEST", headers=ADMIN).status_code == 200
    evenement = [json.loads(v) for v in (cfg.log_dir / "audit.log").read_text().splitlines()
                 if json.loads(v)["event"] == "revue_douaniere"][-1]
    attendu = next(v["manifest_sha256"] for v in json.loads(registre.read_text())["lots"] if v["id"] == "code_a")
    assert evenement["manifestes"] == {"code_a": attendu}
    assert evenement["statut"] == 200
    texte = json.dumps(evenement)
    assert "CONFIDENTIEL_TEST" not in texte and "TEST_ADMIN_NON_PRODUCTION" not in texte
    assert "NON OFFICIELLE" not in texte


def test_refus_preserves_si_audit_en_panne(revue, monkeypatch):
    from unocr import api
    client, racine, registre, cfg = revue
    def refuser(*args, **kwargs):
        raise AuditIndisponible("PANNE TEST")
    monkeypatch.setattr(api, "audit_obligatoire", refuser)
    assert client.get(BASE + "/lots/inconnu/check", headers=ADMIN).status_code == 404
    assert client.get(BASE + "/lots/code_a/history?article=%20", headers=ADMIN).status_code == 422
    brut = json.loads(registre.read_text())
    brut["reviseurs"] = []
    registre.write_text(json.dumps(brut))
    assert client.get(BASE + "/lots", headers=ADMIN).status_code == 403


def test_pas_evenement_succes_si_serialisation_reponse_echoue(revue, monkeypatch):
    from unocr.routes import customs_review
    client, racine, registre, cfg = revue
    reel = customs_review.charger_lot_code
    def resultat_non_serialisable(*args):
        lot, rapport = reel(*args)
        rapport["invalide"] = float("nan")
        return lot, rapport
    monkeypatch.setattr(customs_review, "charger_lot_code", resultat_non_serialisable)
    assert client.get(BASE + "/lots/code_a/check", headers=ADMIN).status_code == 409
    evenements = [json.loads(v) for v in (cfg.log_dir / "audit.log").read_text().splitlines()]
    assert not any(v["event"] == "revue_douaniere" and v["statut"] == 200 for v in evenements)
