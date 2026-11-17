"""Revue HTTP avec authentification réelle du middleware ; fixtures NON OFFICIELLES."""
import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from tests.test_customs_reference import snapshot
from tests.test_customs_search import lot_code, lot_tarif
from unocr import api
from unocr.customs_reference.review_registry import RegistreRevue, charger_registre
from unocr.rbac import RegistreRBAC

BASE = "/api/v1/customs-review"
ADMIN = {"Authorization": "Bearer TEST_ADMIN_NON_PRODUCTION"}


@pytest.fixture()
def revue(tmp_cfg, monkeypatch):
    utilisateurs = [{"nom": "admin-test", "roles": ["administrateur"], "jeton": "TEST_ADMIN_NON_PRODUCTION"},
                    {"nom": "lecteur-test", "roles": ["lecteur"], "jeton": "TEST_LECTEUR_NON_PRODUCTION"}]
    monkeypatch.setattr(api, "_rbac", RegistreRBAC.depuis({"utilisateurs": utilisateurs}))
    monkeypatch.setattr(api, "_AUTH_TOKEN", "")
    racine = tmp_cfg.data_dir / "customs-quarantine"
    racine.mkdir()
    entrees = tmp_cfg.root / "entrees"
    entrees.mkdir()
    lots = []
    for nom, preparer, type_lot in (("tarif_a", lot_tarif, "tarif"), ("tarif_b", lot_tarif, "tarif"), ("code_a", lot_code, "code")):
        entree = entrees / nom
        entree.mkdir()
        lot = preparer(entree)
        destination = racine / nom
        import shutil
        shutil.copytree(lot, destination)
        lots.append({"id": nom, "dossier": nom, "type_lot": type_lot,
                     "manifest_sha256": hashlib.sha256((destination / "manifest.json").read_bytes()).hexdigest()})
    registre = racine / "registre.json"
    registre.write_text(json.dumps({"reviseurs": ["admin-test"], "lots": lots}))
    with TestClient(api.app) as client:
        yield client, racine, registre, tmp_cfg


def test_liste_admin_nominatif_sans_chemin_ni_fausse_validation(revue):
    client, racine, registre, cfg = revue
    avant = snapshot(racine)
    resultat = client.get(BASE + "/lots", headers=ADMIN)
    assert resultat.status_code == 200
    assert resultat.headers["cache-control"] == "no-store"
    corps = resultat.json()
    assert corps["publication_active"] is False
    assert corps["resultat"]["integrite_lots"] == "non_controlee_par_la_liste"
    assert len(corps["resultat"]["lots"]) == 3
    assert str(racine) not in resultat.text and "dossier" not in resultat.text
    assert snapshot(racine) == avant


@pytest.mark.parametrize("endpoint", ["/lots", "/lots/tarif_a/check", "/lots/code_a/search?article=5%20bis", "/diff?avant=tarif_a&apres=tarif_b"])
def test_mode_ouvert_legacy_ne_donne_aucun_acces(revue, monkeypatch, endpoint):
    client, racine, registre, cfg = revue
    monkeypatch.setattr(api, "_rbac", RegistreRBAC(actif=False))
    resultat = client.get(BASE + endpoint)
    assert resultat.status_code == 403
    assert resultat.json()["detail"]["code"] == "administrateur_nominatif_rbac_requis"
    assert "resultat" not in resultat.json()


@pytest.mark.parametrize("headers,statut", [({}, 401), ({"Authorization": "Bearer INCONNU"}, 401),
                                          ({"Authorization": "Bearer TEST_LECTEUR_NON_PRODUCTION"}, 403),
                                          ({"X-Role": "administrateur", "X-User": "admin-test"}, 401)])
def test_jetons_roles_et_entetes_non_fiables(revue, headers, statut):
    client, racine, registre, cfg = revue
    assert client.get(BASE + "/lots", headers=headers).status_code == statut


def test_passe_partout_environnement_refuse(revue, monkeypatch):
    client, racine, registre, cfg = revue
    monkeypatch.setattr(api, "_AUTH_TOKEN", "TEST_ENV_NON_PRODUCTION")
    assert client.get(BASE + "/lots", headers={"Authorization": "Bearer TEST_ENV_NON_PRODUCTION"}).status_code == 403
    assert client.get(BASE + "/lots", headers=ADMIN).status_code == 200


