"""Rôles et cloisonnement par dossier.

Le point le plus important de ce fichier : **sans `data/rbac.json`, rien ne
change**. Un déploiement existant qui n'a jamais créé ce fichier doit obtenir
exactement le comportement d'avant — pas de jeton exigé, aucune route fermée.
C'est ce que vérifient les premiers tests.
"""
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from unocr import api
from unocr.dossier import DossierStore
from unocr.rbac import (
    ADMINISTRATEUR,
    LECTEUR,
    OPERATEUR,
    SUPERVISEUR,
    AGENT_DE_TRANSIT,
    RESPONSABLE_TRANSPORT,
    DECLARANT_HABILE,
    CONTROLEUR_DOCUMENTAIRE,
    RESPONSABLE_FINANCIER,
    TOUS,
    RBACError,
    RegistreRBAC,
    Utilisateur,
)


@pytest.fixture()
def client(tmp_cfg):
    """Client avec RBAC inactif (pas de data/rbac.json)."""
    original = api._rbac
    api._rbac = RegistreRBAC.charger(tmp_cfg.data_dir)
    assert not api._rbac.actif
    try:
        with TestClient(api.app) as c:
            yield c
    finally:
        api._rbac = original


def _active(client, utilisateurs):
    """Active le RBAC en écrivant data/rbac.json puis en rechargeant."""
    api._rbac = RegistreRBAC.depuis({"utilisateurs": utilisateurs})
    yield_ = api._rbac
    api._rbac = yield_
    return yield_


def _jeton(nom):
    return "jeton-" + nom


def _installe(tmp_cfg, utilisateurs):
    """Écrit le fichier de rôles et recharge le registre de l'API."""
    (tmp_cfg.data_dir / "rbac.json").write_text(json.dumps(
        {"utilisateurs": utilisateurs}, ensure_ascii=False), encoding="utf-8")
    api._rbac = RegistreRBAC.charger(tmp_cfg.data_dir)
    return api._rbac


def _auth(c, nom):
    return {"Authorization": "Bearer %s" % _jeton(nom)}


# ─────────────── compatibilité : sans fichier, rien ne change ───────────────

def test_sans_fichier_les_routes_restent_ouvertes(client):
    """Aucun cloisonnement, aucun rôle exigé : comportement historique.

    On ne vérifie pas que la liste est vide : `_dossiers` est lié au data/ réel
    du module, pas au répertoire temporaire du test. Ce qui compte ici est que
    la route répond 200 sans jeton.
    """
    r = client.get("/api/dossiers")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_sans_fichier_rbac_moi_le_dit(client):
    r = client.get("/api/rbac/moi")
    assert r.status_code == 200
    assert r.json()["actif"] is False


def test_sans_fichier_les_routes_admin_restent_ouvertes(client):
    """La liste des utilisateurs est ouverte : inutile de gérer qui que ce
    soit quand aucun cloisonnement n'existe."""
    r = client.get("/api/rbac/utilisateurs")
    assert r.status_code == 200
    assert r.json()["actif"] is False


def test_sans_fichier_les_jetons_inconnus_sont_ignores(client):
    """Un jeton fourni sans RBAC actif ne doit rien fermer ni rien ouvrir."""
    r = client.get("/api/dossiers", headers=_auth(client, "fantome"))
    assert r.status_code == 200


# ─────────────── le module, isolément ───────────────

def test_chargement_absent_est_inactif(tmp_path):
    assert RegistreRBAC.charger(tmp_path).actif is False


def test_role_inconnu_fait_echouer_le_chargement(tmp_path):
    (tmp_path / "rbac.json").write_text(json.dumps({"utilisateurs": [
        {"nom": "x", "jeton": "t", "roles": ["patron"]}]}), encoding="utf-8")
    with pytest.raises(RBACError, match="patron"):
        RegistreRBAC.charger(tmp_path)


