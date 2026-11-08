"""Pièces textuelles NON OFFICIELLES : intégrité, historique, autorisation."""
import copy
import hashlib
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from test_customs_assessment import ADMIN, COMPLET, create, revise, url, value
from test_customs_review import revue as revue

from unocr.customs_reference.assessment import MagasinDossiers

PIECE = {"piece_id":"NOTICE-TEST", "nom":"notice-non-officielle.txt", "nature":"notice",
         "criteres_declares":["matiere","fonction"], "localisateur_declare":"Texte reçu, section technique déclarée",
         "texte":"FIXTURE NON OFFICIELLE\nمادة معلنة — fonction déclarée : équipement.\n<img src=x onerror=evil()>"}


def creer(revue, pieces=None):
    return revue[0].post(url(identifiant=None), headers=ADMIN,
                         json={"dossier_id":"TEST94","produit":COMPLET,
                               "pieces_techniques":[copy.deepcopy(PIECE)] if pieces is None else pieces})


def test_creation_integrite_et_historique_avec_sommaires_sans_texte(revue):
    doc = value(creer(revue))
    p = doc["pieces_techniques"][0]
    brut = PIECE["texte"].encode()
    assert p["sha256"] == hashlib.sha256(brut).hexdigest()
    assert p["octets"] == len(brut) and p["fourni_par"] == "admin-test"
    assert p["verification"] == "non_verifiee" and p["format"] == "texte_utf8"
    assert doc["diagnostic"]["classement_ia_effectue"] is False
    lu = value(revue[0].get(url(), headers=ADMIN))
    assert lu["pieces_techniques"] == [p]
    assert "texte" not in lu["historique"][0]["pieces_techniques"][0]
    assert lu["historique"][0]["pieces_techniques"][0]["sha256"] == p["sha256"]
    ancien = value(revue[0].get(url()+"?version=1", headers=ADMIN))
    assert ancien["pieces_techniques"] == [p] and "historique" not in ancien


def test_revisions_conservation_remplacement_suppression_et_lecture_ancienne(revue):
    premier = value(creer(revue))["pieces_techniques"][0]
    second = value(revise(revue))["pieces_techniques"][0]
    assert second == premier
    identique = value(revise(revue,version=2,pieces_techniques=[PIECE]))["pieces_techniques"][0]
    assert identique == premier
    nouvelle = dict(PIECE, texte="Version modifiée NON OFFICIELLE")
    modifie = value(revise(revue,version=3,pieces_techniques=[nouvelle]))["pieces_techniques"][0]
    assert modifie["sha256"] != premier["sha256"]
    assert value(revise(revue,version=4,pieces_techniques=[]))["pieces_techniques"] == []
    assert value(revue[0].get(url()+"?version=1", headers=ADMIN))["pieces_techniques"] == [premier]
    assert value(revue[0].get(url()+"?version=4", headers=ADMIN))["pieces_techniques"] == [modifie]
    assert value(revue[0].get(url(), headers=ADMIN))["version"] == 5


def test_piece_ne_complete_pas_produit_et_n_est_pas_expertise(revue):
    doc = value(revue[0].post(url(identifiant=None), headers=ADMIN,
                            json={"dossier_id":"TEST94","produit":{"designation":"Équipement"},
                                  "pieces_techniques":[PIECE]}))
    assert "matiere" in doc["diagnostic"]["informations_non_renseignees"]
    assert "fonction" in doc["diagnostic"]["informations_non_renseignees"]
    assert doc["publication_active"] is False and doc["validation_juridique"] == "non_validee"


@pytest.mark.parametrize("champ,valeur", [
    ("piece_id","../fuite"), ("nom","../fuite.txt"), ("nom","x/y"), ("nom","x:y"),
    ("nom","\nnotice"), ("nom"," "), ("nom","."), ("texte"," "), ("texte","\x00"),
    ("texte","a"*16385), ("texte","€"*11000), ("texte","\x7f"),
    ("localisateur_declare","\ttest"), ("localisateur_declare"," "),
    ("criteres_declares",[]), ("criteres_declares",["matiere","matiere"]),
    ("criteres_declares",["classification_certifiee"]), ("nature","expertise_validee"),
    ("sha256","0"*64), ("fourni_par","autre-admin"), ("verification","validee"),
])
def test_piece_invalide_refusee_avant_ecriture(revue, champ, valeur):
    p = dict(PIECE)
    p[champ] = valeur
    assert creer(revue,[p]).status_code == 422
    assert not (revue[1]/"dossiers_metier.sqlite3").exists()


