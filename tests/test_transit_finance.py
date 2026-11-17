"""Finance historique `/transit/*` : persistance métier, RBAC et périmètre.

Ces routes écrivaient autrefois dans une liste JSON annexe du dossier, avec un
identifiant jamais généré et un horodatage appelant une méthode inexistante.
Elles doivent désormais partager le magasin `BusinessStore[Frais]` avec
`/api/frais`, sans régression de cloisonnement ni faux succès.
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from unocr import api as api_module
from unocr.api import app
from unocr.business_store import BusinessStore
from unocr.models import Frais

ADMIN = {"Authorization": "Bearer jeton-admin"}
FINANCIER = {"Authorization": "Bearer jeton-financier"}
FINANCIER_A = {"Authorization": "Bearer jeton-financier-a"}
RESP_TRANSIT = {"Authorization": "Bearer jeton-responsable-transit"}
CONTROLEUR = {"Authorization": "Bearer jeton-controleur"}
AGENT = {"Authorization": "Bearer jeton-agent"}
LECTEUR = {"Authorization": "Bearer jeton-lecteur"}


@pytest.fixture()
def transit(tmp_cfg):
    data = tmp_cfg.data_dir
    (data / "dossiers").mkdir(parents=True, exist_ok=True)
    for identifiant in ("dos_a", "dos_b"):
        (data / "dossiers" / f"{identifiant}.json").write_text(
            json.dumps({"id": identifiant, "label": identifiant}), encoding="utf-8")
    (data / "rbac.json").write_text(json.dumps({
        "utilisateurs": [
            {"nom": "admin", "jeton": "jeton-admin", "roles": ["administrateur"], "dossiers": ["*"]},
            {"nom": "financier", "jeton": "jeton-financier", "roles": ["responsable_financier"], "dossiers": ["*"]},
            {"nom": "financier_a", "jeton": "jeton-financier-a", "roles": ["responsable_financier"], "dossiers": ["dos_a"]},
            {"nom": "resp_transit", "jeton": "jeton-responsable-transit", "roles": ["responsable_transit"], "dossiers": ["*"]},
            {"nom": "controleur", "jeton": "jeton-controleur", "roles": ["controleur_documentaire"], "dossiers": ["*"]},
            {"nom": "agent", "jeton": "jeton-agent", "roles": ["agent_de_transit"], "dossiers": ["*"]},
            {"nom": "lecteur", "jeton": "jeton-lecteur", "roles": ["lecteur"], "dossiers": ["*"]},
        ]
    }, ensure_ascii=False), encoding="utf-8")
    api_module._recharge_rbac()
    assert api_module._rbac.actif is True
    with TestClient(app) as client:
        yield client, tmp_cfg
    api_module._recharge_rbac()


def _cree_frais(client, dossier="dos_a", entete=FINANCIER, **champs):
    corps = {"type_frais": "fret_maritime", "montant": 125.5, "devise": "eur",
             "description": "Fret dossier A"}
    corps.update(champs)
    return client.post(f"/transit/dossiers/{dossier}/frais", json=corps, headers=entete)


def test_frais_transit_persistant_et_partage_avec_api_frais(transit):
    client, cfg = transit
    rep = _cree_frais(client)
    assert rep.status_code == 200, rep.text
    frais = rep.json()["frais"]
    assert frais["id"].startswith("frais_")
    assert frais["dossier_id"] == "dos_a"
    assert frais["categorie"] == "fret_maritime"
    assert frais["devise"] == "EUR"
    assert frais["montant"] == 125.5
    assert frais["montant_devise"] == 125.5
    assert frais["statut_paiement"] == "en_attente"

    magasin = BusinessStore(cfg.data_dir / "metier.sqlite3", "frais", Frais)
    assert magasin[frais["id"]].model_dump() == frais
    assert client.get("/api/frais/" + frais["id"], headers=ADMIN).json() == frais
    assert client.get("/api/frais", params={"dossier_id": "dos_a"}, headers=ADMIN).json() == [frais]
    resume = client.get("/api/frais/dossier/dos_a/resume", headers=ADMIN).json()
    assert resume["par_devise"]["EUR"]["total_frais"] == 125.5


def test_paiement_transit_met_a_jour_le_frais_et_trace_l_acteur(transit):
    client, cfg = transit
    frais = _cree_frais(client).json()["frais"]
    rep = client.post("/transit/dossiers/dos_a/paiement", json={
        "frais_id": frais["id"], "montant": 125.5,
        "reference_paiement": "VIR-001", "mode_paiement": "virement",
    }, headers=FINANCIER)
    assert rep.status_code == 200, rep.text
    assert rep.json()["frais_id"] == frais["id"]
    assert rep.json()["paiement"]["par"] == "financier"
    assert rep.json()["frais"]["statut_paiement"] == "paye"
    assert rep.json()["frais"]["reference_paiement"] == "VIR-001"

    relu = client.get("/api/frais/" + frais["id"], headers=ADMIN).json()
    assert relu["statut_paiement"] == "paye"
    assert relu["mode_paiement"] == "virement"
    assert relu["date_paiement"]

    # L'alias historique fautif reste accepté, mais ne crée pas un second paiement.
    alias = client.post("/transit/dossiers/dos_a/paiement", json={
        "frai_id": frais["id"], "montant": 125.5,
    }, headers=FINANCIER)
    assert alias.status_code == 409

    audit = (cfg.log_dir / "audit.log").read_text(encoding="utf-8")
    assert "paiement_enregistre" in audit
    assert '"acteur": "financier"' in audit or '"acteur":"financier"' in audit
    assert frais["id"] in audit


@pytest.mark.parametrize("entete", [LECTEUR, AGENT, CONTROLEUR, RESP_TRANSIT])
def test_paiement_reserve_au_responsable_financier(transit, entete):
    client, _ = transit
    frais = _cree_frais(client).json()["frais"]
    rep = client.post("/transit/dossiers/dos_a/paiement", json={
        "frais_id": frais["id"], "montant": 125.5,
    }, headers=entete)
    assert rep.status_code == 403
    assert client.get("/api/frais/" + frais["id"], headers=ADMIN).json()["statut_paiement"] == "en_attente"


@pytest.mark.parametrize("entete", [LECTEUR, AGENT])
def test_creation_frais_refusee_aux_roles_insuffisants(transit, entete):
    client, _ = transit
    assert _cree_frais(client, entete=entete).status_code == 403
    assert client.get("/api/frais", headers=ADMIN).json() == []


def test_creation_par_responsable_transit_autorisee(transit):
    client, _ = transit
    assert _cree_frais(client, entete=RESP_TRANSIT).status_code == 200


def test_perimetre_dossier_sur_creation_et_paiement(transit):
    client, _ = transit
    assert _cree_frais(client, dossier="dos_b", entete=FINANCIER_A).status_code == 403
    frais_b = _cree_frais(client, dossier="dos_b").json()["frais"]
    # Un frais du dossier B ne doit pas être payable via le dossier A.
    rep = client.post("/transit/dossiers/dos_a/paiement", json={
        "frais_id": frais_b["id"], "montant": 125.5,
    }, headers=FINANCIER_A)
    assert rep.status_code == 404
    assert client.get("/api/frais/" + frais_b["id"], headers=ADMIN).json()["statut_paiement"] == "en_attente"


def test_dossier_ou_frais_inconnu_renvoie_404(transit):
    client, _ = transit
    assert _cree_frais(client, dossier="dos_inconnu").status_code == 404
    assert client.post("/transit/dossiers/dos_a/paiement", json={
        "frais_id": "frais_inconnu", "montant": 1,
    }, headers=FINANCIER).status_code == 404


@pytest.mark.parametrize("corps", [
    {"type_frais": "fret", "montant": 0},
    {"type_frais": "fret", "montant": -1},
    {"type_frais": "fret", "montant": "NaN"},
    {"type_frais": "fret", "montant": "Infinity"},
    {"type_frais": "   ", "montant": 1},
    {"type_frais": "fret", "montant": 1, "devise": "EU"},
    {"type_frais": "fret", "montant": 1, "devise": "EURO"},
])
def test_creation_invalide_422_sans_ecriture(transit, corps):
    client, _ = transit
    rep = client.post("/transit/dossiers/dos_a/frais", json=corps, headers=FINANCIER)
    assert rep.status_code == 422, rep.text
    assert client.get("/api/frais", headers=ADMIN).json() == []


def test_paiement_partiel_ou_divergent_refuse_sans_modifier_le_frais(transit):
    client, _ = transit
    frais = _cree_frais(client).json()["frais"]
    rep = client.post("/transit/dossiers/dos_a/paiement", json={
        "frais_id": frais["id"], "montant": 100,
    }, headers=FINANCIER)
    assert rep.status_code == 422
    assert client.get("/api/frais/" + frais["id"], headers=ADMIN).json()["statut_paiement"] == "en_attente"


def test_transit_exige_un_jeton_quand_rbac_est_actif(transit):
    client, _ = transit
    assert client.get("/transit/dossiers").status_code == 401
    assert client.get("/transit/dossiers", headers={"Authorization": "Bearer inconnu"}).status_code == 401
    assert client.post("/transit/dossiers/dos_a/frais", json={
        "type_frais": "fret", "montant": 1,
    }).status_code == 401
    assert client.get("/transit/dossiers", headers=LECTEUR).status_code == 200


def test_cloture_persistante_et_double_refus(transit):
    client, cfg = transit
    rep = client.post("/transit/dossiers/dos_a/cloturer", json={"motif": "fin de mission"}, headers=ADMIN)
    assert rep.status_code == 200, rep.text
    assert client.post("/transit/dossiers/dos_a/cloturer", json={"motif": "bis"}, headers=ADMIN).status_code == 409
    detail = client.get("/transit/dossiers/dos_a", headers=ADMIN).json()
    assert detail["statut_documentaire"] == "cloture"
    assert any(e["action"] == "cloture" for e in detail["history"])
    assert "dossier_cloture" in (cfg.log_dir / "audit.log").read_text(encoding="utf-8")


def test_archivage_restauration_utilisent_l_etat_reel(transit):
    client, _ = transit
    avant = client.get("/transit/dossiers/dos_a", headers=ADMIN).json()["state"]
    rep = client.post("/transit/dossiers/dos_a/archiver", json={"motif": "clos"}, headers=ADMIN)
    assert rep.status_code == 200, rep.text
    assert rep.json()["state"] == "archive"
    assert client.get("/transit/dossiers/dos_a", headers=ADMIN).json()["state"] == "archive"
    assert client.post("/transit/dossiers/dos_a/archiver", json={"motif": "bis"}, headers=ADMIN).status_code == 409
    restaure = client.post("/transit/dossiers/dos_a/restorer", headers=ADMIN)
    assert restaure.status_code == 200, restaure.text
    assert restaure.json()["state"] == avant
    assert client.post("/transit/dossiers/dos_a/restorer", headers=ADMIN).status_code == 400


def test_conteneurs_transit_persistants_et_cloisonnes(transit):
    client, cfg = transit
    rep = client.post("/transit/dossiers/dos_a/conteneurs", json={
        "conteneur": "CONT-001", "scelle": "S1", "poids": 1200,
    }, headers=AGENT)
    assert rep.status_code == 200, rep.text
    conteneur_id = rep.json()["conteneur_id"]
    liste = client.get("/transit/dossiers/dos_a/conteneurs", headers=LECTEUR).json()["conteneurs"]
    assert len(liste) == 1
    assert liste[0]["numero"] == "CONT-001"
    assert liste[0]["numero_conteneur"] == "CONT-001"
    assert client.get("/api/conteneurs/" + conteneur_id, headers=ADMIN).json()["dossier_id"] == "dos_a"
    assert client.post("/transit/dossiers/dos_a/conteneurs", json={"conteneur": "CONT-001"}, headers=AGENT).status_code == 400
    assert client.post("/transit/dossiers/dos_b/conteneurs", json={"conteneur": "CONT-001"}, headers=ADMIN).status_code == 409
    assert client.post("/transit/dossiers/dos_b/conteneurs", json={"conteneur": "CONT-002"}, headers=FINANCIER_A).status_code == 403
    assert client.delete("/transit/dossiers/dos_a/conteneurs/CONT-001", headers=AGENT).status_code == 200
    assert client.get("/transit/dossiers/dos_a/conteneurs", headers=LECTEUR).json()["conteneurs"] == []
    assert client.get("/api/conteneurs/" + conteneur_id, headers=ADMIN).status_code == 404


def test_historique_transit_lit_le_journal_reel(transit):
    client, _ = transit
    assert client.post("/transit/dossiers/dos_a/eta", json={"eta": "2026-12-01"}, headers=AGENT).status_code == 200
    historique = client.get("/transit/dossiers/dos_a/historique", headers=LECTEUR).json()["historique"]
    assert historique
    assert any(e["action"] == "mise_a_jour" for e in historique)


def test_audit_et_doublons_transit_restent_dans_le_perimetre(transit):
    client, _ = transit
    assert _cree_frais(client, dossier="dos_a").status_code == 200
    assert _cree_frais(client, dossier="dos_b").status_code == 200
    logs = client.get("/transit/audit", headers=FINANCIER_A).json()["logs"]
    assert logs
    assert all((e.get("dossier") or e.get("dossier_id")) == "dos_a" for e in logs)
    assert client.get("/transit/audit", params={"dossier_id": "dos_b"}, headers=FINANCIER_A).json()["logs"] == []

    doublons_a = client.post("/transit/dossiers/doublons", json={"label": "dos"}, headers=FINANCIER_A).json()
    assert doublons_a["total"] == 0
    doublons_admin = client.post("/transit/dossiers/doublons", json={"label": "dos"}, headers=ADMIN).json()
    assert doublons_admin["total"] == 1
    assert set(doublons_admin["doublons"][0]["dossiers"]) == {"dos_a", "dos_b"}


def test_transit_utilise_la_config_de_requete(transit, monkeypatch):
    client, _ = transit

    def interdit():
        raise AssertionError("la route ne doit pas retomber sur le singleton get_config")

    from unocr.routes import transit as transit_module
    monkeypatch.setattr(transit_module, "get_config", interdit)
    assert client.get("/transit/dossiers", headers=ADMIN).status_code == 200
    assert _cree_frais(client).status_code == 200


def test_list_dossiers_filtre_port(transit):
    client, cfg = transit
    data = cfg.data_dir / "dossiers"

    (data / "dos_c.json").write_text(
        json.dumps({"id": "dos_c", "label": "dos_c",
                    "port_chargement": "Le Havre", "port_destination": ""},
                   ensure_ascii=False), encoding="utf-8")
    (data / "dos_d.json").write_text(
        json.dumps({"id": "dos_d", "label": "dos_d",
                    "port_chargement": "", "port_destination": "Rotterdam"}),
        encoding="utf-8")
    (data / "dos_e.json").write_text(
        json.dumps({"id": "dos_e", "label": "dos_e",
                    "port_chargement": "", "port_destination": ""}),
        encoding="utf-8")

    tous = client.get("/transit/dossiers", headers=ADMIN).json()
    assert {d["id"] for d in tous} == {"dos_a", "dos_b", "dos_c", "dos_d", "dos_e"}

    havre = client.get("/transit/dossiers", params={"port": "Le Havre"}, headers=ADMIN).json()
    assert {d["id"] for d in havre} == {"dos_c"}

    havre_insensible = client.get("/transit/dossiers", params={"port": "le havre"}, headers=ADMIN).json()
    assert {d["id"] for d in havre_insensible} == {"dos_c"}

    # Cas de régression : un dossier dont seul port_destination est renseigné
    # ne doit pas matcher un port de chargement différent.
    rotterdam = client.get("/transit/dossiers", params={"port": "Rotterdam"}, headers=ADMIN).json()
    assert {d["id"] for d in rotterdam} == {"dos_d"}

    aucun = client.get("/transit/dossiers", params={"port": "Inconnu"}, headers=ADMIN).json()
    assert aucun == []