def test_utilisateur_sans_role_est_refuse(tmp_path):
    """Un rôle vide = aucun droit. Configuration valide mais dangereuse."""
    (tmp_path / "rbac.json").write_text(json.dumps({"utilisateurs": [
        {"nom": "x", "jeton": "t", "roles": []}]}), encoding="utf-8")
    with pytest.raises(RBACError, match="sans rôle"):
        RegistreRBAC.charger(tmp_path)


def test_jeton_en_double_est_signale(tmp_path):
    (tmp_path / "rbac.json").write_text(json.dumps({"utilisateurs": [
        {"nom": "a", "jeton": "meme", "roles": ["lecteur"]},
        {"nom": "b", "jeton": "meme", "roles": ["lecteur"]}]}), encoding="utf-8")
    reg = RegistreRBAC.charger(tmp_path)
    assert reg.resoudre("meme") is not None   # le premier gagne


def test_jeton_absent_est_refuse(tmp_path):
    (tmp_path / "rbac.json").write_text(json.dumps({"utilisateurs": [
        {"nom": "x", "jeton": "", "roles": ["lecteur"]}]}), encoding="utf-8")
    with pytest.raises(RBACError, match="sans jeton"):
        RegistreRBAC.charger(tmp_path)


def test_liste_ne_divulgue_jamais_le_jeton(tmp_path):
    reg = RegistreRBAC.depuis({"utilisateurs": [
        {"nom": "a", "jeton": "secret-tres-long", "roles": ["lecteur"]}]})
    publique = reg.liste()
    assert "secret-tres-long" not in json.dumps(publique)
    assert publique[0]["nom"] == "a"


# ─────────────── hiérarchie des rôles ───────────────

def test_administrateur_couvre_tous_les_roles():
    u = Utilisateur(nom="a", roles=frozenset({ADMINISTRATEUR}))
    assert all(u.a_role(r) for r in (LECTEUR, OPERATEUR, SUPERVISEUR,
                                     ADMINISTRATEUR))


def test_operateur_ne_couvre_pas_superviseur():
    u = Utilisateur(nom="a", roles=frozenset({OPERATEUR}))
    assert u.a_role(OPERATEUR) and u.a_role(LECTEUR)
    assert not u.a_role(SUPERVISEUR)


def test_lecteur_ne_valide_pas():
    u = Utilisateur(nom="a", roles=frozenset({LECTEUR}))
    assert not u.a_role(OPERATEUR)


def test_role_demande_inconnu_leve():
    u = Utilisateur(nom="a", roles=frozenset({LECTEUR}))
    with pytest.raises(RBACError):
        u.a_role("patron")


# ─────────────── cloisonnement par dossier ───────────────

def test_portee_tous_voit_tout():
    u = Utilisateur(nom="a", roles=frozenset({LECTEUR}), dossiers=frozenset({TOUS}))
    assert u.voit_dossier("nimporte-lequel")


def test_portee_listee_ne_voit_que_ses_dossiers():
    u = Utilisateur(nom="a", roles=frozenset({LECTEUR}),
                    dossiers=frozenset({"D1", "D2"}))
    assert u.voit_dossier("D1") and not u.voit_dossier("D3")


def test_portee_vide_ne_voit_rien():
    """Échec fermé : un utilisateur sans affectation n'accède à rien."""
    u = Utilisateur(nom="a", roles=frozenset({LECTEUR}), dossiers=frozenset())
    assert not u.voit_dossier("D1")


# ─────────────── bout en bout, RBAC actif ───────────────

@pytest.fixture()
def client_rbac(tmp_cfg):
    """Client avec RBAC actif : lecteur, opérateur, superviseur, administrateur."""
    original = api._rbac
    _installe(tmp_cfg, [
        {"nom": "audit", "jeton": _jeton("audit"), "roles": ["lecteur"],
         "dossiers": ["*"]},
        {"nom": "marie", "jeton": _jeton("marie"), "roles": ["operateur"],
         "dossiers": ["D1"]},
        {"nom": "chef", "jeton": _jeton("chef"), "roles": ["superviseur"],
         "dossiers": ["*"]},
        {"nom": "admin", "jeton": _jeton("admin"), "roles": ["administrateur"],
         "dossiers": ["*"]},
    ])
    try:
        with TestClient(api.app) as c:
            yield c
    finally:
        api._rbac = original


