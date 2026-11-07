"""Routes OCR de dossiers : stores réels temporaires, pas moteur OCR exécuté."""
import hashlib

import pytest
from fastapi.testclient import TestClient

from unocr import api, ocr_integration
from unocr.models import ChampExtrait, DocumentResult, FieldValue
from unocr.ocr_integration import OCRTransitIntegration
from unocr.rbac import RegistreRBAC
from unocr.routes import documents_ocr as routes

ACTIONS = ["list", "get", "update", "validate", "correct", "classify", "create"]
DETAIL = ["get", "update", "validate", "correct"]


def headers(user="a"):
    return {"Authorization": "Bearer FAKE73-" + user}


def perform(client, folder, extraction, job, action, user="a", body_folder=None):
    root = f"/api/dossiers/{folder}/documents-ocr"
    opts = {"headers": headers(user)}
    if action == "list":
        return client.get(root, **opts)
    if action == "get":
        return client.get(root + "/" + extraction, **opts)
    if action == "update":
        return client.put(root + "/" + extraction, json={"statut": "corrected"}, **opts)
    if action == "validate":
        return client.post(root + "/" + extraction + "/valider", **opts)
    if action == "correct":
        return client.post(root + "/" + extraction + "/corriger", json={"champ_nom": "sample", "nouvelle_valeur": "CORRECT73"}, **opts)
    if action == "classify":
        return client.post(root + "/auto-classifier", **opts)
    return client.post(root, json={"dossier_id": body_folder or folder, "job_id": job, "type_document": "generic"}, **opts)


@pytest.fixture
def scoped(tmp_cfg, monkeypatch):
    folders = {key: api._dossiers.creer(key, "personnalise").id for key in ("a", "b", "a2")}
    users = [{"nom": user, "jeton": "FAKE73-" + user, "roles": [role], "dossiers": ids}
             for user, role, ids in [("a", "operateur", [folders["a"], folders["a2"]]),
                                     ("b", "operateur", [folders["b"]]),
                                     ("reader", "lecteur", [folders["a"]]),
                                     ("admin", "administrateur", ["*"])]]
    monkeypatch.setattr(api, "_rbac", RegistreRBAC.depuis({"utilisateurs": users}))
    monkeypatch.setattr(api, "_AUTH_TOKEN", "FAKE73-master")
    monkeypatch.setattr(ocr_integration, "cfg", tmp_cfg)
    integration = OCRTransitIntegration(tmp_cfg.data_dir)
    monkeypatch.setattr(routes, "get_ocr_integration", lambda: integration)
    jobs, extractions = {}, {}
    for key in ("a", "b"):
        job = api.store.create_job(key + ".txt", key.encode())
        api.store.save_result(job.id, DocumentResult(source_file=key + ".txt", fields={
            "sample": FieldValue(name="sample", raw_value="PRIVATE73", confidence=0.2)}).model_dump(mode="json"))
        api._dossiers.ajouter_piece(folders[key], job.id, key + ".txt", category="generic")
        extraction = integration.extraction_store.creer(dossier_id=folders[key], document_id=job.id,
            type_document="generic", texte_complet="PRIVATE73", champs_extraits=[ChampExtrait(nom="sample", valeur_raw="PRIVATE73")])
        jobs[key], extractions[key] = job.id, extraction.id
    with TestClient(api.app) as client:
        yield client, folders, jobs, extractions, integration, tmp_cfg


