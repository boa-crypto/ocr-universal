"""Transitions terminal : refus persistants, pas seulement boutons masqués."""
import pytest

PLAN = {"date_planifiee": "2026-11-05", "transporteur_id": "trans",
        "camion_id": "cam", "chauffeur_id": "ch", "immatriculation": "123",
        "chauffeur_nom": "Nom", "chauffeur_permis": "P"}
AUTORISATION = {"mainlevee_obtenue": True, "bad_obtenu": True,
                "frais_portuaires_payes": True, "justificatif_sortie": "JUSTIF"}


def creer(client):
    rep = client.post("/api/terminal", json={"dossier_id": "dos_test", "numero_bl": "BL",
                                            "numero_conteneur": "CONT"})
    assert rep.status_code == 200
    return "/api/terminal/" + rep.json()["id"]


@pytest.mark.parametrize("action,params", [
    ("sortie", {"date_sortie": "2026-11-06"}),
    ("autoriser_sortie", AUTORISATION),
])
def test_pas_de_saut_depuis_demande(client_factory, action, params):
    with client_factory() as client:
        url = creer(client)
        avant = client.get(url).json()
        assert client.post(url + "/" + action, params=params).status_code == 409
    with client_factory() as client:
        assert client.get(url).json() == avant


@pytest.mark.parametrize("corps", [
    {"statut": "sortis"}, {"date_sortie": "2026-11-06"},
    {"justificatif_sortie": "contournement"}, {"statut": "sortie_autorisee"},
])
def test_put_ne_contourne_pas_workflow(client_factory, corps):
    with client_factory() as client:
        url = creer(client)
        avant = client.get(url).json()
        assert client.put(url, json=corps).status_code == 409
    with client_factory() as client:
        assert client.get(url).json() == avant


@pytest.mark.parametrize("champ,valeur,code", [
    ("mainlevee_obtenue", False, 400), ("bad_obtenu", False, 400),
    ("frais_portuaires_payes", False, 400), ("justificatif_sortie", "  ", 422),
])
def test_autorisation_incomplete_refusee(client_factory, champ, valeur, code):
    with client_factory() as client:
        url = creer(client)
        assert client.post(url + "/planifier", params=PLAN).status_code == 200
        avant = client.get(url).json()
        rep = client.post(url + "/autoriser_sortie", params={**AUTORISATION, champ: valeur})
        assert rep.status_code == code, rep.text
    with client_factory() as client:
        assert client.get(url).json() == avant


@pytest.mark.parametrize("champ,valeur", [("date_planifiee", "2026-W45-3"), ("chauffeur_permis", "  ")])
def test_planification_invalide_refusee(client_factory, champ, valeur):
    with client_factory() as client:
        url = creer(client)
        assert client.post(url + "/planifier", params={**PLAN, champ: valeur}).status_code == 422
        assert client.get(url).json()["statut"] == "demande"


def test_apres_autorisation_preuves_figees_et_pas_de_retour(client_factory):
    with client_factory() as client:
        url = creer(client)
        assert client.post(url + "/planifier", params=PLAN).status_code == 200
        assert client.post(url + "/autoriser_sortie", params=AUTORISATION).status_code == 200
        assert client.put(url, json={"mainlevee_obtenue": False}).status_code == 409
        assert client.put(url, json={"numero_conteneur": "AUTRE"}).status_code == 409
        assert client.post(url + "/planifier", params=PLAN).status_code == 409
        assert client.post(url + "/sortie", params={"date_sortie": "2026-99-99"}).status_code == 422
        assert client.get(url).json()["statut"] == "sortie_autorisee"
        assert client.post(url + "/sortie", params={"date_sortie": "2026-11-06"}).status_code == 200
    with client_factory() as client:
        avant = client.get(url).json()
        assert client.post(url + "/sortie", params={"date_sortie": "2026-11-07"}).status_code == 409
        assert client.post(url + "/autoriser_sortie", params=AUTORISATION).status_code == 409
        assert client.get(url).json() == avant
        assert client.put(url, json={"observations": "Note après sortie"}).status_code == 200
        assert client.get(url).json()["statut"] == "sortis"


def test_creation_ne_peut_pas_declarer_une_sortie(client_factory):
    with client_factory() as client:
        rep = client.post("/api/terminal", json={"dossier_id": "dos_test", "numero_bl": "BL",
                                                "numero_conteneur": "CONT", "statut": "sortis"})
        assert rep.status_code == 409
        assert client.get("/api/terminal").json() == []


def test_null_invalide_est_422_pas_500(client_factory):
    with client_factory() as client:
        url = creer(client)
        assert client.put(url, json={"numero_bl": None}).status_code == 422
        assert client.get(url).json()["numero_bl"] == "BL"


def test_refus_trace_dans_audit(client_factory, tmp_path):
    with client_factory() as client:
        url = creer(client)
        assert client.post(url + "/sortie", params={"date_sortie": "2026-11-06"}).status_code == 409
    journal = (tmp_path / "logs/audit.log").read_text(encoding="utf-8")
    assert "enlevement_transition_refusee" in journal
    assert url.rsplit("/", 1)[1] in journal
