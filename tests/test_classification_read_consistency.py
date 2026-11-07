"""Le journal ne réécrit pas le caractère manuel de la décision stockée."""
import json

import pytest
from test_field_correction_scope import auth, fingerprint
from test_field_correction_scope import scoped as scoped

from unocr import api

DECISION = {"category": "invoice", "confidence": 0.75, "classifier_version": "synthetic78",
            "needs_review": True, "manual": False, "label": "LABEL78",
            "evidence": [{"matched_text": "EVIDENCE78"}], "alternatives": [{"category": "unknown"}],
            "reason": "REASON78", "corrected_by": None}
KEYS = ("category", "confidence", "classifier_version", "needs_review", "manual")


def prepare(scoped, decision=DECISION):
    _, jobs, _ = scoped
    job = jobs["visible"]
    result = api.store.load_result(job)
    result["classification"] = decision
    api.store.save_result(job, result)
    return job


def trace(job, **overrides):
    return {"event": "document_classified", "job_id": job, "ts": 78,
            **{k: DECISION[k] for k in KEYS}, **overrides}


def append(cfg, value):
    with (cfg.log_dir / "audit.log").open("a") as output:
        output.write(json.dumps(value, ensure_ascii=False) + "\n")


def read(scoped, job):
    client, _, _ = scoped
    response = client.get(f"/api/jobs/{job}/classification", headers=auth("a"))
    assert response.status_code == 200, response.text
    return response.json()["classification"]


@pytest.mark.parametrize("key,value", [("category", "packing_list"), ("confidence", 0.5),
    ("classifier_version", "another78"), ("needs_review", False), ("manual", True)])
def test_disagreeing_latest_event_cannot_alter_stored_decision(scoped, key, value):
    job = prepare(scoped)
    append(scoped[-1], trace(job, **{key: value}))
    before = fingerprint(job)
    assert read(scoped, job) == DECISION
    assert fingerprint(job) == before


def test_matching_event_only_adds_timestamp(scoped):
    job = prepare(scoped)
    append(scoped[-1], trace(job))
    assert read(scoped, job) == {**DECISION, "ts": 78}


@pytest.mark.parametrize("manual", [True, False])
def test_stored_manual_status_is_authoritative(scoped, manual):
    decision = {**DECISION, "manual": manual}
    job = prepare(scoped, decision)
    append(scoped[-1], trace(job, manual=not manual))
    assert read(scoped, job) == decision


@pytest.mark.parametrize("noise", [
    "document_classified", ["document_classified"], None, 78,
    {"event": "other78", "message": "document_classified"},
    {"event": "document_classified_suffix"},
])
def test_non_event_json_cannot_override_matching_trace(scoped, noise):
    job = prepare(scoped)
    append(scoped[-1], trace(job))
    if isinstance(noise, dict):
        noise = {**trace(job, manual=True, ts=999), **noise}
    append(scoped[-1], noise)
    assert read(scoped, job) == {**DECISION, "ts": 78}


def test_invalid_json_does_not_replace_last_valid_event(scoped):
    job = prepare(scoped)
    append(scoped[-1], trace(job))
    with (scoped[-1].log_dir / "audit.log").open("a") as out:
        out.write('{"event":"document_classified",broken\n')
    assert read(scoped, job) == {**DECISION, "ts": 78}


def test_other_job_event_is_not_selected(scoped):
    job = prepare(scoped)
    append(scoped[-1], trace(job))
    append(scoped[-1], trace(scoped[1]["hidden"], ts=999, manual=True))
    assert read(scoped, job) == {**DECISION, "ts": 78}


def test_latest_conflict_does_not_reuse_older_matching_timestamp(scoped):
    job = prepare(scoped)
    append(scoped[-1], trace(job))
    append(scoped[-1], trace(job, manual=True, ts=999))
    assert read(scoped, job) == DECISION


@pytest.mark.parametrize("present", [True, False])
def test_no_trace_keeps_stored_decision_or_none(scoped, present):
    job = prepare(scoped, DECISION if present else None)
    assert read(scoped, job) == (DECISION if present else None)


def test_legacy_without_stored_classification_keeps_explicit_event_fallback(scoped):
    job = prepare(scoped, None)
    append(scoped[-1], trace(job))
    assert read(scoped, job) == {**{k: DECISION[k] for k in KEYS}, "ts": 78}


@pytest.mark.parametrize("kind,who,status", [("hidden", "a", 403), ("visible", "unknown", 401)])
def test_scope_and_auth_guard_still_precede_result_read(scoped, monkeypatch, kind, who, status):
    client, jobs, _ = scoped
    def forbidden(*args):
        raise AssertionError("lecture résultat avant autorisation")
    monkeypatch.setattr(api.store, "load_result", forbidden)
    response = client.get(f"/api/jobs/{jobs[kind]}/classification", headers=auth(who))
    assert response.status_code == status