def test_jeton_inconnu_est_refuse(client_rbac):
    r = client_rbac.get("/api/dossiers", headers=_auth(client_rbac, "inconnu"))
    assert r.status_code == 401
    assert "inconnu" in r.json()["detail"]


def test_sans_jeton_est_refuse(client_rbac):
    r = client_rbac.get("/api/dossiers")
    assert r.status_code == 401


def test_lecteur_voit_sa_propre_identite(client_rbac):
    r = client_rbac.get("/api/rbac/moi", headers=_auth(client_rbac, "audit"))
    assert r.status_code == 200
    corps = r.json()
    assert corps["actif"] is True and corps["nom"] == "audit"
    assert "jeton" not in json.dumps(corps)      # jamais de secret en sortie


def test_lecteur_ne_peut_pas_valider_un_champ(client_rbac):
    """Un auditeur consulte, il ne modifie pas les données métier."""
    r = client_rbac.patch("/api/jobs/j1/fields/invoice_number",
                          json={"confirmed_value": "X"},
                          headers=_auth(client_rbac, "audit"))
    assert r.status_code == 403
    assert "operateur" in r.json()["detail"]


def test_operateur_peut_creer_un_dossier(client_rbac):
    r = client_rbac.post("/api/dossiers", json={"label": "nouveau"},
                         headers=_auth(client_rbac, "marie"))
    assert r.status_code == 200


def test_operateur_ne_voit_que_son_dossier(client_rbac):
    """Marie a le périmètre D1 : elle ne voit que ce qu'elle crée.

    Son jeton la limite à D1, donc un dossier créé par un autre ne doit pas
    apparaître — d'où la comparaison avant/après.
    """
    avant = {d["id"] for d in client_rbac.get(
        "/api/dossiers", headers=_auth(client_rbac, "marie")).json()}
    cree = client_rbac.post("/api/dossiers", json={"label": "à marie"},
                            headers=_auth(client_rbac, "marie")).json()
    apres = {d["id"] for d in client_rbac.get(
        "/api/dossiers", headers=_auth(client_rbac, "marie")).json()}
    assert cree["id"] in apres
    assert apres - avant == {cree["id"]}


def test_cloisonnement_filtre_la_liste(client_rbac):
    """Un opérateur ne doit pas voir les dossiers des autres dans la liste."""
    client_rbac.post("/api/dossiers", json={"label": "de marie"},
                     headers=_auth(client_rbac, "marie"))
    ids_marie = {d["id"] for d in
                 client_rbac.get("/api/dossiers",
                                 headers=_auth(client_rbac, "marie")).json()}
    # un autre opérateur, périmètre restreint : il ne voit rien de tout ça.
    # Son jeton est généré par le registre — il faut le lire, pas le deviner.
    paul = api._rbac.ajouter("paul", ["operateur"], ["AUTRE"])
    r = client_rbac.get("/api/dossiers",
                        headers={"Authorization": "Bearer %s" % paul.jeton})
    assert r.status_code == 200
    vus = {d["id"] for d in r.json()}
    assert vus & ids_marie == set()


def test_dossier_hors_perimetre_est_refuse(client_rbac):
    d = client_rbac.post("/api/dossiers", json={"label": "de marie"},
                         headers=_auth(client_rbac, "marie")).json()
    paul = api._rbac.ajouter("paul", ["operateur"], ["AUTRE"])
    r = client_rbac.get("/api/dossiers/%s" % d["id"],
                        headers={"Authorization": "Bearer %s" % paul.jeton})
    assert r.status_code == 403


