"""Non-régression P0 : cloisonnement, workflow persistant, résolutions tracées.

Ces tests exercent les trois blocages identifiés dans le bilan du 2026-11-14 :
accès hors périmètre sur les modules métier, workflow purement déclaratif,
et acceptations de risque perdues ou réappliquées après changement de source.
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from unocr import api as api_module
from unocr import controle_documentaire
from unocr.api import app
from unocr.controle_documentaire import AnomalieDetectee, Gravite, TypeAnomalie
from unocr.routes import controle_doc

ADMIN = {"Authorization": "Bearer jeton-admin"}
SUPERVISEUR = {"Authorization": "Bearer jeton-superviseur"}
OPERATEUR_A = {"Authorization": "Bearer jeton-operateur-a"}
OPERATEUR_B = {"Authorization": "Bearer jeton-operateur-b"}
LECTEUR = {"Authorization": "Bearer jeton-lecteur"}


@pytest.fixture()
def perimetre(tmp_cfg):
    """RBAC actif, deux dossiers, un opérateur limité au dossier A."""
    data = tmp_cfg.data_dir
    (data / "dossiers").mkdir(parents=True, exist_ok=True)
    for identifiant in ("dos_a", "dos_b"):
        (data / "dossiers" / f"{identifiant}.json").write_text(
            json.dumps({"id": identifiant, "label": identifiant}), encoding="utf-8")
    (data / "rbac.json").write_text(json.dumps({
        "utilisateurs": [
            {"nom": "admin", "jeton": "jeton-admin", "roles": ["administrateur"], "dossiers": ["*"]},
            {"nom": "superviseur", "jeton": "jeton-superviseur", "roles": ["superviseur"], "dossiers": ["*"]},
            {"nom": "operateur_a", "jeton": "jeton-operateur-a", "roles": ["operateur"], "dossiers": ["dos_a"]},
            {"nom": "operateur_b", "jeton": "jeton-operateur-b", "roles": ["operateur"], "dossiers": ["dos_b"]},
            {"nom": "lecteur", "jeton": "jeton-lecteur", "roles": ["lecteur"], "dossiers": ["*"]},
        ]
    }, ensure_ascii=False), encoding="utf-8")
    api_module._recharge_rbac()
    assert api_module._rbac.actif is True
    yield TestClient(app)
    api_module._recharge_rbac()


def _seed(client, dossier):
    """Objets métier réels dans un dossier, créés par l'administrateur."""
    ids = {}
    rep = client.post("/api/frais", json={"dossier_id": dossier, "montant": 10}, headers=ADMIN)
    assert rep.status_code == 200, rep.text
    ids["frais"] = "/api/frais/" + rep.json()["id"]
    rep = client.post("/api/frais/facture", json={"dossier_id": dossier, "montant_ttc": 10}, headers=ADMIN)
    assert rep.status_code == 200, rep.text
    ids["facture"] = "/api/frais/facture/" + rep.json()["id"]
    rep = client.post("/api/declarations", json={"dossier_id": dossier, "numero_declaration": "D-" + dossier}, headers=ADMIN)
    assert rep.status_code == 200, rep.text
    ids["declaration"] = "/api/declarations/" + rep.json()["id"]
    rep = client.post("/api/declarations/liquidation", json={"dossier_id": dossier, "declaration_id": rep.json()["id"]}, headers=ADMIN)
    assert rep.status_code == 200, rep.text
    ids["liquidation"] = "/api/declarations/liquidation/" + rep.json()["id"]
    rep = client.post("/api/terminal", json={"dossier_id": dossier, "numero_bl": "BL-" + dossier, "numero_conteneur": "CONT-" + dossier}, headers=ADMIN)
    assert rep.status_code == 200, rep.text
    ids["terminal"] = "/api/terminal/" + rep.json()["id"]
    rep = client.post("/api/expeditions", json={"dossier_id": dossier, "numero_bl": "BL-" + dossier}, headers=ADMIN)
    assert rep.status_code == 200, rep.text
    ids["expedition"] = "/api/expeditions/" + rep.json()["id"]
    rep = client.post("/api/transport/livraisons", json={"dossier_id": dossier}, headers=ADMIN)
    assert rep.status_code == 200, rep.text
    ids["livraison"] = "/api/transport/livraisons/" + rep.json()["id"]
    rep = client.post("/api/conteneurs", json={"dossier_id": dossier, "numero_conteneur": "CONT-" + dossier}, headers=ADMIN)
    assert rep.status_code == 200, rep.text
    ids["conteneur"] = "/api/conteneurs/" + rep.json()["id"]
    rep = client.post("/api/connaissements/bl", json={"dossier_id": dossier, "numero_bl": "BL-" + dossier}, headers=ADMIN)
    assert rep.status_code == 200, rep.text
    ids["bl"] = "/api/connaissements/bl/" + rep.json()["id"]
    rep = client.post("/api/connaissements/bad", json={"dossier_id": dossier, "numero_bl": "BL-" + dossier, "numero_bad": "BAD-" + dossier}, headers=ADMIN)
    assert rep.status_code == 200, rep.text
    ids["bad"] = "/api/connaissements/bad/" + rep.json()["id"]
    rep = client.post("/api/frais/banque/import", json={"dossier_id": dossier, "operations": [
        {"date": "2026-11-11", "montant": 10, "devise": "EUR", "identifiant_externe": "BANQ-" + dossier}]}, headers=ADMIN)
    assert rep.status_code == 200, rep.text
    return ids


