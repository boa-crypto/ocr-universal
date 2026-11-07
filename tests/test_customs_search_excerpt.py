"""Extraits de transcriptions de fixtures NON OFFICIELLES ; pas preuve PDF."""
import json
import random

import pytest

from tests import test_customs_review
from tests.test_customs_legal import fichiers_code
from tests.test_customs_reference import snapshot
from tests.test_customs_review import ADMIN, BASE
from unocr.cli import main
from unocr.customs_reference.article_detail import consulter_article
from unocr.customs_reference.legal_importer import preparer_code
from unocr.customs_reference.review_export import analyser_export
from unocr.customs_reference.search import _normaliser, rechercher_code
from unocr.customs_reference.search_excerpt import _indices_normalises, extraits_correspondants
from unocr.logging_setup import AuditIndisponible

revue = test_customs_review.revue


@pytest.mark.parametrize("texte,requete",[
    ("x "*400+"ÉQUIPEMENT NON OFFICIEL","equipement"),
    ("😀 "*300+"مُعَـدَّات اختبار غير رسمية","معدات"),
    ("abc œuvré","oeuvre"),("abc æther","aether"),("abc ﬃction","ffi"),
    ("abc ﬃction","f"),("abc Straße","ss"),("abc ＡＢＣ","abc"),
    ("abc e\u0301quipement","equipement"),("abc ﻻ","لا"),("abc ㍿","株式会社"),
    ("x ¼ y","4"),("أبجدية","ابجدية"),("Kelvin","kelvin"),
])
def test_positions_originales_normalisation_et_relecture(texte,requete):
    rep = extraits_correspondants({"texte_integral":texte},[requete])[0]
    debut,fin = rep["correspondance_debut"],rep["correspondance_fin"]
    assert requete in _normaliser(texte[debut:fin])
    assert rep["fragment"] == texte[rep["decalage"]:rep["decalage"]+len(rep["fragment"])]
    assert len(rep["fragment"]) <= 384 and rep["unite_decalage"] == "points_de_code_unicode_python"
    assert rep["total_caracteres"] == len(texte)


def test_projection_indices_compatible_normaliseur_sur_unicode_divers():
    rng = random.Random(33)
    texte = ''.join(chr(rng.randrange(0x110000)) for _ in range(12000)) + "e\u0301 — مُعَـدَّات œ æ ﬃ ß ¼ ㍿"
    normalise = _normaliser(texte)
    indices = list(_indices_normalises(texte))
    assert len(indices) == len(normalise)
    assert indices == sorted(indices)
    assert all(c == " " or c in _normaliser(texte[i]) for c,i in zip(normalise,indices))


def test_selection_un_par_champ_premier_terme_pas_premiere_position():
    champs = {c:"deux puis UN puis UN NON OFFICIEL" for c in ("intitule","texte_integral","texte_francais","texte_arabe")}
    rep = extraits_correspondants(champs,["un","deux"])
    assert len(rep) == 4
    assert all(r["terme_normalise"] == "un" and r["correspondance_debut"] == 10 for r in rep)
    assert extraits_correspondants(champs,[]) == []
    assert extraits_correspondants({"texte_integral":None,"texte_francais":""},["test"]) == []
    assert extraits_correspondants({"texte_integral":"NON OFFICIEL"},["absent"]) == []


def test_span_tres_long_et_terme_expansion_sur_un_caractere():
    texte = "a" + "ـ"*500 + "b NON OFFICIEL"
    rep = extraits_correspondants({"texte_integral":texte},["ab"])[0]
    assert len(rep["fragment"]) == 384 and rep["correspondance_fin"] == 502
    assert rep["correspondance_entierement_visible"] is False and rep["tronque_fin"] is True
    assert extraits_correspondants({"intitule":"ﬃ"},["fi"])[0]["correspondance_fin"] == 1


def test_recherche_garde_apercu_pagination_et_lecture_exacte(tmp_path):
    transcription,metadata = fichiers_code(tmp_path)
    brut = json.loads(transcription.read_text())
    texte = "😀 début NON OFFICIEL "*50+"ÉQUIPEMENT <img src=x> NON OFFICIEL"
    brut["articles"][0]["texte_integral"] = texte
    transcription.write_text(json.dumps(brut))
    lot = tmp_path / "lot"
    preparer_code(transcription,metadata,lot)
    avant = snapshot(tmp_path)
    rep = rechercher_code(lot,"equipement")
    r = rep["resultats"][0]
    assert "ÉQUIPEMENT" not in r["apercus"]["texte_integral"]["texte"]
    ex = r["extraits_correspondants"][0]
    assert "ÉQUIPEMENT" in ex["fragment"]
    lecture = consulter_article(lot,r["id"],ex["champ_texte"],len(ex["fragment"]),ex["decalage"])
    assert lecture["fragment"] == ex["fragment"]
    assert rep["occurrences_denombrees"] is False and rep["validation_juridique"] == "non_validee"
    assert rechercher_code(lot,"equipement",decalage=1)["resultats"] == []
    assert rechercher_code(lot,numero_article="5 bis")["resultats"][0]["extraits_correspondants"] == []
    assert snapshot(tmp_path) == avant


def test_cli_et_extrait_intitule_seul(tmp_path,capsys):
    transcription,metadata = fichiers_code(tmp_path)
    brut = json.loads(transcription.read_text())
    brut["articles"][0]["intitule"] = "EN_TETE_SEULEMENT NON OFFICIEL"
    transcription.write_text(json.dumps(brut))
    lot = tmp_path / "lot"
    preparer_code(transcription,metadata,lot)
    assert main(["customs-code-search",str(lot),"--query","tete"]) == 0
    rep = json.loads(capsys.readouterr().out)
    assert rep["resultats"][0]["extraits_correspondants"][0]["champ_texte"] == "intitule"


def test_api_export_et_audit_obligatoire(revue,monkeypatch):
    from unocr import api
    client,racine,registre,cfg = revue
    avant = snapshot(racine)
    url = BASE + "/lots/code_a/search?q=equipement"
    r = client.get(url,headers=ADMIN)
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    rep = r.json()["resultat"]
    ex = rep["resultats"][0]["extraits_correspondants"][0]
    assert "QUIPEMENT" in ex["fragment"]
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