def test_refus_de_role_et_de_perimetre_sont_traces(client_rbac):
    client_rbac.patch("/api/jobs/j1/fields/invoice_number",
                      json={"confirmed_value": "X"},
                      headers=_auth(client_rbac, "audit"))
    client_rbac.post("/api/dossiers", json={"label": "x"},
                     headers=_auth(client_rbac, "audit"))  # interdit aussi
    journal = (api.cfg.log_dir / "audit.log").read_text(encoding="utf-8")
    assert "acces_refuse_role" in journal
    assert "acces_refuse_jeton" in journal or "acces_refuse_role" in journal


def test_seul_administrateur_gere_les_utilisateurs(client_rbac):
    r = client_rbac.get("/api/rbac/utilisateurs",
                        headers=_auth(client_rbac, "marie"))
    assert r.status_code == 403
    r = client_rbac.get("/api/rbac/utilisateurs",
                        headers=_auth(client_rbac, "admin"))
    assert r.status_code == 200
    assert "jeton" not in json.dumps(r.json())


def test_seul_administrateur_restaure(client_rbac):
    r = client_rbac.post("/api/backups/restore", json={"path": "x"},
                         headers=_auth(client_rbac, "chef"))
    assert r.status_code == 403     # superviseur, pas administrateur
    r = client_rbac.post("/api/backups/restore", json={"path": "x"},
                         headers=_auth(client_rbac, "admin"))
    assert r.status_code != 403     # l'administrateur, lui, passe


def test_lecteur_ne_peut_pas_lancer_la_purge_administrative(client_rbac):
    r = client_rbac.post("/api/admin/cleanup?dry_run=true",
                         headers=_auth(client_rbac, "audit"))
    assert r.status_code == 403


def test_lecteur_ne_peut_pas_corriger_une_classification(client_rbac):
    r = client_rbac.patch("/api/jobs/ghost/classification",
                          json={"category": "invoice"},
                          headers=_auth(client_rbac, "audit"))
    assert r.status_code == 403


@pytest.mark.parametrize(("method", "path", "body"), [
    ("POST", "/api/connectors/transmit", {}),
    ("PUT", "/api/connectors/demo_simulated/secrets", {}),
    ("PUT", "/api/profiles/custom", {}),
    ("PUT", "/api/watch", {}),
    ("POST", "/api/dossiers/D1/transmission", {}),
    ("POST", "/api/dossiers/D1/coherence", {}),
])
def test_lecteur_refuse_sur_les_routes_mutantes_sensibles(
        client_rbac, method, path, body):
    response = client_rbac.request(
        method, path, json=body, headers=_auth(client_rbac, "audit"))
    assert response.status_code == 403


def test_superviseur_arbitre_un_constat(client_rbac):
    """L'arbitrage est une décision de superviseur, pas d'opérateur.

    Le corps d'une arbitrage porte `status` (accepte / corrige / ignore), pas
    `decision` — c'est le nom de champ déjà en place dans l'API.
    """
    d = client_rbac.post("/api/dossiers", json={"label": "à arbitrer"},
                         headers=_auth(client_rbac, "admin")).json()
    corps = {"rule": "poids_divergent:gross_weight", "status": "accepte",
             "motif": "vérifié"}
    r = client_rbac.post("/api/dossiers/%s/coherence" % d["id"], json=corps,
                         headers=_auth(client_rbac, "marie"))
    assert r.status_code == 403     # opérateur : il travaille, il n'arbitre pas
    r = client_rbac.post("/api/dossiers/%s/coherence" % d["id"], json=corps,
                         headers=_auth(client_rbac, "chef"))
    assert r.status_code == 200


def test_jeton_regenerable_et_ancien_invalide(client_rbac):
    r = client_rbac.post("/api/rbac/utilisateurs/audit/jeton",
                         headers=_auth(client_rbac, "admin"))
    assert r.status_code == 200
    nouveau = r.json()["jeton"]
    assert nouveau and nouveau != _jeton("audit")
    # l'ancien jeton ne fonctionne plus
    r = client_rbac.get("/api/rbac/moi", headers=_auth(client_rbac, "audit"))
    assert r.status_code == 401
    r = client_rbac.get("/api/rbac/moi",
                        headers={"Authorization": "Bearer %s" % nouveau})
    assert r.status_code == 200