def test_limites_cinq_pieces_et_identifiants_uniques(revue):
    assert creer(revue,[PIECE,PIECE]).status_code == 422
    assert creer(revue,[dict(PIECE,piece_id=f"P{i}") for i in range(6)]).status_code == 422
    assert len(value(creer(revue,[dict(PIECE,piece_id=f"P{i}") for i in range(5)]))["pieces_techniques"]) == 5


def test_borne_utf8_exacte_et_pas_de_nom_de_chemin_physique(revue):
    p = dict(PIECE,texte="م"*16384)
    doc = value(creer(revue,[p]))
    assert doc["pieces_techniques"][0]["octets"] == 32768
    assert not list(revue[1].rglob(PIECE["nom"]))


def test_etat_ferme_reouverture_sans_modification_puis_revision(revue):
    value(creer(revue))
    value(revise(revue,statut="rejetee"))
    assert revise(revue,version=2,pieces_techniques=[]).status_code == 422
    doc = value(revise(revue,version=2))
    assert len(doc["pieces_techniques"]) == 1
    assert value(revise(revue,version=3,pieces_techniques=[]))["pieces_techniques"] == []


@pytest.mark.parametrize("version", ["0","101","invalide"])
def test_version_historique_invalide(revue, version):
    value(creer(revue))
    assert revue[0].get(url()+"?version="+version,headers=ADMIN).status_code == 422


def test_version_absente_et_authentification_historique(revue):
    value(creer(revue))
    assert revue[0].get(url()+"?version=2",headers=ADMIN).status_code == 404
    assert revue[0].get(url()+"?version=1").status_code == 401
    assert revue[0].get(url(lot="code_a")+"?version=1",headers=ADMIN).status_code == 422
    assert revue[0].get(url(identifiant="AUTRE")+"?version=1",headers=ADMIN).status_code == 404


def test_integrite_piece_verifiee_meme_si_enveloppe_rehachee(revue):
    doc = value(creer(revue))
    doc["pieces_techniques"][0]["texte"] = "ALTÉRATION NON OFFICIELLE"
    contenu = json.dumps(doc,ensure_ascii=False,sort_keys=True,separators=(",",":"))
    evenement = json.dumps({"dossier":doc,"sha256_contenu":hashlib.sha256(contenu.encode()).hexdigest()})
    with sqlite3.connect(revue[1]/"dossiers_metier.sqlite3") as conn:
        conn.execute("UPDATE dossiers SET contenu=?",(contenu,))
        conn.execute("UPDATE versions SET contenu=?",(evenement,))
    assert revue[0].get(url(),headers=ADMIN).status_code == 422


def test_compatibilite_version_sans_pieces_et_source_revalidee(revue):
    doc = value(create(revue))
    db = revue[1]/"dossiers_metier.sqlite3"
    # Représentation historique94/95, sans migration destructive du contenu.
    doc.pop("pieces_techniques")
    contenu = json.dumps(doc,ensure_ascii=False,sort_keys=True,separators=(",",":"))
    evenement = json.dumps({"dossier":doc,"sha256_contenu":hashlib.sha256(contenu.encode()).hexdigest()})
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE dossiers SET contenu=?",(contenu,))
        conn.execute("UPDATE versions SET contenu=?",(evenement,))
        conn.execute("DELETE FROM sorties_audit")
    assert "pieces_techniques" not in value(revue[0].get(url()+"?version=1",headers=ADMIN))
    assert value(revise(revue))["pieces_techniques"] == []
    (revue[1]/"tarif_a/source_recue.json").write_text("[]")
    assert revue[0].get(url()+"?version=1",headers=ADMIN).status_code in {409,422}


