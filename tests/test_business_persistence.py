"""Les tests métier écrivent uniquement dans tmp_path, jamais dans data/."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from unocr.business_store import BusinessStore
from unocr.models import DeclarationDouaniere


@pytest.mark.parametrize("route,corps,champ_id,modification", [
    ("/api/declarations", {"dossier_id": "dos_test", "numero_declaration": "D-1"},
     "id", {"statut": "deposee"}),
    ("/api/declarations/liquidation", {"dossier_id": "dos_test", "declaration_id": "decl_test"},
     "id", {"tva": 120.5}),
    ("/api/terminal", {"dossier_id": "dos_test", "numero_bl": "BL-1", "numero_conteneur": "CONT-1"},
     "id", {"observations": "mise à jour"}),
])
def test_crud_apres_nouvelle_application(client_factory, route, corps, champ_id, modification):
    client = client_factory()
    creation = client.post(route, json=corps)
    assert creation.status_code == 200, creation.text
    identifiant = creation.json()[champ_id]
    client.close()
    with client_factory() as client:
        lecture = client.get(f"{route}/{identifiant}")
        assert lecture.status_code == 200, lecture.text
        assert lecture.json()["dossier_id"] == "dos_test"
        assert client.put(f"{route}/{identifiant}", json=modification).status_code == 200
    with client_factory() as client:
        lecture = client.get(f"{route}/{identifiant}").json()
        for cle, valeur in modification.items():
            assert lecture[cle] == valeur
        assert client.delete(f"{route}/{identifiant}").status_code == 200
    with client_factory() as client:
        assert client.get(f"{route}/{identifiant}").status_code == 404
        assert client.get(route).json() == []


def test_workflow_terminal_persiste(client_factory):
    with client_factory() as client:
        identifiant = client.post("/api/terminal", json={
            "dossier_id": "dos_test", "numero_bl": "BL", "numero_conteneur": "CONT"
        }).json()["id"]
        url = f"/api/terminal/{identifiant}"
        rep = client.post(url + "/planifier", params={
            "date_planifiee": "2026-11-05", "transporteur_id": "trans_test",
            "camion_id": "cam_test", "chauffeur_id": "ch_test", "immatriculation": "123",
            "chauffeur_nom": "Nom", "chauffeur_permis": "P"
        })
        assert rep.status_code == 200, rep.text
    with client_factory() as client:
        assert client.get(url).json()["statut"] == "planifie"
        params = {"mainlevee_obtenue": True, "bad_obtenu": True,
                  "frais_portuaires_payes": True, "justificatif_sortie": "JUSTIF"}
        assert client.post(url + "/autoriser_sortie", params=params).status_code == 200
    with client_factory() as client:
        assert client.get(url).json()["statut"] == "sortie_autorisee"
        assert client.post(url + "/sortie", params={"date_sortie": "2026-11-06"}).status_code == 200
    with client_factory() as client:
        assert client.get(url).json()["statut"] == "sortis"
        assert client.get(url).json()["date_sortie"] == "2026-11-06"


def test_lecture_est_une_copie_et_collections_isolees(tmp_path):
    path = tmp_path / "metier.sqlite3"
    store = BusinessStore(path, "declaration", DeclarationDouaniere)
    objet = DeclarationDouaniere(id="decl_test", dossier_id="dos_test")
    store[objet.id] = objet
    copie = store[objet.id]
    copie.statut = "rejetee"
    assert store[objet.id].statut != "rejetee"
    assert len(BusinessStore(path, "autre", DeclarationDouaniere)) == 0
    assert list(store) == [objet.id]
    assert len(store) == 1
    with pytest.raises(KeyError):
        del store["inconnu"]


def test_date_et_agent_non_perdus(client_factory):
    with client_factory() as client:
        rep = client.post("/api/declarations", json={
            "dossier_id": "dos_test", "date_depot": "2026-11-04", "agent_declarant": "Agent"
        })
        assert rep.status_code == 200, rep.text
        identifiant = rep.json()["id"]
    with client_factory() as client:
        rep = client.get(f"/api/declarations/{identifiant}").json()
        assert rep["date_depot"] == "2026-11-04"
        assert rep["agent_declarant"] == "Agent"
    ancien = DeclarationDouaniere.model_validate({"date_depôt": "2026-01-01", "agent_declarat": "Ancien"})
    assert ancien.date_depot == "2026-01-01" and ancien.agent_declarant == "Ancien"


def test_sauvegarde_restauration_metier(tmp_path):
    from unocr.backup import BackupError, creer_sauvegarde, restaurer_sauvegarde

    cfg = SimpleNamespace(data_dir=tmp_path / "data", log_dir=tmp_path / "logs")
    store = BusinessStore(cfg.data_dir / "metier.sqlite3", "declaration", DeclarationDouaniere)
    store["decl_test"] = DeclarationDouaniere(id="decl_test", dossier_id="dos_test")
    sauvegarde = creer_sauvegarde(cfg)
    autre = SimpleNamespace(data_dir=tmp_path / "restaure", log_dir=tmp_path / "autres_logs")
    restaurer_sauvegarde(autre, sauvegarde.chemin)
    nouveau = BusinessStore(autre.data_dir / "metier.sqlite3", "declaration", DeclarationDouaniere)
    assert nouveau["decl_test"].dossier_id == "dos_test"
    with pytest.raises(BackupError, match="magasin non vide"):
        restaurer_sauvegarde(autre, sauvegarde.chemin)


def test_lecture_autre_processus(tmp_path):
    import os
    import subprocess
    import sys

    path = tmp_path / "metier.sqlite3"
    store = BusinessStore(path, "declaration", DeclarationDouaniere)
    store["decl_processus"] = DeclarationDouaniere(id="decl_processus", dossier_id="dos_persistant")
    code = (
        "from pathlib import Path; from unocr.business_store import BusinessStore; "
        "from unocr.models import DeclarationDouaniere; "
        f"s=BusinessStore(Path({str(path)!r}), 'declaration', DeclarationDouaniere); "
        "assert s['decl_processus'].dossier_id == 'dos_persistant'"
    )
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
    subprocess.run([sys.executable, "-c", code], env=env, check=True, timeout=30)


def test_objet_invalide_ne_remplace_pas_la_version_persistante(tmp_path):
    from pydantic import ValidationError

    store = BusinessStore(tmp_path / "metier.sqlite3", "declaration", DeclarationDouaniere)
    original = DeclarationDouaniere(id="decl_test", dossier_id="dos_test")
    store[original.id] = original
    copie = store[original.id]
    copie.statut = None  # affectation non validée par le modèle historique
    with pytest.raises(ValidationError):
        store[original.id] = copie
    assert store[original.id].statut == "en_preparation"