def test_creation_utilisateur_renvoie_le_jeton_une_fois(client_rbac):
    r = client_rbac.post("/api/rbac/utilisateurs",
                         json={"nom": "nouveau", "roles": ["lecteur"],
                               "dossiers": ["D9"]},
                         headers=_auth(client_rbac, "admin"))
    assert r.status_code == 200
    corps = r.json()
    assert corps["jeton"]
    # et il n'est plus relisible ensuite
    liste = client_rbac.get("/api/rbac/utilisateurs",
                            headers=_auth(client_rbac, "chef")).json()
    assert corps["jeton"] not in json.dumps(liste)


def test_suppression_revoque_immediatement(client_rbac):
    client_rbac.delete("/api/rbac/utilisateurs/audit",
                       headers=_auth(client_rbac, "admin"))
    r = client_rbac.get("/api/rbac/moi", headers=_auth(client_rbac, "audit"))
    assert r.status_code == 401


def test_jeton_environnement_est_passe_partout(client_rbac, monkeypatch):
    """Comportement historique conservé pour les scripts existants."""
    monkeypatch.setattr(api, "_AUTH_TOKEN", "master-secret")
    r = client_rbac.get("/api/rbac/moi",
                        headers={"Authorization": "Bearer master-secret"})
    assert r.status_code == 200
    assert r.json()["environnement"] is True
    assert r.json()["administrateur"] is True
    journal = (api.cfg.log_dir / "audit.log").read_text(encoding="utf-8")
    assert "acces_jeton_environnement" in journal


def test_createur_restreint_voit_son_dossier(client_rbac):
    """Un opérateur limité doit voir ce qu'il crée — et c'est tracé.

    C'est le défaut trouvé par les tests : sans extension du périmètre, un
    opérateur cantonné à « D1 » créait un dossier qu'il ne pouvait plus
    ouvrir, parce que l'identifiant est généré par le système.
    """
    r = client_rbac.post("/api/dossiers", json={"label": "de marie"},
                         headers=_auth(client_rbac, "marie"))
    assert r.status_code == 200
    cree = r.json()
    r = client_rbac.get("/api/dossiers/%s" % cree["id"],
                        headers=_auth(client_rbac, "marie"))
    assert r.status_code == 200
    journal = (api.cfg.log_dir / "audit.log").read_text(encoding="utf-8")
    assert "rbac_perimetre_etendu" in journal


def test_extension_ne_touche_pas_un_perimetre_ouvert(client_rbac):
    """À périmètre « tous », rien n'est étendu : il n'y a rien à étendre.

    Le journal peut ne pas exister du tout — c'est justement le signe qu'aucun
    événement de périmètre n'a été émis.
    """
    r = client_rbac.post("/api/dossiers", json={"label": "de l'admin"},
                         headers=_auth(client_rbac, "admin"))
    assert r.status_code == 200
    journal = api.cfg.log_dir / "audit.log"
    contenu = journal.read_text(encoding="utf-8") if journal.is_file() else ""
    assert "rbac_perimetre_etendu" not in contenu


# ─────────────── cloisonnement au niveau du document ───────────────

