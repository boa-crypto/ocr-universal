"""Inventaire de fixtures NON OFFICIELLES uniquement, sans acquisition réseau."""
import copy
import json

import pytest

from tests import test_customs_review
from tests.test_customs_legal import fichiers_code
from tests.test_customs_reference import snapshot
from tests.test_customs_review import ADMIN, BASE
from tests.test_customs_search import lot_tarif
from unocr.cli import main
from unocr.customs_reference.legal_importer import preparer_code
from unocr.customs_reference.review_export import analyser_export
from unocr.customs_reference.search import ParamRechercheInvalide
from unocr.customs_reference.source_catalog import inventorier_sources
from unocr.logging_setup import AuditIndisponible

revue = test_customs_review.revue


def preparer(root):
    transcription,metadata = fichiers_code(root)
    meta = json.loads(metadata.read_text())
    meta["documents"][0]["document"]["titre"] = "Équipement مُعَـدَّات NON OFFICIEL"
    copie = copy.deepcopy(meta["documents"][0])
    copie["document"]["id"] = "TEST_DUP"
    (root / "COPIE_NON_OFFICIELLE.pdf").write_bytes((root / copie["fichier_recu"]).read_bytes())
    copie["fichier_recu"] = "COPIE_NON_OFFICIELLE.pdf"
    meta["documents"].append(copie)
    metadata.write_text(json.dumps(meta))
    brut = json.loads(transcription.read_text())
    brut["articles"][0]["historique_modifications"] = [{"source_id":"TEST_M","localisateur":"TEST NON OFFICIEL"}]*2
    transcription.write_text(json.dumps(brut))
    lot = root / "lot"
    preparer_code(transcription,metadata,lot)
    return lot


def test_catalogue_sources_types_compteurs_doublons_et_non_mutation(tmp_path):
    lot = preparer(tmp_path)
    avant = snapshot(tmp_path)
    rep = inventorier_sources(lot,"code")
    assert rep["total_sources_lot"] == rep["total_correspondances"] == 4
    assert [r["source_declaree"]["id"] for r in rep["resultats"]] == ["TEST_C","TEST_DUP","TEST_M","TEST_O"]
    par_id = {r["source_declaree"]["id"]:r for r in rep["resultats"]}
    assert par_id["TEST_M"]["compteurs_lot"] == {"articles_reference_principale":1,"articles_historique_declare":1,"relations_reference_preuve":1}
    assert par_id["TEST_DUP"]["compteurs_lot"]["articles_reference_principale"] == 0
    assert par_id["TEST_DUP"]["autres_sources_meme_sha256_dans_lot"] == ["TEST_O"]
    assert par_id["TEST_O"]["autres_sources_meme_sha256_dans_lot"] == ["TEST_DUP"]
    assert rep["authenticite_etablie"] is rep["utilisable_pour_calcul_douanier"] is False
    assert rep["publication_active"] is False and rep["validation_juridique"] == "non_validee"
    assert snapshot(tmp_path) == avant


def test_recherche_fr_ar_filtres_et_pagination(tmp_path):
    lot = preparer(tmp_path)
    rep = inventorier_sources(lot,"code","EQUIPEMENT معدات",limite=1)
    assert rep["total_correspondances"] == 2 and rep["decalage_suivant"] == 1
    assert rep["resultats"][0]["champs_correspondants"] == {"equipement":["titre"],"معدات":["titre"]}
    assert inventorier_sources(lot,"code","equipement",source_id="TEST_O",nature_document="code_original")["total_correspondances"] == 1
    assert inventorier_sources(lot,"code",source_id="TEST_O",nature_document="compilation")["total_correspondances"] == 0
    assert inventorier_sources(lot,"code",source_id="test_o")["total_correspondances"] == 0
    assert inventorier_sources(lot,"code",decalage=99)["resultats"] == []
    assert inventorier_sources(lot,"code","www.joradp.dz")["total_correspondances"] == 0
    assert inventorier_sources(lot,"code","TEST_O")["total_correspondances"] == 4  # Sous-chaînes normalisées « test » et « o », pas ID exact.


def test_tarif_source_unique_sans_nature_inventee(tmp_path):
    lot = lot_tarif(tmp_path)
    rep = inventorier_sources(lot,"tarif")
    assert rep["total_sources_lot"] == rep["total_correspondances"] == 1
    r = rep["resultats"][0]
    assert "nature_document" not in r["source_declaree"]
    assert r["compteurs_lot"]["lignes"] == 5 and r["compteurs_lot"]["mesures"] == 1
    assert r["autres_sources_meme_sha256_dans_lot"] == []


