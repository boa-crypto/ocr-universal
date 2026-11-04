"""Étape 15 — archivage et traçabilité, vus par l'API.

**Pourquoi ce fichier.** Le module `unocr.tracabilite` est testé en direct
contre le store (`tests/test_tracabilite.py`). Ce qui reste à prouver, c'est
que les **routes** le servent sans le dénaturer : qu'un archivage aboutisse,
qu'un double archivage soit refusé, et surtout que **toute** réponse de trace
porte l'avertissement sur ce que le journal est. Une trace servie sans son
avertissement serait une régression grave, pas un détail de présentation.

Le magasin est isolé par test (même méthode que test_parcours_bout_en_bout).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.usefixtures("tmp_cfg")


@pytest.fixture()
def client(tmp_cfg, tmp_path):
    """Client d'API avec magasin de dossiers isolé."""
    from unocr import api
    from unocr.dossier import DossierStore

    api._watch.stop()
    api._watch.reset()
    api._dossiers = DossierStore(tmp_path / "dossiers", log_dir=tmp_path / "logs")
    with TestClient(api.app) as c:
        yield c
    api._watch.stop()
    api._watch.reset()


def _job_factice(client, job_id: str, filename: str = "facture.pdf") -> None:
    """Crée un enregistrement de document dans le magasin.

    L'ajout d'une pièce à un dossier exige que le document existe. On n'a pas
    besoin du pipeline OCR ici — un enregistrement suffit, et il évite de
    dépendre d'un moteur absent.
    """
    from unocr import api
    from unocr.models import Job, JobStatus

    # job_dir() ne crée pas le répertoire, et l'écriture est atomique via un
    # fichier .tmp voisin : sans le mkdir, elle échoue.
    api.store.job_dir(job_id).mkdir(parents=True, exist_ok=True)
    api.store.update(Job(id=job_id, filename=filename, status=JobStatus.DONE))


def _cree(client, label: str = "Dossier traçabilité") -> str:
    r = client.post("/api/dossiers", json={"label": label,
                                          "profile": "importation"})
    assert r.status_code == 200, r.text
    return r.json()["id"]


# ─────────────────────────────── archivage ───────────────────────────────

def test_archiver_change_l_etat_sans_supprimer(client) -> None:
    did = _cree(client)
    _job_factice(client, "job_x")
    r = client.post(f"/api/dossiers/{did}/pieces", json={
        "job_id": "job_x", "filename": "facture.pdf", "category": "invoice"})
    assert r.status_code == 200, r.text

    r = client.post(f"/api/dossiers/{did}/archiver",
                    json={"motif": "dossier clos"})
    assert r.status_code == 200, r.text
    corps = r.json()
    assert corps["state"] == "archive"
    # rien n'a disparu : les pièces sont toujours là
    assert len(corps["pieces"]) == 1
    assert corps["pieces"][0]["filename"] == "facture.pdf"

    apres = client.get(f"/api/dossiers/{did}").json()
    assert apres["state"] == "archive"
    assert len(apres["pieces"]) == 1


def test_archiver_sans_motif_est_accepte(client) -> None:
    did = _cree(client)
    r = client.post(f"/api/dossiers/{did}/archiver")
    assert r.status_code == 200, r.text
    assert r.json()["state"] == "archive"


def test_double_archivage_est_refuse(client) -> None:
    did = _cree(client)
    assert client.post(f"/api/dossiers/{did}/archiver").status_code == 200
    r = client.post(f"/api/dossiers/{did}/archiver")
    assert r.status_code == 409
    assert "archivé" in r.json()["detail"]


def test_archivage_survit_a_une_relecture_du_dossier(client) -> None:
    """Consulter un dossier archivé ne doit pas le désarchiver.

    `recalculer_etat` déduit l'état des faits. Appliqué sans garde à un dossier
    archivé, il le faisait revenir « incomplet » au simple fait de l'afficher :
    l'archivage ne tenait donc qu'aussi longtemps qu'on ne regardait pas.
    """
    did = _cree(client)
    assert client.post(f"/api/dossiers/{did}/archiver").status_code == 200

    apres = client.get(f"/api/dossiers/{did}").json()
    assert apres["state"] == "archive", (
        "une simple consultation a désarchivé le dossier"
    )
    # et la relecture ne doit pas non plus écrire un changement d'état fantôme
    corps = client.get(f"/api/dossiers/{did}/trace").json()
    retours = [e for e in corps["entrees"] if e["event"] == "dossier_state_changed"]
    assert not retours, "la consultation a journalisé un changement d'état"


