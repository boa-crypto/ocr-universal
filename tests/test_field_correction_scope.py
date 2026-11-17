"""Corrections/annulations : rôle ET document visible avant lecture du résultat."""
import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from unocr import api
from unocr.models import DocumentResult, FieldValue
from unocr.rbac import RegistreRBAC

ACTIONS = ["confirm", "correct", "status", "undo"]


def auth(who):
    return {"Authorization": "Bearer FAKE72-" + who} if who is not None else {}


def perform(client, job, action, who="a", name="sample"):
    path = f"/api/jobs/{job}/fields/{name}"
    if action == "undo":
        return client.post(path + "/undo", json={"motif": "test"}, headers=auth(who))
    bodies = {"confirm": {"confirmed_value": "CONFIRMED72"},
              "correct": {"corrected_value": "CORRECTED72"},
              "status": {"status": "ambiguous"}}
    return client.patch(path, json=bodies[action], headers=auth(who))


@pytest.fixture
def scoped(tmp_cfg, monkeypatch):
    folders = {name: api._dossiers.creer(name, "personnalise").id for name in ("a", "b")}
    users = [{"nom": name, "jeton": "FAKE72-" + name, "roles": [role], "dossiers": scopes}
             for name, role, scopes in [("a", "operateur", [folders["a"]]),
                                       ("b", "operateur", [folders["b"]]),
                                       ("reader", "lecteur", ["*"]),
                                       ("admin", "administrateur", ["*"])]]
    monkeypatch.setattr(api, "_rbac", RegistreRBAC.depuis({"utilisateurs": users}))
    monkeypatch.setattr(api, "_AUTH_TOKEN", "FAKE72-master")
    jobs = {}
    for kind, memberships in [("visible", ["a"]), ("hidden", ["b"]),
                              ("shared", ["a", "b"]), ("unclassified", [])]:
        job = api.store.create_job(kind + ".txt", kind.encode())
        result = DocumentResult(fields={"sample": FieldValue(
            name="sample", raw_value="INITIAL72", normalized_value="NORMAL72",
            value_origin="normalized", confidence=0.4)})
        api.store.save_result(job.id, result.model_dump(mode="json"))
        for folder in memberships:
            api._dossiers.ajouter_piece(folders[folder], job.id, kind + ".txt", category="facture")
        jobs[kind] = job.id
    with TestClient(api.app) as client:
        # Un véritable audit de correction, pour que l'annulation soit possible.
        seed = perform(client, jobs["hidden"], "confirm", "b")
        assert seed.status_code == 200, seed.text
        yield client, jobs, tmp_cfg


def fingerprint(job):
    return hashlib.sha256((api.store.job_dir(job) / "result.json").read_bytes()).hexdigest()


def audit_text(cfg):
    return (cfg.log_dir / "audit.log").read_text()


@pytest.mark.parametrize("action", ACTIONS)
@pytest.mark.parametrize("name", ["sample", "absent"])
def test_outside_scope_denied_before_field_lookup_without_mutation(scoped, action, name):
    client, jobs, cfg = scoped
    job = jobs["hidden"]
    before, journal = fingerprint(job), audit_text(cfg)
    assert client.get(f"/api/jobs/{job}/result", headers=auth("a")).status_code == 403
    response = perform(client, job, action, name=name)
    assert response.status_code == 403
    assert response.json()["detail"] == "document hors de votre périmètre"
    assert fingerprint(job) == before
    delta = audit_text(cfg)[len(journal):]
    assert "acces_refuse_document" in delta
    assert "field_validated" not in delta and "field_correction_annulee" not in delta
    for value in ("INITIAL72", "NORMAL72", "CONFIRMED72", "CORRECTED72"):
        assert value not in response.text + delta


@pytest.mark.parametrize("action", ACTIONS)
def test_guard_precedes_loading_result(scoped, monkeypatch, action):
    client, jobs, _ = scoped

    def forbidden_read(*args, **kwargs):
        raise AssertionError("résultat ne doit pas être lu avant la garde")

    monkeypatch.setattr(api.store, "load_result", forbidden_read)
    assert perform(client, jobs["hidden"], action).status_code == 403


@pytest.mark.parametrize("action", ACTIONS)
@pytest.mark.parametrize("membership", ["visible", "shared", "unclassified"])
def test_existing_visibility_policy_allows_legitimate_changes(scoped, action, membership):
    client, jobs, cfg = scoped
    job = jobs[membership]
    if action == "undo":
        assert perform(client, job, "confirm").status_code == 200
    response = perform(client, job, action)
    assert response.status_code == 200, response.text
    field = api.store.load_result(job)["fields"]["sample"]
    assert field["raw_value"] == "INITIAL72" and field["normalized_value"] == "NORMAL72"
    expected = {"confirm": ("validated", "confirmed"), "correct": ("corrected", "corrected"),
                "status": ("ambiguous", "normalized"), "undo": ("detected", "normalized")}
    assert (field["status"], field["value_origin"]) == expected[action]
    if action == "confirm":
        assert field["confirmed_value"] == "CONFIRMED72"
    elif action == "correct":
        assert field["corrected_value"] == "CORRECTED72"
    elif action == "undo":
        assert field["confirmed_value"] is None and field["corrected_value"] is None
    event = "field_correction_annulee" if action == "undo" else "field_validated"
    assert any(json.loads(line).get("event") == event for line in audit_text(cfg).splitlines())


@pytest.mark.parametrize("action", ACTIONS)
@pytest.mark.parametrize("who,code", [("reader", 403), ("unknown", 401)])
def test_role_and_authentication_remain_required(scoped, action, who, code):
    client, jobs, _ = scoped
    job = jobs["visible"]
    before = fingerprint(job)
    assert perform(client, job, action, who).status_code == code
    assert fingerprint(job) == before


@pytest.mark.parametrize("action", ACTIONS)
@pytest.mark.parametrize("who", ["admin", "master"])
def test_existing_admin_and_environment_token_access_preserved(scoped, action, who):
    client, jobs, _ = scoped
    assert perform(client, jobs["hidden"], action, who).status_code == 200


@pytest.mark.parametrize("action", ACTIONS)
def test_rbac_disabled_keeps_legacy_access(scoped, monkeypatch, tmp_path, action):
    client, jobs, _ = scoped
    empty = tmp_path / "without-rbac"
    empty.mkdir()
    monkeypatch.setattr(api, "_rbac", RegistreRBAC.charger(empty))
    monkeypatch.setattr(api, "_AUTH_TOKEN", None)
    # Aucun fichier RBAC/jeton : garde sans effet comme les autres routes.
    response = perform(client, jobs["hidden"], action, who=None)
    assert response.status_code == 200