@pytest.mark.parametrize("objet", [
    "frais", "facture", "declaration", "liquidation", "terminal",
    "expedition", "livraison", "conteneur", "bl", "bad",
])
def test_operateur_a_ne_lit_ni_ecrit_le_dossier_b(perimetre, objet):
    client = perimetre
    _seed(client, "dos_a")
    ids_b = _seed(client, "dos_b")
    url = ids_b[objet]

    assert client.get(url, headers=OPERATEUR_A).status_code == 403
    assert client.put(url, json={"observations": "intrus"}, headers=OPERATEUR_A).status_code == 403
    assert client.delete(url, headers=OPERATEUR_A).status_code == 403
    # L'objet est intact pour son propriétaire.
    assert client.get(url, headers=OPERATEUR_B).status_code == 200


def test_listes_filtrees_et_creation_hors_perimetre_refusee(perimetre):
    client = perimetre
    _seed(client, "dos_a")
    _seed(client, "dos_b")
    for liste in ("/api/frais", "/api/frais/facture", "/api/declarations",
                  "/api/declarations/liquidation", "/api/terminal", "/api/expeditions",
                  "/api/transport/livraisons", "/api/conteneurs",
                  "/api/connaissements/bl", "/api/connaissements/bad",
                  "/api/frais/banque/operations"):
        rep = client.get(liste, headers=OPERATEUR_A)
        assert rep.status_code == 200, liste
        assert all(obj["dossier_id"] == "dos_a" for obj in rep.json()), liste

    for url, corps in (
        ("/api/frais", {"dossier_id": "dos_b"}),
        ("/api/declarations", {"dossier_id": "dos_b"}),
        ("/api/terminal", {"dossier_id": "dos_b", "numero_bl": "X", "numero_conteneur": "X"}),
        ("/api/expeditions", {"dossier_id": "dos_b"}),
        ("/api/transport/livraisons", {"dossier_id": "dos_b"}),
        ("/api/conteneurs", {"dossier_id": "dos_b", "numero_conteneur": "X"}),
        ("/api/connaissements/bl", {"dossier_id": "dos_b", "numero_bl": "X"}),
        ("/api/workflow/create", {"dossier_id": "dos_b"}),
        ("/api/controle/analyser", {"dossier_id": "dos_b"}),
        ("/api/frais/banque/import", {"dossier_id": "dos_b", "operations": []}),
        ("/api/frais/rapprochement/auto", {"dossier_id": "dos_b", "date_debut": "2026-11-01", "date_fin": "2026-11-30"}),
    ):
        assert client.post(url, json=corps, headers=OPERATEUR_A).status_code == 403, url


def test_deplacement_inter_dossiers_refuse(perimetre):
    client = perimetre
    ids = _seed(client, "dos_a")
    for objet in ("frais", "declaration", "terminal", "expedition", "livraison", "conteneur", "bl"):
        rep = client.put(ids[objet], json={"dossier_id": "dos_b"}, headers=OPERATEUR_A)
        assert rep.status_code == 403, objet
        assert client.get(ids[objet], headers=OPERATEUR_A).json()["dossier_id"] == "dos_a"


