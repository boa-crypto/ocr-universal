"""Dossiers métier sur fixtures NON OFFICIELLES ; aucune validation fiscale."""
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from test_customs_review import ADMIN, BASE
from test_customs_review import revue as revue

from unocr.customs_reference.assessment import (
    MagasinDossiers,
    RevisionDossier,
    RevisionDossierConflict,
)
from unocr.logging_setup import AuditIndisponible

PRODUIT={"designation":"Équipement"}
COMPLET={k:"Équipement" for k in ("designation","matiere","fonction","usage","caracteristiques")}


def url(lot="tarif_a",identifiant="TEST94"):
    return f"{BASE}/lots/{lot}/assessments"+(f"/{identifiant}" if identifiant else "")


def create(revue,produit=PRODUIT,identifiant="TEST94",lot="tarif_a",headers=ADMIN):
    return revue[0].post(url(lot,None),headers=headers,json={"dossier_id":identifiant,"produit":produit})


def revise(revue,version=1,statut="en_revue",**extra):
    return revue[0].patch(url(),headers=ADMIN,json={"version_attendue":version,"statut":statut,
                                                  "justification":"Motivation documentaire de test NON OFFICIEL",**extra})


def value(response):
    assert response.status_code==200,response.text
    assert response.headers["cache-control"]=="no-store"
    body=response.json()
    assert body["publication_active"] is False and body["validation_juridique"]=="non_validee"
    return body["resultat"]


def test_complete_workflow_and_history_survive_fresh_store(revue):
    client,root,registre,_=revue
    created=value(create(revue,COMPLET))
    assert created["statut"]=="brouillon" and created["version"]==1
    assert created["acteur"]=="admin-test"
    assert not create(revue,COMPLET).json().get("resultat")
    assert value(revise(revue))["version"]==2
    candidate=created["diagnostic"]["recherche"]["resultats"][0]["ligne"]
    proposed=value(revise(revue,2,"proposition_humaine",code_propose=candidate["code_tarifaire_10"],
                          raisonnement_rgi="Analyse RGI déclarée NON OFFICIELLE",notes_exclusions="Notes non qualifiées NON OFFICIELLES",
                          references=[candidate["reference"]]))
    assert proposed["statut"]=="proposition_humaine" and proposed["publication_active"] is False
    read=value(client.get(url(),headers=ADMIN))
    assert [v["statut"] for v in read["historique"]]==["brouillon","en_revue","proposition_humaine"]
    assert all(v["acteur"]=="admin-test" and len(v["sha256_contenu"])==64 for v in read["historique"])
    manifest=json.loads(registre.read_text())["lots"][0]["manifest_sha256"]
    assert MagasinDossiers(root/"dossiers_metier.sqlite3").lire("TEST94","tarif_a",manifest)==proposed
    assert value(revise(revue,3,"en_revue"))["version"]==4
    assert value(revise(revue,4,"rejetee"))["statut"]=="rejetee"
    assert value(revise(revue,5,"en_revue"))["version"]==6


def test_missing_information_and_abstention_are_explicit(revue):
    document=value(create(revue,{"designation":"xyzabsent94"}))
    d=document["diagnostic"]
    assert d["abstention_documentaire"] is True
    assert d["informations_non_renseignees"]==["matiere","fonction","usage","caracteristiques"]
    assert len(d["questions_a_documenter"])==4 and d["classement_ia_effectue"] is False
    assert d["recherche"]["resultats"]==[]


def test_product_can_be_completed_in_a_revision(revue):
    value(create(revue))
    value(revise(revue,1,"a_completer"))
    updated=value(revise(revue,2,"en_revue",produit=COMPLET))
    assert updated["diagnostic"]["informations_non_renseignees"]==[]
    assert len(updated["diagnostic"]["recherche"]["resultats"])>0


@pytest.mark.parametrize("extra",[{"statut":"publiee"},{"user":"SPOOF94"},{"publication_active":True},
                                 {"version_attendue":True},{"justification":"          "}])
def test_untrusted_fields_status_and_types_are_rejected(revue,extra):
    value(create(revue))
    assert revise(revue,**extra).status_code==422
    assert value(revue[0].get(url(),headers=ADMIN))["version"]==1


@pytest.mark.parametrize("produit",[{"designation":" "},{"designation":"Équipement","matiere":""},
                                   {"designation":"Équipement","tariff_code":"0101000000"}])
def test_product_contract(revue,produit):
    assert create(revue,produit).status_code==422
    assert not (revue[1]/"dossiers_metier.sqlite3").exists()


def test_direct_proposal_without_review_is_rejected(revue):
    value(create(revue,COMPLET))
    assert revise(revue,statut="proposition_humaine").status_code==422