@pytest.mark.parametrize("kwargs",[{"type_lot":"autre"},{"type_lot":True},{"source_id":" "},{"source_id":True},
    {"source_id":"X"*257},{"source_id":"A\x00"},{"source_id":"A\ud800"},{"nature_document":"originale"},
    {"nature_document":True},{"type_lot":"tarif","nature_document":"code_original"},{"requete":"!!!"},
    {"requete":"x"*257},{"requete":"a\ud800"},{"requete":"a\x00"},{"limite":True},{"limite":0},
    {"limite":101},{"decalage":-1},{"decalage":1000001},{"decalage":True}])
def test_parametres_avant_lecture(tmp_path,kwargs):
    params = {"type_lot":"code",**kwargs}
    with pytest.raises(ParamRechercheInvalide):
        inventorier_sources(tmp_path / "absent",**params)


def test_cli(tmp_path,capsys):
    lot = preparer(tmp_path)
    assert main(["customs-sources",str(lot),"--type","code","--nature","acte_modificatif"]) == 0
    assert json.loads(capsys.readouterr().out)["resultats"][0]["source_declaree"]["id"] == "TEST_M"


def test_api_export_audit_et_503(revue,monkeypatch):
    from unocr import api
    client,racine,registre,cfg = revue
    avant = snapshot(racine)
    url = BASE + "/lots/code_a/sources?source_id=TEST_M&nature_document=acte_modificatif"
    r = client.get(url,headers=ADMIN)
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    rep = r.json()["resultat"]
    assert rep["resultats"][0]["source_declaree"]["id"] == "TEST_M"
    events = [json.loads(ligne) for ligne in (cfg.log_dir / "audit.log").read_text().splitlines()]
    assert [e for e in events if e.get("operation") == "inventaire_sources"][-1]["manifestes"].keys() == {"code_a"}
    export = {"schema_version":"1","type_export":"rapport_revue_documentaire_non_valide","lecture_seule":True,
        "publication_active":False,"validation_juridique":"non_validee","perimetre":"rapport_ou_page_uniquement_pas_corpus_complet",
        "horodatage_client_non_certifie":"2026-11-07T10:00:00.000Z","requete_relative":url,"resultat":rep}
    assert analyser_export(json.dumps(export).encode())["statut"] == "structure_compatible"
    def panne(*a,**kw):
        raise AuditIndisponible("SECRET_TEST")
    monkeypatch.setattr(api,"audit_obligatoire",panne)
    r = client.get(url,headers=ADMIN)
    assert r.status_code == 503 and "resultat" not in r.json()
    assert snapshot(racine) == avant


@pytest.mark.parametrize("route,headers,statut",[
    ("code_a/sources",{},401),("code_a/sources",{"Authorization":"Bearer TEST_LECTEUR_NON_PRODUCTION"},403),
    ("code_a/sources?nature_document=inconnu",ADMIN,422),("tarif_a/sources?nature_document=compilation",ADMIN,422),
    ("code_a/sources?limit=0",ADMIN,422),("absent/sources",ADMIN,404)])
def test_refus_api(revue,route,headers,statut):
    client,*_ = revue
    assert client.get(BASE + "/lots/"+route,headers=headers).status_code == statut


@pytest.mark.parametrize("moment",["avant","apres"])
def test_epingle_et_recontrole_resultat(revue,monkeypatch,moment):
    import unocr.routes.customs_review as routes
    client,racine,*_ = revue
    manifeste = racine / "code_a" / "manifest.json"
    if moment == "avant":
        manifeste.write_bytes(manifeste.read_bytes()+b" ")
    else:
        original = routes.inventorier_sources
        def changer(*a,**kw):
            rep = original(*a,**kw)
            rep["archive"]["manifest_sha256"] = "0"*64
            return rep
        monkeypatch.setattr(routes,"inventorier_sources",changer)
    r = client.get(BASE + "/lots/code_a/sources",headers=ADMIN)
    assert r.status_code == 409 and "resultat" not in r.json()


def test_sources_sans_article_ne_deviennent_pas_documents_vides(tmp_path):
    transcription,metadata = fichiers_code(tmp_path)
    transcription.write_text(json.dumps({"articles":[],"relations":[]}))
    lot = tmp_path / "lot"
    preparer_code(transcription,metadata,lot)
    rep = inventorier_sources(lot,"code")
    assert rep["total_sources_lot"] == 3
    assert all(r["compteurs_lot"]["articles_reference_principale"] == 0 for r in rep["resultats"])
    assert rep["completude_reglementaire"] == "non_etablie"


def test_api_tarif_source_declaree(revue):
    client,*_ = revue
    r = client.get(BASE + "/lots/tarif_a/sources",headers=ADMIN)
    assert r.status_code == 200
    rep = r.json()["resultat"]
    assert rep["type_lot"] == "tarif" and rep["total_sources_lot"] == 1
    assert rep["resultats"][0]["compteurs_lot"]["lignes"] == 5