def test_revisions_concurrentes_de_pieces_sans_perte_silencieuse(revue):
    value(creer(revue))
    with ThreadPoolExecutor(max_workers=2) as pool:
        reponses = list(pool.map(lambda texte: revise(revue,pieces_techniques=[dict(PIECE,texte=texte)]),
                                 ["TEXTE A NON OFFICIEL", "TEXTE B NON OFFICIEL"]))
    assert sorted(r.status_code for r in reponses) == [200,409]
    doc = value(revue[0].get(url(),headers=ADMIN))
    assert doc["version"] == 2 and len(doc["historique"]) == 2
    assert doc["pieces_techniques"][0]["texte"] in {"TEXTE A NON OFFICIEL", "TEXTE B NON OFFICIEL"}
    assert MagasinDossiers(revue[1]/"dossiers_metier.sqlite3").lire("TEST94","tarif_a",doc["manifest_sha256"])["version"] == 2


def test_sauvegarde_reprise_piece_et_outbox_en_attente(revue, tmp_path, monkeypatch):
    from types import SimpleNamespace

    from unocr import api, backup
    from unocr.logging_setup import AuditIndisponible
    original = api.audit_obligatoire
    def panne(*args, **kwargs):
        if kwargs.get("operation") == "version_dossier_metier":
            raise AuditIndisponible("TEST panne de livraison")
        return original(*args, **kwargs)
    monkeypatch.setattr(api,"audit_obligatoire",panne)
    assert creer(revue).status_code == 503
    sauvegarde = backup.creer_sauvegarde(revue[3], inclure_quarantaine=True)
    cible = SimpleNamespace(data_dir=tmp_path/"reprise/data", log_dir=tmp_path/"reprise/logs")
    backup.restaurer_sauvegarde(cible,sauvegarde.chemin,inclure_quarantaine=True)
    db = cible.data_dir/"customs-quarantine/dossiers_metier.sqlite3"
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT livre FROM sorties_audit").fetchall() == [(0,)]
        document = json.loads(conn.execute("SELECT contenu FROM dossiers").fetchone()[0])
    magasin = MagasinDossiers(db)
    assert magasin.lire("TEST94","tarif_a",document["manifest_sha256"])["pieces_techniques"][0]["texte"] == PIECE["texte"]
    sorties = []
    magasin.reconcilier_audit("TEST94","tarif_a",document["manifest_sha256"],lambda **kw: sorties.append(kw))
    assert len(sorties) == 1 and "texte" not in sorties[0]


def test_declaration_attribut_citation_exacte_unicode_pas_inference(revue):
    texte = "😀 مادة معلنة : acier NON OFFICIEL"
    debut = texte.index("acier")
    declaration = {"critere":"matiere","valeur_declaree":"acier", "debut":debut,
                   "fin":debut+5,"citation":"acier"}
    p = dict(PIECE,texte=texte,declarations_attributs=[declaration])
    doc = value(creer(revue,[p]))
    assert doc["pieces_techniques"][0]["declarations_attributs"] == [declaration]
    assert doc["diagnostic"]["produit_declare"]["matiere"] == COMPLET["matiere"]
    historique = value(revue[0].get(url(),headers=ADMIN))["historique"]
    assert "declarations_attributs" not in historique[0]["pieces_techniques"][0]


@pytest.mark.parametrize("modification", [
    {"citation":"inventée"}, {"debut":-1}, {"fin":100}, {"debut":5,"fin":4},
    {"critere":"usage"}, {"valeur_declaree":" "}, {"debut":True},
])
def test_citation_incoherente_refusee(revue, modification):
    declaration = {"critere":"matiere","valeur_declaree":"acier", "debut":0,"fin":5,"citation":"acier"}
    declaration.update(modification)
    p = dict(PIECE,texte="acier NON OFFICIEL",declarations_attributs=[declaration])
    assert creer(revue,[p]).status_code == 422
    assert not (revue[1]/"dossiers_metier.sqlite3").exists()


def test_citations_repetees_par_critere_refusees(revue):
    declaration = {"critere":"matiere","valeur_declaree":"acier", "debut":0,"fin":5,"citation":"acier"}
    assert creer(revue,[dict(PIECE,texte="acier",declarations_attributs=[declaration,declaration])]).status_code == 422