def test_workflow_persistant_roles_motif_et_version(perimetre):
    client = perimetre
    rep = client.post("/api/workflow/create", json={"dossier_id": "dos_a"}, headers=OPERATEUR_A)
    assert rep.status_code == 200, rep.text
    assert rep.json()["current_stage"] == "creation"
    assert rep.json()["version"] == 1
    seconde = client.post("/api/workflow/create", json={"dossier_id": "dos_a"}, headers=OPERATEUR_A)
    assert seconde.status_code == 200
    assert seconde.json()["created"] is False
    assert client.post("/api/workflow/create", json={"dossier_id": "dos_a", "template_id": "inconnu"}, headers=OPERATEUR_A).status_code == 422
    assert client.get("/api/workflow/dos_a", headers=OPERATEUR_B).status_code == 403

    def transition(stage, entete=OPERATEUR_A, motif="", version=None, code=200):
        corps = {"to_stage": stage, "motif": motif}
        if version is not None:
            corps["expected_version"] = version
        rep = client.post("/api/workflow/dos_a/transition", json=corps, headers=entete)
        assert rep.status_code == code, (stage, rep.status_code, rep.text)
        return rep.json() if code == 200 else None

    transition("scan", version=1)
    transition("scan", version=1, code=409)  # version obsolète
    transition("ocr")
    transition("verification")
    transition("douane", code=403)  # rôle superviseur requis
    transition("douane", entete=SUPERVISEUR)
    transition("bloque", entete=SUPERVISEUR, code=422)  # motif requis
    bloque = transition("bloque", entete=SUPERVISEUR, motif="Pièce manquante")
    assert bloque["current_stage"] == "bloque"
    transition("douane", code=403)  # déblocage superviseur
    transition("douane", entete=SUPERVISEUR, code=422)
    transition("douane", entete=SUPERVISEUR, motif="Pièce retrouvée")
    transition("verification", entete=SUPERVISEUR, code=422)  # retour arrière motivé
    transition("verification", entete=SUPERVISEUR, motif="Relecture douane")
    transition("scan", entete=SUPERVISEUR, motif="Relecture complète")
    transition("cloture", entete=SUPERVISEUR, motif="Saut", code=409)

    # Rechargement : l'état vient du disque, pas d'un dictionnaire app.state.
    with TestClient(app) as recharge:
        vue = recharge.get("/api/workflow/dos_a", headers=SUPERVISEUR).json()
        assert vue["current_stage"] == "scan"
        assert vue["version"] >= 9
        historique = recharge.get("/api/workflow/dos_a/historique", headers=SUPERVISEUR).json()
        assert historique[0]["evenement"] == "workflow_cree"
        assert any(h.get("motif") == "Pièce manquante" for h in historique)

    # La clôture est terminale : aucun retour ni saut après elle.
    transition("ocr")
    transition("verification")
    transition("douane", entete=SUPERVISEUR)
    transition("port", entete=SUPERVISEUR)
    transition("transport", entete=SUPERVISEUR)
    transition("cloture", entete=SUPERVISEUR, code=422)
    cloture = transition("cloture", entete=SUPERVISEUR, motif="Dossier soldé")
    assert cloture["status"] == "termine"
    transition("scan", entete=SUPERVISEUR, motif="Retour interdit", code=409)


@pytest.fixture()
def moteur_controle(monkeypatch):
    """Anomalie contrôlée, mutable pour simuler un changement de source."""
    etat = {"anomalies": [AnomalieDetectee(
        type_anomalie=TypeAnomalie.INCOHERENCE,
        regle="valeur",
        documents_concernes=["doc1", "doc2"],
        champ="total_amount",
        valeurs={"doc1": "100", "doc2": "200"},
        gravite=Gravite.BLOCKING,
        message="Valeur divergente",
    )]}

    class FakeEngine:
        def __init__(self, *args, **kwargs):
            pass

        def analyser_dossier(self, dossier_id):
            return list(etat["anomalies"])

    monkeypatch.setattr(controle_documentaire, "ControleDocumentaireEngine", FakeEngine)
    monkeypatch.setattr(controle_doc, "ControleDocumentaireEngine", FakeEngine)
    return etat


