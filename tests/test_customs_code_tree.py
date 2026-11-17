"""Chemins déclarés de fixtures NON OFFICIELLES, pas hiérarchie juridique reconstituée."""
import json

import pytest

from tests import test_customs_review
from tests.test_customs_legal import fichiers_code
from tests.test_customs_reference import snapshot
from unocr.cli import main
from unocr.customs_reference.code_tree import ParamArbreCodeInvalide, parcourir_code
from unocr.customs_reference.legal_importer import preparer_code
from unocr.customs_reference.review_export import analyser_export
from unocr.logging_setup import AuditIndisponible

revue = test_customs_review.revue
ADMIN, BASE = test_customs_review.ADMIN, test_customs_review.BASE


def path(*couples):
    return [{"niveau": n, "identifiant": i} for n, i in couples]


def arbre(lot, source=None, chemin=None, **kwargs):
    return parcourir_code(lot, source, json.dumps(chemin or []), **kwargs)


def preparer(root):
    t, m = fichiers_code(root)
    objet = json.loads(t.read_text())
    a = objet["articles"][0]
    a["hierarchie"] = [{**n, "intitule":"Titre NON OFFICIEL A"} for n in path(("texte_legislatif", "TEST_O"), ("titre", "I"), ("article", "5 bis"))]
    b = {**a, "id":"TEST_O_B", "numero_article":"6", "hierarchie":[a["hierarchie"][0], {**a["hierarchie"][1], "intitule":"عنوان غير رسمي"}, {"niveau":"article", "identifiant":"6"}]}
    c = {**a, "id":"TEST_O_C", "numero_article":"8", "hierarchie":path(("texte_legislatif", "TEST_O"), ("article", "8"))}
    objet["articles"] += [b, c]
    t.write_text(json.dumps(objet))
    lot = root / "lot"
    preparer_code(t, m, lot)
    return lot


def test_sources_separees_absences_et_corpus_inchange(tmp_path):
    lot = preparer(tmp_path)
    avant = snapshot(lot)
    racine = arbre(lot)
    assert [v["source_id"] for v in racine["enfants_declares"]] == ["TEST_C", "TEST_M", "TEST_O"]
    assert racine["enfants_declares"][-1]["nombre_versions_transcrites"] == 3
    doc = arbre(lot, "TEST_O", path(("texte_legislatif", "TEST_O")))
    assert [v["type_noeud"] for v in doc["enfants_declares"]] == ["niveau_declare", "niveau_declare"]
    n = doc["enfants_declares"][0]
    assert n["chemin"] == path(("texte_legislatif", "TEST_O"), ("titre", "I"))  # Ni livre ni chapitre inventés.
    assert len(n["intitules_declares"]) == 2 and n["nombre_versions_transcrites"] == 2
    assert doc["enfants_declares"][1]["chemin"][-1] == {"niveau":"article", "identifiant":"8"}
    feuille = arbre(lot, "TEST_O", path(("texte_legislatif", "TEST_O"), ("titre", "I"), ("article", "5 bis")))
    assert feuille["enfants_declares"][0]["version_declaree"]["reference"]["source_id"] == "TEST_O"
    assert arbre(lot, "TEST_M", path(("titre", "I")))["parent_trouve"] is False
    assert arbre(lot, "INCONNU")["parent_trouve"] is False
    assert arbre(lot, "TEST_O", path(("titre", "i")))["total_enfants_declares"] == 0
    assert snapshot(lot) == avant


def test_pagination_et_hors_fin(tmp_path):
    lot = preparer(tmp_path)
    rep = arbre(lot, limite=1, decalage=1)
    assert rep["enfants_declares"][0]["source_id"] == "TEST_M" and rep["decalage_suivant"] == 2
    assert arbre(lot, limite=1, decalage=3)["decalage_suivant"] is None
    assert arbre(lot, "TEST_O", path(("texte_legislatif", "TEST_O")), limite=1)["decalage_suivant"] == 1


@pytest.mark.parametrize("kwargs", [
    {"source_id":""}, {"source_id":"A\n"}, {"source_id":False}, {"source_id":"x"*257},
    {"source_id":"S", "chemin":'[ {"niveau":"titre","identifiant":"\\ud800"} ]'},
    {"chemin":"{"}, {"chemin":"null"}, {"chemin":"{}"}, {"chemin":"x"*8193},
    {"source_id":"S", "chemin":'[{"niveau":"titre","niveau":"article","identifiant":"1"}]'},
    {"source_id":"S", "chemin":'[{"niveau":"titre","identifiant":1}]'},
    {"chemin":json.dumps(path(("titre","I")))},
    {"source_id":"S", "chemin":json.dumps(path(("article","1"),("titre","I")))},
    {"source_id":"S", "chemin":json.dumps(path(("titre","I"),("titre","II")))},
    {"limite":True}, {"limite":101}, {"limite":0}, {"decalage":-1}, {"decalage":True}, {"decalage":1000001},
])
def test_parametres_avant_lecture(tmp_path, kwargs):
    with pytest.raises(ParamArbreCodeInvalide):
        parcourir_code(tmp_path / "absent", **kwargs)