def snapshot(cfg):
    return {str(p.relative_to(cfg.data_dir)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in cfg.data_dir.rglob("*.json")}


@pytest.mark.parametrize("action", ACTIONS)
def test_hidden_dossier_refused_before_integration(scoped, monkeypatch, action):
    client, f, j, e, integration, cfg = scoped
    before = snapshot(cfg)
    def forbidden():
        raise AssertionError("accès intégration avant autorisation")
    monkeypatch.setattr(routes, "get_ocr_integration", forbidden)
    response = perform(client, f["b"], e["b"], j["b"], action)
    assert response.status_code == 403
    assert "PRIVATE73" not in response.text
    assert snapshot(cfg) == before
    assert "acces_refuse_dossier" in (cfg.log_dir / "audit.log").read_text()


@pytest.mark.parametrize("action", DETAIL)
@pytest.mark.parametrize("folder", ["a", "a2"])
def test_wrong_extraction_cannot_be_read_or_mutated_under_visible_dossier(scoped, action, folder):
    client, f, j, e, integration, cfg = scoped
    before = snapshot(cfg)
    response = perform(client, f[folder], e["b"], j["a"], action)
    assert response.status_code == 403
    assert "PRIVATE73" not in response.text
    assert snapshot(cfg) == before
    assert integration.extraction_store.get(e["b"]).statut == "extracted"


@pytest.mark.parametrize("action", ACTIONS)
def test_visible_document_operations_still_work(scoped, action):
    client, f, j, e, integration, cfg = scoped
    response = perform(client, f["a"], e["a"], j["a"], action)
    assert response.status_code == 200, response.text
    if action == "validate":
        assert integration.extraction_store.get(e["a"]).statut == "validated"
    if action == "correct":
        assert integration.extraction_store.get(e["a"]).champs_extraits[0].valeur_confirmee == "CORRECT73"
    if action == "create":
        assert response.json()["dossier_id"] == f["a"]
        assert response.json()["document_id"] == j["a"]
        assert response.json()["champs_extraits"][0]["valeur_raw"] == "PRIVATE73"


@pytest.mark.parametrize("action", ["update", "validate", "correct", "classify", "create"])
def test_reader_cannot_write(scoped, action):
    client, f, j, e, integration, cfg = scoped
    before = snapshot(cfg)
    assert perform(client, f["a"], e["a"], j["a"], action, "reader").status_code == 403
    assert snapshot(cfg) == before


@pytest.mark.parametrize("action", ["list", "get"])
def test_reader_can_read_visible_dossier(scoped, action):
    client, f, j, e, _, _ = scoped
    assert perform(client, f["a"], e["a"], j["a"], action, "reader").status_code == 200


def test_create_rejects_hidden_source_job_before_reading_result(scoped, monkeypatch):
    client, f, j, e, _, cfg = scoped
    before = snapshot(cfg)
    def forbidden(*args):
        raise AssertionError("lecture résultat hors périmètre")
    monkeypatch.setattr(api.store, "load_result", forbidden)
    assert perform(client, f["a"], e["a"], j["b"], "create").status_code == 403
    assert snapshot(cfg) == before


def test_create_body_and_path_dossier_must_match(scoped):
    client, f, j, e, _, cfg = scoped
    before = snapshot(cfg)
    assert perform(client, f["a"], e["a"], j["a"], "create", body_folder=f["a2"]).status_code == 422
    assert snapshot(cfg) == before


@pytest.mark.parametrize("action", DETAIL)
def test_missing_extraction_still_404_in_authorized_dossier(scoped, action):
    client, f, j, _, _, _ = scoped
    assert perform(client, f["a"], "ocr_absent", j["a"], action).status_code == 404


@pytest.mark.parametrize("action", ACTIONS)
def test_unknown_token_refused(scoped, action):
    client, f, j, e, _, cfg = scoped
    before = snapshot(cfg)
    assert perform(client, f["a"], e["a"], j["a"], action, "unknown").status_code == 401
    assert snapshot(cfg) == before


@pytest.mark.parametrize("who", ["admin", "master"])
@pytest.mark.parametrize("action", ["get", "validate", "correct", "create"])
def test_existing_privileged_access_preserved(scoped, who, action):
    client, f, j, e, _, _ = scoped
    assert perform(client, f["b"], e["b"], j["b"], action, who).status_code == 200


@pytest.mark.parametrize("model_name", ["ChampExtrait", "ExtractionOCR"])
def test_ocr_timestamps_are_callable_defaults_at_creation(monkeypatch, model_name):
    from unocr import models

    monkeypatch.setattr(models.time, "strftime", lambda *args: "NOW73")
    assert getattr(models, model_name)().cree_le == "NOW73"


def test_integration_consumes_checked_result_without_reading_another_store(scoped, monkeypatch):
    from unocr.storage import JobStore

    _, f, j, _, integration, _ = scoped
    checked = api.store.load_result(j["a"])
    def forbidden(*args):
        raise AssertionError("nouvelle lecture globale non autorisée")
    monkeypatch.setattr(JobStore, "load_result", forbidden)
    result = integration.process_job_result(j["a"], f["a"], "generic", result_json=checked)
    assert result.document_id == j["a"] and result.dossier_id == f["a"]
    assert result.champs_extraits[0].valeur_raw == "PRIVATE73"


@pytest.mark.parametrize("membership", ["shared", "unclassified"])
def test_create_keeps_existing_job_visibility_policy(scoped, membership):
    client, f, j, e, _, _ = scoped
    if membership == "shared":
        api._dossiers.ajouter_piece(f["a"], j["b"], "shared.txt", category="generic")
        job = j["b"]
    else:
        record = api.store.create_job("unclassified.txt", b"synthetic")
        api.store.save_result(record.id, DocumentResult().model_dump(mode="json"))
        job = record.id
    assert perform(client, f["a"], e["a"], job, "create").status_code == 200


@pytest.mark.parametrize("action", ["get", "validate", "correct", "create"])
def test_rbac_disabled_does_not_activate_implicit_permissions(scoped, monkeypatch, tmp_path, action):
    client, f, j, e, _, _ = scoped
    empty = tmp_path / "without-rbac"
    empty.mkdir()
    monkeypatch.setattr(api, "_rbac", RegistreRBAC.charger(empty))
    # Le jeton global donne aussi le comportement ouvert historique sans rôles.
    assert perform(client, f["b"], e["b"], j["b"], action, "master").status_code == 200
