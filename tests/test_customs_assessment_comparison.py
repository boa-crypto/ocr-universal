"""Comparaison de déclarations NON OFFICIELLES, pas expertise ni classement."""
import copy
import hashlib
import json

import pytest
from test_customs_assessment import ADMIN, COMPLET, create, revise, url, value
from test_customs_review import revue as revue
from test_customs_technical_evidence import PIECE, creer


def comparaison(revue, version=None, headers=ADMIN):
    return revue[0].get(url()+"/comparison"+(f"?version={version}" if version is not None else ""),headers=headers)


def piece(identifiant, valeur, critere="matiere"):
    texte = "😀 مادة — "+valeur+" — NON OFFICIEL"
    debut = texte.index(valeur)
    return dict(PIECE,piece_id=identifiant,texte=texte,criteres_declares=[critere],
                declarations_attributs=[{"critere":critere,"valeur_declaree":valeur,
                                        "debut":debut,"fin":debut+len(valeur),"citation":valeur}])


def critere(resultat, cle="matiere"):
    return next(c for c in resultat["criteres"] if c["critere"] == cle)


def test_comparaison_provenance_citations_et_empreinte_sans_modifier_etat(revue):
    doc = value(creer(revue,[piece("P1",COMPLET["matiere"])]))
    resultat = value(comparaison(revue))
    c = critere(resultat)
    assert c["declarations_citees"][0]["egalite_exacte_avec_produit"] is True
    assert c["declarations_citees"][0]["piece"]["sha256"] == doc["pieces_techniques"][0]["sha256"]
    assert c["declarations_citees"][0]["citation"] == COMPLET["matiere"]
    attendu = hashlib.sha256(json.dumps(doc,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
    assert resultat["sha256_dossier"] == attendu
    apres = value(revue[0].get(url(),headers=ADMIN))
    apres.pop("historique")
    assert apres == doc
    assert len(resultat["candidats"]) == len(doc["diagnostic"]["recherche"]["resultats"])
    assert resultat["attributs_techniques_certifies"] is False
    assert resultat["contradiction_semantique_etablie"] is False


@pytest.mark.parametrize("valeurs", [("acier","aluminium"),("Acier","acier"),("acier ","acier"),("مادة","ماده")])
def test_divergence_exacte_pas_contradiction_semantique(revue,valeurs):
    value(creer(revue,[piece("P1",valeurs[0]),piece("P2",valeurs[1])]))
    r = value(comparaison(revue))
    assert critere(r)["divergence_textuelle_declarations"] is True
    assert critere(r)["valeurs_distinctes_exactes"] == list(valeurs)
    assert any(q["type"] == "ecart_textuel_a_examiner" and q["critere"] == "matiere" for q in r["questions_a_arbitrer"])
    assert r["contradiction_semantique_etablie"] is False


def test_meme_valeur_plusieurs_pieces_ne_compte_pas_confiance(revue):
    value(creer(revue,[piece("P1","acier"),piece("P2","acier")]))
    r = value(comparaison(revue))
    assert critere(r)["valeurs_distinctes_exactes"] == ["acier"]
    assert critere(r)["divergence_textuelle_declarations"] is False
    assert len(critere(r)["declarations_citees"]) == 2
    assert "score" not in r and "probabilite" not in r


def test_piece_associee_sans_citation_et_produit_manquant(revue):
    value(create(revue))
    value(revise(revue,pieces_techniques=[PIECE]))
    r = value(comparaison(revue))
    c = critere(r)
    assert len(c["pieces_associees"]) == 1 and c["declarations_citees"] == []
    assert any(q["type"] == "produit_non_renseigne" and q["critere"] == "matiere" for q in r["questions_a_arbitrer"])
    assert any(q["type"] == "sans_citation_declaree" and q["critere"] == "matiere" for q in r["questions_a_arbitrer"])


def test_versions_anciennes_et_retrait_sans_reecriture(revue):
    value(creer(revue,[piece("P1","acier")]))
    value(revise(revue,pieces_techniques=[]))
    courant = value(comparaison(revue))
    ancien = value(comparaison(revue,1))
    assert courant["version"] == 2 and ancien["version"] == 1
    assert critere(courant)["declarations_citees"] == []
    assert len(critere(ancien)["declarations_citees"]) == 1
    assert courant["sha256_dossier"] != ancien["sha256_dossier"]


@pytest.mark.parametrize("version,statut", [(0,422),(101,422),("abc",422),(2,404)])
def test_version_invalide_ou_absente(revue,version,statut):
    value(creer(revue))
    assert comparaison(revue,version).status_code == statut


def test_authentification_et_allowlist_non_contournees(revue):
    value(creer(revue))
    assert comparaison(revue,headers={}).status_code == 401
    registre = json.loads(revue[2].read_text())
    registre["reviseurs"] = []
    revue[2].write_text(json.dumps(registre))
    assert comparaison(revue).status_code == 403


def test_source_modifiee_refuse_comparaison(revue):
    value(creer(revue))
    (revue[1]/"tarif_a/source_recue.json").write_text("[]")
    assert comparaison(revue).status_code in {409,422}


def test_abstention_et_pas_de_candidat_invente(revue):
    doc = value(create(revue,produit={"designation":"AUCUN_TERME_FIXTURE_ZZZ"}))
    r = value(comparaison(revue))
    assert r["candidats"] == [] and doc["diagnostic"]["abstention_documentaire"] is True
    assert r["candidat_retenu_automatiquement"] is False and r["classement_ia_effectue"] is False


def test_comparaison_ne_mute_pas_entree_python(revue):
    from unocr.customs_reference.assessment_comparison import comparer_dossier
    doc = value(creer(revue))
    avant = copy.deepcopy(doc)
    r = comparer_dossier(doc)
    assert doc == avant
    assert r["version"] == doc["version"]
    r["criteres"][1]["pieces_associees"][0]["nom"] = "MODIFIE"
    if r["candidats"]:
        r["candidats"][0]["reference"]["source_id"] = "MODIFIE"
    assert doc == avant


def test_audit_indisponible_reconciliation_par_comparaison_sans_nouvelle_version(revue,monkeypatch):
    from unocr import api
    from unocr.logging_setup import AuditIndisponible
    original = api.audit_obligatoire
    def panne(*args,**kwargs):
        if kwargs.get("operation") == "version_dossier_metier":
            raise AuditIndisponible("TEST panne")
        return original(*args,**kwargs)
    monkeypatch.setattr(api,"audit_obligatoire",panne)
    assert creer(revue).status_code == 503
    assert comparaison(revue).status_code == 503
    monkeypatch.setattr(api,"audit_obligatoire",original)
    r = value(comparaison(revue))
    assert r["version"] == 1
    assert len(value(revue[0].get(url(),headers=ADMIN))["historique"]) == 1


def test_comparaison_absente_ne_cree_pas_de_base(revue):
    assert comparaison(revue).status_code == 404
    assert not (revue[1]/"dossiers_metier.sqlite3").exists()


def test_comparaison_hash_identique_avec_ou_sans_historique_et_sortie_independante(revue):
    from unocr.customs_reference.assessment_comparison import comparer_dossier
    doc = value(creer(revue,[piece("P1","acier")]))
    avec_historique = dict(doc,historique=[{"version":1,"information":"sommaire"}])
    assert comparer_dossier(doc) == comparer_dossier(avec_historique)


def test_pieces_plus_precises_ne_reclassent_pas_les_candidats(revue):
    avant = value(creer(revue))
    premier = value(comparaison(revue))
    value(revise(revue,pieces_techniques=[piece("P1","AUTRE MARCHANDISE NON OFFICIELLE")]))
    apres = value(comparaison(revue))
    assert premier["candidats"] == apres["candidats"]
    assert premier["version"] == avant["version"] and apres["version"] == 2
    assert apres["candidat_retenu_automatiquement"] is False