@pytest.fixture()
def client_jobs(tmp_cfg):
    """RBAC actif + un document classé dans plusieurs dossiers.

    Les identifiants de dossier sont générés par le système : les dossiers sont
    donc créés d'abord, puis les périmètres sont fixés d'après leurs identifiants
    réels. Écrire « D-MARIE » en dur ne matcherait rien.
    """
    original = api._rbac
    # `api._dossiers` est lié au data/ réel du module, pas au répertoire
    # temporaire : sans cette réaffectation, `_dossiers_du_job` ne trouverait
    # aucun des dossiers créés ici et la garde ne se déclencherait pas.
    original_dossiers = api._dossiers
    api._dossiers = DossierStore(tmp_cfg.data_dir / "dossiers",
                                 log_dir=tmp_cfg.log_dir)
    # `store.get()` exige un enregistrement de job ; un simple result.json ne
    # suffit pas et la route renverrait 404 avant même la garde.
    api.store.create_job("facture.pdf", b"%PDF-1.4 facture")
    job_id = api.store.list_jobs()[0].id
    api.store.save_result(job_id, {"job_id": job_id, "status": "done",
                                   "fields": {}})
    dossiers = api._dossiers
    ids: dict[str, str] = {}
    # le document n'est classé que dans les dossiers de marie. Paul a son propre
    # dossier, vide : sans cela il aurait un accès légitime au document et le
    # test ne prouverait rien.
    for etiquette, prop in (("de-marie", "marie"), ("de-marie-2", "marie")):
        d = dossiers.creer(etiquette, "personnalise", acteur=prop)
        dossiers.ajouter_piece(d.id, job_id, "facture.pdf",
                               category="facture", acteur=prop)
        ids[etiquette] = d.id
    ids["de-paul"] = dossiers.creer("de-paul", "personnalise",
                                    acteur="paul").id

    _installe(tmp_cfg, [
        {"nom": "marie", "jeton": _jeton("marie"), "roles": ["operateur"],
         "dossiers": [ids["de-marie"], ids["de-marie-2"]]},
        {"nom": "paul", "jeton": _jeton("paul"), "roles": ["operateur"],
         "dossiers": [ids["de-paul"]]},
        {"nom": "admin", "jeton": _jeton("admin"), "roles": ["administrateur"],
         "dossiers": ["*"]},
    ])
    try:
        with TestClient(api.app) as c:
            yield SimpleNamespace(client=c, job_id=job_id,
                                  dossiers=ids)
    finally:
        api._rbac = original
        api._dossiers = original_dossiers


def test_document_lisible_par_son_proprietaire(client_jobs):
    """Le contournement par /api/jobs est fermé, sans bloquer le propriétaire.

    C'est le défaut trouvé en conditions réelles : `GET /api/jobs/{id}/result`
    renvoyait l'intégralité d'un document sans passer par la route du dossier.
    """
    for route in ("", "/result", "/fields", "/text", "/quality", "/tables"):
        r = client_jobs.client.get("/api/jobs/" + client_jobs.job_id + route,
                            headers=_auth(client_jobs.client, "marie"))
        assert r.status_code == 200, route


def test_document_illisible_hors_perimetre(client_jobs):
    """Un opérateur sans aucun dossier visible ne lit rien du document."""
    for route in ("", "/result", "/fields", "/text", "/quality", "/tables"):
        r = client_jobs.client.get("/api/jobs/" + client_jobs.job_id + route,
                            headers=_auth(client_jobs.client, "paul"))
        assert r.status_code == 403, route


def test_suppression_refusee_hors_perimetre(client_jobs):
    """Supprimer le document d'autrui est un accès en écriture : refusé."""
    r = client_jobs.client.delete("/api/jobs/" + client_jobs.job_id,
                           headers=_auth(client_jobs.client, "paul"))
    assert r.status_code == 403


def test_correction_classification_refusee_hors_perimetre(client_jobs):
    r = client_jobs.client.patch(
        "/api/jobs/" + client_jobs.job_id + "/classification",
        json={"category": "invoice"},
        headers=_auth(client_jobs.client, "paul"))
    assert r.status_code == 403


def test_test_profil_refuse_un_document_hors_perimetre(client_jobs):
    r = client_jobs.client.post(
        "/api/profiles/test",
        json={"profile": "generic", "job_id": client_jobs.job_id},
        headers=_auth(client_jobs.client, "paul"))
    assert r.status_code == 403


