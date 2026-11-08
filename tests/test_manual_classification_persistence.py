"""Une catégorie manuelle reçue doit être persistée, pas seulement journalisée."""
import json

import pytest
from test_field_correction_scope import auth, fingerprint
from test_field_correction_scope import scoped as scoped

from unocr import api
from unocr.models import DocumentResult
from unocr.storage import JobStore


def patch(client, job, category="invoice", who="a"):
    return client.patch(f"/api/jobs/{job}/classification", headers=auth(who),
                        json={"category": category, "user": "DECLARED77"})


def events(cfg):
    path = cfg.log_dir / "audit.log"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


@pytest.mark.parametrize("membership", ["visible", "shared", "unclassified"])
@pytest.mark.parametrize("category", ["invoice", "bill_of_lading", "packing_list"])
@pytest.mark.parametrize("previous", [False, True])
def test_manual_category_survives_fresh_store_and_get(scoped, membership, category, previous):
    client, jobs, cfg = scoped
    job = jobs[membership]
    original = api.store.load_result(job)
    if previous:
        original["classification"] = {"category": "unknown", "manual": False,
                                      "evidence": [{"matched_text": "AUTO77"}]}
        api.store.save_result(job, original)
    response = patch(client, job, category)
    assert response.status_code == 200, response.text
    decision = response.json()["classification"]
    assert decision["category"] == category and decision["manual"] is True
    assert decision["corrected_by"] == "a"  # principal serveur, pas identité civile (lot86)
    assert decision["evidence"] == []  # ne pas attribuer les anciennes preuves à une autre catégorie
    expected = {**original, "classification": decision}
    assert JobStore(cfg).load_result(job) == expected
    assert DocumentResult.model_validate(JobStore(cfg).load_result(job)).classification == decision
    read = client.get(f"/api/jobs/{job}/classification", headers=auth("a"))
    assert read.status_code == 200
    actual = read.json()["classification"]
    assert {k: v for k, v in actual.items() if k != "ts"} == decision
    assert len([e for e in events(cfg) if e["event"] == "document_classified" and e["job_id"] == job]) == 1


@pytest.mark.parametrize("who", ["admin", "master"])
def test_privileged_can_persist_on_other_dossier(scoped, who):
    client, jobs, cfg = scoped
    assert patch(client, jobs["hidden"], who=who).status_code == 200
    assert JobStore(cfg).load_result(jobs["hidden"])["classification"]["category"] == "invoice"


@pytest.mark.parametrize("who,kind,status", [("reader", "visible", 403), ("a", "hidden", 403),
                                           ("unknown", "visible", 401), (None, "visible", 401)])
def test_refused_scope_or_role_precedes_read_and_write(scoped, monkeypatch, who, kind, status):
    client, jobs, cfg = scoped
    job = jobs[kind]
    before = fingerprint(job)
    def forbidden(*args, **kwargs):
        raise AssertionError("lecture/écriture avant autorisation")
    monkeypatch.setattr(api.store, "load_result", forbidden)
    monkeypatch.setattr(api.store, "save_result", forbidden)
    assert patch(client, job, who=who).status_code == status
    assert fingerprint(job) == before
    assert not [e for e in events(cfg) if e["event"] == "document_classified"]


@pytest.mark.parametrize("category", ["", "  ", "not-a-category77"])
def test_invalid_category_does_not_persist_or_audit_success(scoped, category):
    client, jobs, cfg = scoped
    job = jobs["visible"]
    before = fingerprint(job)
    assert patch(client, job, category).status_code == 422
    assert fingerprint(job) == before
    assert not [e for e in events(cfg) if e["event"] == "document_classified"]


def test_missing_job_has_no_success(scoped):
    client, _, cfg = scoped
    assert patch(client, "missing77").status_code == 404
    assert not [e for e in events(cfg) if e["event"] == "document_classified"]


def test_job_without_result_has_no_success(scoped):
    client, _, cfg = scoped
    record = api.store.create_job("synthetic77.txt", b"synthetic77")
    assert patch(client, record.id).status_code == 409
    assert api.store.load_result(record.id) is None
    assert not [e for e in events(cfg) if e["event"] == "document_classified"]


def test_save_failure_does_not_report_success_or_audit(scoped, monkeypatch):
    client, jobs, cfg = scoped
    job = jobs["visible"]
    before = fingerprint(job)
    def fail(*args):
        raise OSError("SYNTHETIC77 write failure")
    monkeypatch.setattr(api.store, "save_result", fail)
    with pytest.raises(OSError, match="SYNTHETIC77"):
        patch(client, job)
    assert fingerprint(job) == before
    assert not [e for e in events(cfg) if e["event"] == "document_classified"]


def test_successive_manual_categories_replace_current_decision(scoped):
    client, jobs, cfg = scoped
    job = jobs["visible"]
    for category in ("invoice", "packing_list", "bill_of_lading"):
        assert patch(client, job, category).status_code == 200
        assert JobStore(cfg).load_result(job)["classification"]["category"] == category
    assert [e["category"] for e in events(cfg) if e["event"] == "document_classified"] == ["invoice", "packing_list", "bill_of_lading"]