def test_controle_recherche_et_diff_reutilisent_services(revue):
    client, racine, registre, cfg = revue
    avant = snapshot(racine)
    for nom in ("tarif_a", "code_a"):
        resultat = client.get(f"{BASE}/lots/{nom}/check", headers=ADMIN)
        assert resultat.status_code == 200
        assert resultat.json()["resultat"]["archive"]["manifest_sha256"]
    tarif = client.get(BASE + "/lots/tarif_a/search", params={"q": "معدات", "limit": 1}, headers=ADMIN)
    assert tarif.status_code == 200
    assert tarif.json()["resultat"]["total_correspondances"] == 1
    code = client.get(BASE + "/lots/code_a/search", params={"article": "5 bis", "nature": "originale"}, headers=ADMIN)
    assert code.status_code == 200
    assert code.json()["resultat"]["resultats"][0]["validation_juridique"] == "non_validee"
    diff = client.get(BASE + "/diff", params={"avant": "tarif_a", "apres": "tarif_b"}, headers=ADMIN)
    assert diff.status_code == 200
    assert diff.json()["resultat"]["lignes"]["modifies"] == []
    meme_code = client.get(BASE + "/diff", params={"avant": "code_a", "apres": "code_a"}, headers=ADMIN)
    assert meme_code.status_code == 200
    assert meme_code.json()["resultat"]["articles"]["modifies"] == []
    assert snapshot(racine) == avant


@pytest.mark.parametrize("defaut", ["absent", "symlink", "json", "duplique", "path", "sha", "role", "doublon_id", "doublon_dossier"])
def test_registre_invalide_503_sans_divulgation(revue, defaut):
    client, racine, registre, cfg = revue
    brut = json.loads(registre.read_text())
    if defaut == "absent":
        registre.unlink()
    elif defaut == "symlink":
        copie = cfg.root / "copie.json"
        copie.write_bytes(registre.read_bytes())
        registre.unlink()
        registre.symlink_to(copie)
    elif defaut == "json":
        registre.write_text("{malforme")
    elif defaut == "duplique":
        registre.write_text('{"lots": [], "lots": []}')
    else:
        if defaut == "path":
            brut["lots"][0]["dossier"] = "../secret"
        elif defaut == "sha":
            brut["lots"][0]["manifest_sha256"] = "invalide"
        elif defaut == "role":
            brut["lots"][0]["publication_active"] = True
        elif defaut == "doublon_id":
            brut["lots"][1]["id"] = brut["lots"][0]["id"]
        else:
            brut["lots"][1]["dossier"] = brut["lots"][0]["dossier"]
        registre.write_text(json.dumps(brut))
    resultat = client.get(BASE + "/lots", headers=ADMIN)
    assert resultat.status_code == 503
    assert str(cfg.root) not in resultat.text
    assert resultat.json()["detail"]["code"] == "registre_revue_indisponible"


@pytest.mark.parametrize("defaut", ["pin", "corruption", "absent", "symlink"])
def test_lot_non_admissible_refus_409(revue, defaut):
    client, racine, registre, cfg = revue
    lot = racine / "tarif_a"
    if defaut == "pin":
        manifest = lot / "manifest.json"
        manifest.write_bytes(manifest.read_bytes() + b" ")  # cohérent localement, empreinte épinglée différente
    elif defaut == "corruption":
        (lot / "lot.json").write_text("{}")
    elif defaut == "absent":
        (lot / "source_recue.json").unlink()
    else:
        lot.rename(racine / "original")
        lot.symlink_to(racine / "original", target_is_directory=True)
    avant = snapshot(racine)
    for suffixe in ("check", "search?q=010100"):
        resultat = client.get(f"{BASE}/lots/tarif_a/{suffixe}", headers=ADMIN)
        assert resultat.status_code == 409
        assert str(cfg.root) not in resultat.text
        assert "resultat" not in resultat.json()
    assert snapshot(racine) == avant


def test_aucun_chemin_http_et_types_separes(revue):
    client, racine, registre, cfg = revue
    assert client.get(BASE + "/lots/inconnu/check", headers=ADMIN).status_code == 404
    assert client.get(BASE + "/diff", params={"avant": "tarif_a", "apres": "code_a"}, headers=ADMIN).status_code == 422
    assert client.get(BASE + "/diff", params={"avant": "../secret", "apres": "tarif_a"}, headers=ADMIN).status_code == 422
    assert client.get(BASE + "/lots/tarif_a/search", params={"q": "010100", "article": "5"}, headers=ADMIN).status_code == 422