def test_archiver_un_dossier_inconnu_renvoie_404(client) -> None:
    r = client.post("/api/dossiers/dossier_absent/archiver")
    assert r.status_code == 404


def test_archivage_signale_les_pieces_manquantes(client) -> None:
    """Un dossier incomplet est archivable, mais il doit le dire.

    L'archivage ne crée rien : le mentionner est la seule façon de ne pas
    laisser croire qu'un dossier archivé est un dossier complet.
    """
    did = _cree(client)
    r = client.post(f"/api/dossiers/{did}/archiver")
    assert r.status_code == 200
    assert r.json()["avertissements_archivage"], (
        "un dossier vide archivé sans avertissement laisse croire qu'il est "
        "complet"
    )


# ─────────────────────────────── traçabilité ───────────────────────────────

def test_trace_portee_par_la_reponse(client) -> None:
    did = _cree(client)
    r = client.get(f"/api/dossiers/{did}/trace")
    assert r.status_code == 200
    corps = r.json()
    assert corps["total"] >= 1
    evenements = [e["event"] for e in corps["entrees"]]
    assert "dossier_created" in evenements
    # la chronologie est ascendante
    horodatages = [e["ts"] for e in corps["entrees"]]
    assert horodatages == sorted(horodatages)


def test_trace_contient_l_archivage(client) -> None:
    did = _cree(client)
    client.post(f"/api/dossiers/{did}/archiver", json={"motif": "clos"})
    corps = client.get(f"/api/dossiers/{did}/trace").json()
    assert "dossier_archived" in corps["compteurs"]
    assert corps["etat"] == "archive"


def test_trace_d_un_dossier_inconnu_renvoie_404(client) -> None:
    assert client.get("/api/dossiers/dossier_absent/trace").status_code == 404


def test_toute_trace_porte_l_avertissement(client) -> None:
    """Contrainte structurante : l'avertissement n'est jamais optionnel.

    Il est présent sur chaque réponse de trace, même quand le journal est
    vide, même quand le dossier vient d'être créé. Le déplacer dans une page
    d'aide ou derrière un repli serait une régression, pas un gain de place.
    """
    did = _cree(client)
    corps = client.get(f"/api/dossiers/{did}/trace").json()
    avertissement = corps["avertissement"]
    assert "inviolable" in avertissement
    assert "administrateur" in avertissement
    assert "modifier" in avertissement
    # et il dit aussi ce que l'archivage garantit, et ce qu'il ne garantit pas
    assert corps["garanties"]
    assert corps["limites"]
    assert any("inaltérable" in limite for limite in corps["limites"])
    # aucun mot de garantie absolue dans ce qu'on PROMET
    promesses = " ".join(corps["garanties"]).lower()
    for mot in ("inviolable", "inaltérable", "infalsifiable", "preuve"):
        assert mot not in promesses, (
            f"le mot « {mot} » promet ce que l'archivage ne tient pas"
        )


def test_endpoint_avertissement_expose_garanties_et_limites(client) -> None:
    r = client.get("/api/tracabilite/avertissement")
    assert r.status_code == 200
    corps = r.json()
    assert corps["avertissement"]
    assert len(corps["garanties"]) >= 3
    assert len(corps["limites"]) >= 3
    # aucune garantie ne doit promettre l'inviolabilité
    promesses = " ".join(corps["garanties"]).lower()
    for mot in ("inviolable", "inaltérable", "infalsifiable", "preuve"):
        assert mot not in promesses, (
            f"le mot « {mot} » promet ce que l'archivage ne tient pas"
        )
    # à l'inverse, une limite DOIT dire ce que l'archivage ne fait pas
    assert any("preuve" in limite for limite in corps["limites"]), (
        "les limites doivent dire que l'archivage n'est pas une preuve"
    )


def test_trace_distingue_etat_deduit_et_etat_force(client) -> None:
    """Un état posé par un humain doit rester visible comme tel.

    C'est la seule façon de voir qu'un dossier a été forcé « valide » alors
    que ses pièces montraient le contraire.
    """
    did = _cree(client)
    client.post(f"/api/dossiers/{did}/state",
                json={"state": "valide", "motif": "contrôle"})
    corps = client.get(f"/api/dossiers/{did}/trace").json()
    acteurs = [e["detail"].get("acteur")
               for e in corps["entrees"] if e["event"] == "dossier_state_forced"]
    assert acteurs and all(a == "utilisateur" for a in acteurs), (
        "un état forcé doit être attribué à un humain, pas au système"
    )
