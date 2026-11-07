"""Reclassement persistant, sans écrasement automatique de décision manuelle."""
import json

import pytest
from test_field_correction_scope import auth, fingerprint
from test_field_correction_scope import scoped as scoped

from unocr import api
from unocr.classification import ClassificationResult
from unocr.storage import JobStore


@pytest.fixture
def classifier(monkeypatch):
    calls = []
    def classify(text):
        calls.append(text)
        return ClassificationResult(category="invoice", label="SYNTHETIC79", confidence=0.72,
            evidence=[{"matched_text": "EVIDENCE79"}], alternatives=[{"category": "unknown"}],
            classifier_version="synthetic79", needs_review=True, reason="TEST79")
    monkeypatch.setattr(api._classifier, "classify", classify)
    return calls


def events(cfg):
    path = cfg.log_dir / "audit.log"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def post(scoped, kind="visible", who="a"):
    return scoped[0].post(f"/api/jobs/{scoped[1].get(kind,kind)}/classify", headers=auth(who))


def set_classification(job, decision):
    original = api.store.load_result(job)
    original["classification"] = decision
    api.store.save_result(job, original)
    return original


@pytest.mark.parametrize("kind", ["visible", "shared", "unclassified"])
@pytest.mark.parametrize("previous", [None, {}, {"category": "unknown", "manual": False}])
def test_auto_decision_is_saved_and_read_consistently(scoped, classifier, kind, previous):
    client, jobs, cfg = scoped
    job = jobs[kind]
    original = set_classification(job, previous)
    response = post(scoped, kind)
    assert response.status_code == 200, response.text
    decision = response.json()["classification"]
    assert decision["manual"] is False and decision["evidence"] == [{"matched_text": "EVIDENCE79"}]
    assert decision["needs_review"] is True and decision["reason"] == "TEST79"
    assert len(classifier) == 1
    assert JobStore(cfg).load_result(job) == {**original, "classification": decision}
    read = client.get(f"/api/jobs/{job}/classification", headers=auth("a"))
    assert read.status_code == 200
    assert {k:v for k,v in read.json()["classification"].items() if k != "ts"} == decision
    assert len([e for e in events(cfg) if e["event"] == "document_classified"]) == 1


@pytest.mark.parametrize("manual", [True, None, "true", 1, 0, [], {}])
def test_manual_or_ambiguous_marker_refused_before_classifier(scoped, classifier, manual):
    _, jobs, cfg = scoped
    job = jobs["visible"]
    set_classification(job, {"category": "packing_list", "manual": manual, "evidence": ["KEEP79"]})
    before = fingerprint(job)
    assert post(scoped).status_code == 409
    assert fingerprint(job) == before and classifier == []
    assert not [e for e in events(cfg) if e["event"] == "document_classified"]


@pytest.mark.parametrize("decision", [[], "invalid79", 0])
def test_non_object_classification_refused_without_replacement(scoped, classifier, decision):
    job = scoped[1]["visible"]
    set_classification(job, decision)
    before = fingerprint(job)
    assert post(scoped).status_code == 409
    assert fingerprint(job) == before and classifier == []


@pytest.mark.parametrize("who,kind,status", [("reader","visible",403), ("a","hidden",403),
                                           ("unknown","visible",401), (None,"visible",401)])
def test_guard_precedes_result_read_and_classifier(scoped, classifier, monkeypatch, who, kind, status):
    def forbidden(*args):
        raise AssertionError("lecture résultat avant autorisation")
    monkeypatch.setattr(api.store, "load_result", forbidden)
    assert post(scoped, kind, who).status_code == status and classifier == []


@pytest.mark.parametrize("who", ["admin", "master"])
def test_privileged_users_can_persist_visible_by_policy(scoped, classifier, who):
    _, jobs, cfg = scoped
    assert post(scoped, "hidden", who).status_code == 200
    assert JobStore(cfg).load_result(jobs["hidden"])["classification"]["manual"] is False


@pytest.mark.parametrize("missing", ["job", "result"])
def test_missing_job_or_result_never_classified(scoped, classifier, missing):
    client, _, cfg = scoped
    job = "missing79" if missing == "job" else api.store.create_job("empty79.txt", b"synthetic").id
    response = client.post(f"/api/jobs/{job}/classify", headers=auth("a"))
    assert response.status_code == 404 and classifier == []
    assert not [e for e in events(cfg) if e["event"] == "document_classified"]


def test_storage_failure_prevents_success_audit(scoped, classifier, monkeypatch):
    job = scoped[1]["visible"]
    before = fingerprint(job)
    def fail(*args):
        raise OSError("SYNTHETIC79 save failure")
    monkeypatch.setattr(api.store, "save_result", fail)
    with pytest.raises(OSError, match="SYNTHETIC79"):
        post(scoped)
    assert fingerprint(job) == before and len(classifier) == 1
    assert not [e for e in events(scoped[-1]) if e["event"] == "document_classified"]


def test_manual_action_then_auto_cannot_downgrade_decision(scoped, classifier):
    client, jobs, cfg = scoped
    job = jobs["visible"]
    response = client.patch(f"/api/jobs/{job}/classification", headers=auth("a"), json={"category": "packing_list"})
    assert response.status_code == 200
    before = fingerprint(job)
    assert post(scoped).status_code == 409 and classifier == []
    assert fingerprint(job) == before
    assert JobStore(cfg).load_result(job)["classification"] == response.json()["classification"]