def test_acceptation_risque_persistante_et_invalidee_si_source_change(perimetre, moteur_controle):
    client = perimetre
    analyse = client.post("/api/controle/analyser", json={"dossier_id": "dos_a"}, headers=OPERATEUR_A)
    assert analyse.status_code == 200, analyse.text
    assert analyse.json()["total_detectees"] == 1
    assert analyse.json()["peut_continuer"] is False

    # Un opérateur ne peut pas accepter le risque ; un superviseur le peut.
    refus = client.post("/api/controle/dos_a/resoudre", json={"regle": "valeur", "motif": "ok"}, headers=OPERATEUR_A)
    assert refus.status_code == 403
    accepte = client.post("/api/controle/dos_a/resoudre", json={
        "regle": "valeur", "champ": "total_amount", "documents": ["doc1", "doc2"],
        "action": "accepter_risque", "motif": "Écart justifié par avenant",
    }, headers=SUPERVISEUR)
    assert accepte.status_code == 200, accepte.text
    resolution_id = accepte.json()["resolution"]["id"]
    assert accepte.json()["resolution"]["acteur"] == "superviseur"

    statut = client.get("/api/controle/dos_a/statut", headers=LECTEUR).json()
    assert statut["total_detectees"] == 1
    assert statut["total_anomalies"] == 0
    assert statut["anomalies_acceptees"] == 1
    assert statut["peut_continuer"] is True
    acceptee = client.get("/api/controle/dos_a/anomalies", headers=LECTEUR).json()["anomalies"][0]
    assert acceptee["resolue"] is True
    assert acceptee["niveau"] == "blocking"

    # Persistance après rechargement du client.
    with TestClient(app) as recharge:
        assert recharge.get("/api/controle/dos_a/statut", headers=LECTEUR).json()["anomalies_acceptees"] == 1
        assert len(recharge.get("/api/controle/dos_a/resolutions", headers=LECTEUR).json()) == 1

    # La source change : l'empreinte n'est plus la même, l'acceptation ne s'applique plus.
    moteur_controle["anomalies"][0].valeurs = {"doc1": "100", "doc2": "999"}
    statut = client.get("/api/controle/dos_a/statut", headers=LECTEUR).json()
    assert statut["total_detectees"] == 1
    assert statut["total_anomalies"] == 1
    assert statut["anomalies_acceptees"] == 0
    assert statut["peut_continuer"] is False
    anomalie = client.get("/api/controle/dos_a/anomalies", headers=LECTEUR).json()["anomalies"][0]
    assert anomalie["statut"] == "active"
    assert anomalie["resolue"] is False

    # Une correction ne se décrète pas tant que l'anomalie est détectée.
    assert client.post("/api/controle/dos_a/resoudre", json={"regle": "valeur", "action": "corriger"}, headers=SUPERVISEUR).status_code == 409
    moteur_controle["anomalies"] = []
    assert client.post("/api/controle/dos_a/resoudre", json={"regle": "valeur", "action": "corriger"}, headers=SUPERVISEUR).status_code == 200

    # Révocation : si le constat initial revient, il est de nouveau actif.
    assert client.delete(f"/api/controle/dos_a/resolutions/{resolution_id}", headers=SUPERVISEUR).status_code == 200
    moteur_controle["anomalies"] = [AnomalieDetectee(
        type_anomalie=TypeAnomalie.INCOHERENCE, regle="valeur",
        documents_concernes=["doc1", "doc2"], champ="total_amount",
        valeurs={"doc1": "100", "doc2": "200"}, gravite=Gravite.BLOCKING,
        message="Valeur divergente",
    )]
    assert client.get("/api/controle/dos_a/statut", headers=LECTEUR).json()["peut_continuer"] is False


def test_rapprochement_bancaire_exige_superviseur_et_trace_refus(perimetre, tmp_cfg):
    client = perimetre
    _seed(client, "dos_a")
    facture = client.get("/api/frais/facture", headers=ADMIN).json()[0]
    operation = client.get("/api/frais/banque/operations", headers=ADMIN).json()[0]
    corps_auto = {"dossier_id": "dos_a", "date_debut": "2026-11-01", "date_fin": "2026-11-30"}
    corps_manuel = {"dossier_id": "dos_a", "facture_id": facture["id"],
                    "operation_id": operation["id"], "motif": "Pointage"}
    for url, corps in (("/api/frais/rapprochement/auto", corps_auto),
                       ("/api/frais/rapprochement/manuel", corps_manuel),
                       ("/api/frais/rapprochement/annuler", {"dossier_id": "dos_a",
                                                            "facture_id": facture["id"]})):
        assert client.post(url, json=corps, headers=OPERATEUR_A).status_code == 403
        assert client.post(url, json=corps, headers=LECTEUR).status_code == 403
    # L'import reste une saisie opérateur ; le pointage est une décision superviseur.
    assert client.post("/api/frais/banque/import", json={
        "dossier_id": "dos_a", "operations": []}, headers=OPERATEUR_A).status_code == 200
    ok = client.post("/api/frais/rapprochement/manuel", json=corps_manuel, headers=SUPERVISEUR)
    assert ok.status_code == 200, ok.text
    moi = client.get("/api/rbac/moi", headers=OPERATEUR_A).json()
    assert moi["ecriture"] is True and moi["supervision"] is False
    moi_sup = client.get("/api/rbac/moi", headers=SUPERVISEUR).json()
    assert moi_sup["supervision"] is True
    journal = (tmp_cfg.log_dir / "audit.log").read_text(encoding="utf-8")
    assert "acces_refuse_role" in journal and "operateur_a" in journal