@pytest.mark.parametrize("params", [{"q": ""}, {"q": "x", "limit": 0}, {"q": "x", "offset": -1}, {"q": "x", "nature": "validee"}])
def test_parametres_recherche_refuses_422_pas_lot_incoherent(revue, params):
    client, racine, registre, cfg = revue
    assert client.get(BASE + "/lots/code_a/search", params=params, headers=ADMIN).status_code == 422


@pytest.mark.parametrize("methode", ["post", "put", "patch", "delete"])
def test_aucune_ecriture_publication_ou_validation(revue, methode):
    client, racine, registre, cfg = revue
    avant = snapshot(racine)
    assert getattr(client, methode)(BASE + "/lots", headers=ADMIN).status_code == 405
    assert client.post(BASE + "/lots/code_a/validate", headers=ADMIN).status_code == 404
    assert snapshot(racine) == avant


def test_audit_existant_sans_jeton_ni_requete_ni_texte(revue):
    client, racine, registre, cfg = revue
    client.get(BASE + "/lots/code_a/search", params={"q": "REQUETE_CONFIDENTIELLE_TEST"}, headers=ADMIN)
    client.get(BASE + "/lots", headers={"Authorization": "Bearer TEST_LECTEUR_NON_PRODUCTION"})
    lignes = (cfg.log_dir / "audit.log").read_text()
    evenements = [json.loads(ligne) for ligne in lignes.splitlines()]
    assert any(e["event"] == "revue_douaniere" and e["acteur"] == "admin-test" for e in evenements)
    assert any(e["event"] == "revue_douaniere_acces_refuse" for e in evenements)
    assert "TEST_ADMIN_NON_PRODUCTION" not in lignes
    assert "REQUETE_CONFIDENTIELLE_TEST" not in lignes
    assert "FIXTURE NON OFFICIELLE" not in lignes


def test_registre_vide_explicite_pas_de_corpus_fabrique(revue):
    client, racine, registre, cfg = revue
    registre.write_text('{"reviseurs": ["admin-test"], "lots": []}')
    resultat = client.get(BASE + "/lots", headers=ADMIN)
    assert resultat.status_code == 200 and resultat.json()["resultat"]["lots"] == []


def test_schema_et_borne_registre(revue, monkeypatch):
    from unocr.customs_reference import review_registry
    client, racine, registre, cfg = revue
    assert len(charger_registre(registre).lots) == 3
    monkeypatch.setattr(review_registry, "MAX_REGISTRE", 1)
    assert client.get(BASE + "/lots", headers=ADMIN).status_code == 503
    from pathlib import Path
    schema = Path(__file__).resolve().parents[1] / "docs/customs/schemas/RegistreRevue.schema.json"
    assert json.loads(schema.read_text()) == RegistreRevue.model_json_schema()


def test_administrateur_non_habilite_explicitement_refuse(revue):
    client, racine, registre, cfg = revue
    brut = json.loads(registre.read_text())
    brut["reviseurs"] = []
    registre.write_text(json.dumps(brut))
    assert client.get(BASE + "/lots", headers=ADMIN).status_code == 403
    assert client.get(BASE + "/lots/code_a/check", headers=ADMIN).json()["detail"]["code"] == "reviseur_non_habilite"


def test_changement_manifest_entre_precontrole_et_rejeu_refuse(revue, monkeypatch):
    from unocr.routes import customs_review
    client, racine, registre, cfg = revue
    charger = customs_review.charger_lot
    def modifier_puis_charger(dossier):
        manifest = dossier / "manifest.json"
        manifest.write_bytes(manifest.read_bytes() + b" ")
        return charger(dossier)
    monkeypatch.setattr(customs_review, "charger_lot", modifier_puis_charger)
    resultat = client.get(BASE + "/lots/tarif_a/check", headers=ADMIN)
    assert resultat.status_code == 409 and "resultat" not in resultat.json()


@pytest.mark.parametrize("reviseurs", [["admin-test", "admin-test"], [True], [" "], ["x" * 129]])
def test_habilitations_invalides_ne_passent_pas_en_acces_ouvert(revue, reviseurs):
    client, racine, registre, cfg = revue
    brut = json.loads(registre.read_text())
    brut["reviseurs"] = reviseurs
    registre.write_text(json.dumps(brut))
    assert client.get(BASE + "/lots", headers=ADMIN).status_code == 503