def test_document_hors_perimetre_ne_peut_pas_etre_attache_a_un_dossier(
        client_jobs):
    dossier_id = client_jobs.dossiers["de-paul"]
    r = client_jobs.client.post(
        f"/api/dossiers/{dossier_id}/pieces",
        json={"job_id": client_jobs.job_id},
        headers=_auth(client_jobs.client, "paul"))
    assert r.status_code == 403


def test_formulaire_refuse_hors_perimetre(client_jobs, monkeypatch, tmp_path):
    from unocr.formulaire import FormulaireDossier, FormulaireStore

    store = FormulaireStore(tmp_path / "formulaires")
    monkeypatch.setattr(api, "_formulaires", store)
    dossier_id = client_jobs.dossiers["de-marie"]
    store.sauve(FormulaireDossier(formulaire_id="frm_private",
                                  dossier_id=dossier_id,
                                  label="données privées"))
    r = client_jobs.client.get("/api/formulaires/frm_private",
                              headers=_auth(client_jobs.client, "paul"))
    assert r.status_code == 403


def test_refus_de_document_est_trace(client_jobs):
    client_jobs.client.get("/api/jobs/" + client_jobs.job_id + "/result",
                    headers=_auth(client_jobs.client, "paul"))
    journal = api.cfg.log_dir / "audit.log"
    contenu = journal.read_text(encoding="utf-8") if journal.is_file() else ""
    assert "acces_refuse_document" in contenu


def test_document_multi_classe_reste_lisible(client_jobs):
    """Un document classé dans plusieurs dossiers reste lisible.

    **Pourquoi ce test.** Ma première implémentation refusait dès qu'*un* seul
    dossier contenant le document était hors périmètre. Un document classé dans
    quatre dossiers, dont trois à soi, devenait illisible — y compris pour son
    propriétaire. La règle correcte est « au moins un dossier visible ».
    """
    # le document est dans D-MARIE, D-MARIE-2 (visibles) et D-PAUL (non visible)
    r = client_jobs.client.get("/api/jobs/" + client_jobs.job_id + "/result",
                        headers=_auth(client_jobs.client, "marie"))
    assert r.status_code == 200


def test_document_non_classe_regi_par_le_role(client_jobs):
    """Un document qui n'appartient à aucun dossier n'est pas cloisonnable.

    Limite assumée et documentée : sans dossier, il n'y a personne à qui
    attribuer le document. Le rôle, lui, s'applique toujours.
    """
    libre = api.store.create_job("note.pdf", b"%PDF-1.4 note")
    api.store.save_result(libre.id, {"job_id": libre.id, "status": "done",
                                     "fields": {}})
    r = client_jobs.client.get("/api/jobs/" + libre.id,
                               headers=_auth(client_jobs.client, "paul"))
    assert r.status_code == 200


def test_listes_recherche_revue_et_export_respectent_le_perimetre(client_jobs):
    from unocr.models import JobStatus

    job = api.store.get(client_jobs.job_id)
    job.status = JobStatus.DONE
    api.store.update(job)
    api.store.save_result(job.id, {
        "job_id": job.id,
        "fields": {"reference": {"raw_value": "SCOPE-CANARY",
                                  "confidence": 0.1, "status": "invalid"}},
        "pages": [{"page_num": 1, "text": "SCOPE-CANARY"}],
    })
    headers = _auth(client_jobs.client, "paul")

    jobs = client_jobs.client.get("/api/jobs", headers=headers).json()
    review = client_jobs.client.get("/api/review?threshold=1", headers=headers).json()
    search = client_jobs.client.get("/api/search?q=SCOPE-CANARY",
                                    headers=headers).json()
    export = client_jobs.client.get(
        "/api/batches/export/json?ids=" + job.id, headers=headers)

    assert all(item["id"] != job.id for item in jobs)
    assert all(item["job_id"] != job.id for item in review["items"])
    assert all(item.get("job_id") != job.id for item in search["hits"])
    assert export.status_code == 403