def test_cli(tmp_path, capsys):
    lot = preparer(tmp_path)
    assert main(["customs-code-tree", str(lot), "--source", "TEST_O", "--path", json.dumps(path(("texte_legislatif","TEST_O"), ("titre","I")))]) == 0
    assert json.loads(capsys.readouterr().out)["total_enfants_declares"] == 2


def test_api_export_et_audit(revue, monkeypatch):
    from unocr import api
    client, racine, registre, cfg = revue
    avant = snapshot(racine)
    url = BASE + "/lots/code_a/code-tree?source_id=TEST_O"
    rep = client.get(url, headers=ADMIN)
    assert rep.status_code == 200 and rep.headers["cache-control"] == "no-store"
    assert rep.json()["resultat"]["document_declare"]["sha256"]
    export = {"schema_version":"1", "type_export":"rapport_revue_documentaire_non_valide", "lecture_seule":True,
              "publication_active":False,"validation_juridique":"non_validee",
              "perimetre":"rapport_ou_page_uniquement_pas_corpus_complet", "horodatage_client_non_certifie":"2026-11-06T12:30:45.123Z",
              "requete_relative":url, "resultat":rep.json()["resultat"]}
    assert analyser_export(json.dumps(export).encode())["statut"] == "structure_compatible"
    evenements = [json.loads(ligne) for ligne in (cfg.log_dir / "audit.log").read_text().splitlines()]
    assert any(e.get("operation") == "navigation_code" and e.get("manifestes", {}).keys() == {"code_a"} for e in evenements)
    def panne(*a, **kw):
        raise AuditIndisponible("SECRET_TEST")
    monkeypatch.setattr(api, "audit_obligatoire", panne)
    assert client.get(url, headers=ADMIN).status_code == 503
    assert snapshot(racine) == avant


@pytest.mark.parametrize("lot,headers,params,statut", [
    ("code_a", {}, {}, 401), ("tarif_a", ADMIN, {}, 422),
    ("code_a", ADMIN, {"path":"INVALIDE"},422), ("code_a", ADMIN, {"limit":101},422),
])
def test_refus_api(revue, lot, headers, params, statut):
    client, *_ = revue
    assert client.get(BASE + f"/lots/{lot}/code-tree", headers=headers, params=params).status_code == statut


def test_documents_sans_transcription_et_tous_niveaux_declares(tmp_path):
    t, m = fichiers_code(tmp_path)
    objet = json.loads(t.read_text())
    objet["articles"][0]["hierarchie"] = path(("texte_legislatif","T"), ("livre","L"), ("titre","I"),
        ("chapitre","C"), ("section","S"), ("sous_section","SS"), ("article","5 bis"),
        ("paragraphe","P"), ("alinea","أ"), ("annexe","A"))
    t.write_text(json.dumps(objet))
    lot = tmp_path / "lot"
    preparer_code(t, m, lot)
    chemin = []
    for n in objet["articles"][0]["hierarchie"]:
        rep = arbre(lot, "TEST_O", chemin)
        assert rep["enfants_declares"][0]["chemin"] == [*chemin, n]
        chemin.append(n)
    assert arbre(lot,"TEST_O",chemin)["enfants_declares"][0]["version_declaree"]["id"] == "TEST_O_A"
    t.write_text('{"articles":[],"relations":[]}')
    vide = tmp_path / "vide"
    preparer_code(t,m,vide)
    assert len(arbre(vide)["enfants_declares"]) == 3
    assert arbre(vide,"TEST_O")["parent_trouve"] is True
    assert arbre(vide,"TEST_O")["total_enfants_declares"] == 0


def test_meme_chemin_dans_sources_distinctes_non_fusionne(tmp_path):
    t,m = fichiers_code(tmp_path)
    donnees = json.loads(t.read_text())
    a,b = donnees["articles"][:2]
    b["hierarchie"] = a["hierarchie"]
    b["numero_article"] = a["numero_article"]
    t.write_text(json.dumps(donnees))
    lot = tmp_path / "lot"
    preparer_code(t,m,lot)
    for source, identifiant in (("TEST_O","TEST_O_A"),("TEST_M","TEST_M_A")):
        rep = arbre(lot,source,a["hierarchie"])
        assert [v["version_declaree"]["id"] for v in rep["enfants_declares"]] == [identifiant]