@pytest.mark.parametrize("defaut",["informations","code","references","rgi","notes"])
def test_incomplete_proposal_does_not_create_a_version(revue,defaut):
    document=value(create(revue,PRODUIT if defaut=="informations" else COMPLET))
    value(revise(revue))
    candidate=document["diagnostic"]["recherche"]["resultats"][0]["ligne"]
    payload={"code_propose":candidate["code_tarifaire_10"],"references":[candidate["reference"]],
             "raisonnement_rgi":"Analyse RGI NON OFFICIELLE", "notes_exclusions":"Analyse des notes NON OFFICIELLE"}
    if defaut=="code":
        payload["code_propose"]="9999999999"
    elif defaut=="references":
        payload["references"]=[{"source_id":"INVENTED94","localisateur":"page inventée"}]
    elif defaut in {"rgi","notes"}:
        del payload["raisonnement_rgi" if defaut=="rgi" else "notes_exclusions"]
    assert revise(revue,2,"proposition_humaine",**payload).status_code==422
    assert value(revue[0].get(url(),headers=ADMIN))["version"]==2


def test_stale_revision_has_no_write(revue):
    value(create(revue))
    value(revise(revue))
    assert revise(revue).status_code==409
    assert len(value(revue[0].get(url(),headers=ADMIN))["historique"])==2


@pytest.mark.parametrize("headers,status",[({},401),({"Authorization":"Bearer TEST_LECTEUR_NON_PRODUCTION"},403)])
def test_denied_does_not_create_storage(revue,headers,status):
    assert create(revue,headers=headers).status_code==status
    assert not (revue[1]/"dossiers_metier.sqlite3").exists()


def test_reviewer_allowlist_is_required(revue):
    registry=json.loads(revue[2].read_text())
    registry["reviseurs"]=[]
    revue[2].write_text(json.dumps(registry))
    assert create(revue).status_code==403
    assert not (revue[1]/"dossiers_metier.sqlite3").exists()


def test_open_mode_does_not_allow_writes(revue,monkeypatch):
    from unocr import api
    from unocr.rbac import RegistreRBAC
    monkeypatch.setattr(api,"_rbac",RegistreRBAC(actif=False))
    assert create(revue).status_code==403


def test_other_lot_cannot_read_dossier(revue):
    value(create(revue))
    assert revue[0].get(url("tarif_b"),headers=ADMIN).status_code==404


def test_legal_lot_is_not_tariff_assessment(revue):
    assert create(revue,lot="code_a").status_code==422


def test_source_tampering_refused_for_create_and_read(revue):
    value(create(revue))
    path=revue[1]/"tarif_a"/"lot.json"
    path.write_bytes(path.read_bytes()+b" ")
    assert revue[0].get(url(),headers=ADMIN).status_code==409
    assert create(revue,identifiant="OTHER94").status_code==409


def test_database_tampering_is_not_silently_trusted(revue):
    value(create(revue))
    with sqlite3.connect(revue[1]/"dossiers_metier.sqlite3") as conn:
        conn.execute("UPDATE dossiers SET contenu='{}'")
    assert revue[0].get(url(),headers=ADMIN).status_code in {409,422}


def test_external_audit_failure_keeps_transactional_version_explicitly(revue,monkeypatch):
    import unocr.logging_setup as logging
    original=logging.audit_obligatoire
    def fail(*args,**kwargs):
        raise AuditIndisponible("test")
    monkeypatch.setattr(logging,"audit_obligatoire",fail)
    # Le callback de l'API référence son import, pas le module logging.
    from unocr import api
    monkeypatch.setattr(api,"audit_obligatoire",fail)
    assert create(revue).status_code==503
    monkeypatch.setattr(api,"audit_obligatoire",original)
    read=value(revue[0].get(url(),headers=ADMIN))
    assert read["version"]==1 and len(read["historique"])==1


def test_two_store_instances_compare_revision_transactionally(revue):
    created=value(create(revue))
    path=revue[1]/"dossiers_metier.sqlite3"
    revision=RevisionDossier(version_attendue=1,statut="en_revue",justification="Revue concurrente NON OFFICIELLE")
    def edit(actor):
        try:
            return MagasinDossiers(path).enregistrer("TEST94","tarif_a",created["manifest_sha256"],
                     created["diagnostic"],actor,revision)["version"]
        except RevisionDossierConflict:
            return "conflit"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(edit,["REV_A94","REV_B94"]))
    assert sorted(map(str,results))==["2","conflit"]
    assert len(value(revue[0].get(url(),headers=ADMIN))["historique"])==2


def test_two_processes_share_the_sqlite_revision_guard(revue):
    import os
    import subprocess
    import sys
    document=value(create(revue))
    payload=json.dumps({"path":str(revue[1]/"dossiers_metier.sqlite3"),"document":document})
    script='''
import json,sys
from pathlib import Path
from unocr.customs_reference.assessment import MagasinDossiers,RevisionDossier,RevisionDossierConflict
p=json.loads(sys.argv[1]);d=p['document']
r=RevisionDossier(version_attendue=1,statut='en_revue',justification='Revue processus NON OFFICIELLE')
try:
 print(MagasinDossiers(Path(p['path'])).enregistrer(d['id'],d['lot_id'],d['manifest_sha256'],d['diagnostic'],'PROCESS94',r)['version'])
except RevisionDossierConflict:
 print('conflit')
'''
    processes=[subprocess.Popen([sys.executable,"-c",script,payload],stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                               text=True,env={**os.environ,"PYTHONPATH":"src"}) for _ in range(2)]
    outputs=[p.communicate(timeout=30) for p in processes]
    assert all(p.returncode==0 for p in processes),outputs
    assert sorted(o[0].strip() for o in outputs)==["2","conflit"]
    assert value(revue[0].get(url(),headers=ADMIN))["version"]==2


def test_outbox_durable_recuperable_sans_dupliquer_version(revue, monkeypatch):
    from unocr import api
    original = api.audit_obligatoire
    def panne(*args, **kwargs):
        if kwargs.get("operation") == "version_dossier_metier":
            raise AuditIndisponible("TEST INDISPONIBLE")
        return original(*args, **kwargs)
    monkeypatch.setattr(api, "audit_obligatoire", panne)
    assert create(revue).status_code == 503
    db = revue[1]/"dossiers_metier.sqlite3"
    with sqlite3.connect(db) as conn:
        evenement, livre = conn.execute("SELECT evenement,livre FROM sorties_audit").fetchone()
        assert livre == 0
        assert conn.execute("SELECT count(*) FROM versions").fetchone() == (1,)
    monkeypatch.setattr(api, "audit_obligatoire", original)
    assert value(revue[0].get(url(), headers=ADMIN))["version"] == 1
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT evenement,livre FROM sorties_audit").fetchone() == (evenement, 1)
        assert conn.execute("SELECT count(*) FROM versions").fetchone() == (1,)
    sorties = []
    MagasinDossiers(db).reconcilier_audit("TEST94", "tarif_a", value(revue[0].get(url(), headers=ADMIN))["manifest_sha256"], lambda **kw: sorties.append(kw))
    assert sorties == []


def test_outbox_crash_apres_append_meme_identite_et_pas_exactly_once(revue):
    document = value(create(revue))
    db = revue[1]/"dossiers_metier.sqlite3"
    # Simule une ancienne version94 : même état et historique, sans livraison connue.
    with sqlite3.connect(db) as conn:
        conn.execute("DELETE FROM sorties_audit")
    sorties = []
    def append_puis_panne(**kw):
        sorties.append(kw)
        raise OSError("TEST crash après append avant acquittement")
    magasin = MagasinDossiers(db)
    with pytest.raises(OSError):
        magasin.reconcilier_audit("TEST94", "tarif_a", document["manifest_sha256"], append_puis_panne)
    magasin.reconcilier_audit("TEST94", "tarif_a", document["manifest_sha256"], lambda **kw: sorties.append(kw))
    assert len(sorties) == 2 and sorties[0] == sorties[1]
    assert set(sorties[0]) == {"evenement_id", "dossier_id", "version", "lot_id", "manifest_sha256", "acteur", "etat_dossier", "sha256_contenu"}
    assert len(sorties[0]["evenement_id"]) == 64


def test_outbox_alteree_refusee_et_aucun_envoi(revue):
    from unocr.customs_reference.assessment import DossierRefuse
    document = value(create(revue))
    db = revue[1]/"dossiers_metier.sqlite3"
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE sorties_audit SET evenement='{}',livre=0")
    with pytest.raises(DossierRefuse):
        MagasinDossiers(db).reconcilier_audit("TEST94", "tarif_a", document["manifest_sha256"], lambda **kw: pytest.fail("envoi interdit"))


def test_outbox_reconciliations_concurrentes_un_seul_append_sans_panne(revue):
    document = value(create(revue))
    db = revue[1]/"dossiers_metier.sqlite3"
    with sqlite3.connect(db) as conn:
        conn.execute("DELETE FROM sorties_audit")
    sorties = []
    def livrer(_):
        MagasinDossiers(db).reconcilier_audit("TEST94", "tarif_a", document["manifest_sha256"], lambda **kw: sorties.append(kw))
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(livrer,range(2)))
    assert len(sorties) == 1
