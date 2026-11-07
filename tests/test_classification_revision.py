"""Révision de contenu : refus déterministe d'une classification devenue périmée."""
import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from test_field_correction_scope import auth
from test_field_correction_scope import scoped as scoped

from unocr import api
from unocr.classification import ClassificationResult
from unocr.storage import JobStore


def events(cfg):
    path = cfg.log_dir / "audit.log"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


@pytest.mark.parametrize("other_store", [False, True])
def test_snapshot_revision_matches_exact_saved_bytes(scoped, other_store):
    _, jobs, cfg = scoped
    store = JobStore(cfg) if other_store else api.store
    job = jobs["visible"]
    data, revision = store.load_result_revision(job)
    assert data == store.load_result(job)
    assert revision == hashlib.sha256((store.job_dir(job)/"result.json").read_bytes()).hexdigest()
    data["classification"] = {"category": "invoice", "manual": False}
    assert store.replace_result_revision(job, revision, data) is True
    assert store.load_result(job) == data
    assert store.replace_result_revision(job, revision, {"WRONG80": True}) is False
    assert store.load_result(job) == data


@pytest.mark.parametrize("change", ["manual", "field", "format", "delete"])
def test_revision_conflict_does_not_replace_newer_content(scoped, change):
    _, jobs, cfg = scoped
    job = jobs["visible"]
    original, revision = api.store.load_result_revision(job)
    newer = api.store.load_result(job)
    path = api.store.job_dir(job)/"result.json"
    if change == "manual":
        newer["classification"] = {"category": "packing_list", "manual": True}
        JobStore(cfg).save_result(job, newer)
    elif change == "field":
        newer["fields"]["sample"]["confirmed_value"] = "NEW80"
        JobStore(cfg).save_result(job, newer)
    elif change == "format":
        path.write_text(json.dumps(newer, indent=7))
    else:
        path.unlink()
    before = path.read_bytes() if path.exists() else None
    assert api.store.replace_result_revision(job, revision, original) is False
    assert (path.read_bytes() if path.exists() else None) == before


def test_missing_result_snapshot_cannot_create_by_compare_replace(scoped):
    _, jobs, _ = scoped
    assert api.store.load_result_revision("missing80") == (None, None)
    assert api.store.replace_result_revision("missing80", "fake80", {}) is False
    assert api.store.load_result("missing80") is None


def test_two_stores_same_snapshot_only_one_winner(scoped):
    _, jobs, cfg = scoped
    job = jobs["visible"]
    original, revision = api.store.load_result_revision(job)
    barrier = threading.Barrier(2)
    def compete(category):
        store = JobStore(cfg)
        candidate = {**original, "classification": {"category": category}}
        barrier.wait(timeout=10)
        return category, store.replace_result_revision(job, revision, candidate)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(compete, ["invoice", "packing_list"]))
    assert sum(won for _, won in results) == 1
    winner = next(category for category, won in results if won)
    assert JobStore(cfg).load_result(job)["classification"]["category"] == winner


@pytest.mark.parametrize("action", ["auto", "manual"])
@pytest.mark.parametrize("change", ["manual", "field"])
def test_route_conflict_after_computation_refuses_without_success(scoped, monkeypatch, action, change):
    client, jobs, cfg = scoped
    job = jobs["visible"]
    original = api.store.load_result(job)
    newer = api.store.load_result(job)
    if change == "manual":
        newer["classification"] = {"category": "packing_list", "manual": True}
    else:
        newer["fields"]["sample"]["confirmed_value"] = "NEW80"
    def concurrent(*args, **kwargs):
        JobStore(cfg).save_result(job, newer)
        return ClassificationResult(category="invoice", label="TEST80", confidence=0.7)
    if action == "auto":
        monkeypatch.setattr(api._classifier, "classify", concurrent)
        response = client.post(f"/api/jobs/{job}/classify", headers=auth("a"))
    else:
        monkeypatch.setattr(api, "classification_manuelle", concurrent)
        response = client.patch(f"/api/jobs/{job}/classification", headers=auth("a"), json={"category":"invoice"})
    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "résultat modifié pendant la classification : relisez avant de réessayer"
    assert JobStore(cfg).load_result(job) == newer and newer != original
    assert not [e for e in events(cfg) if e["event"] == "document_classified"]


def test_auto_paused_while_manual_request_commits_keeps_manual(scoped, monkeypatch):
    client, jobs, cfg = scoped
    job = jobs["visible"]
    entered, release = threading.Event(), threading.Event()
    def paused(text):
        entered.set()
        assert release.wait(10), "requête manuelle non terminée"
        return ClassificationResult(category="invoice", label="TEST80", confidence=0.7)
    monkeypatch.setattr(api._classifier, "classify", paused)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(client.post, f"/api/jobs/{job}/classify", headers=auth("a"))
        try:
            assert entered.wait(10), "classification automatique non démarrée"
            manual = client.patch(f"/api/jobs/{job}/classification", headers=auth("a"), json={"category":"packing_list"})
            assert manual.status_code == 200, manual.text
        finally:
            release.set()
        automatic = future.result(timeout=15)
    assert automatic.status_code == 409
    assert JobStore(cfg).load_result(job)["classification"] == manual.json()["classification"]
    successes = [e for e in events(cfg) if e["event"] == "document_classified"]
    assert len(successes) == 1 and successes[0]["manual"] is True


@pytest.mark.parametrize("action", ["auto", "manual"])
@pytest.mark.parametrize("who,kind,status", [("reader","visible",403), ("a","hidden",403),
                                           ("unknown","visible",401), (None,"visible",401)])
def test_authorization_precedes_revision_read_and_compare(scoped, monkeypatch, action, who, kind, status):
    client, jobs, _ = scoped
    def forbidden(*args, **kwargs):
        raise AssertionError("révision lue/écrite avant autorisation")
    monkeypatch.setattr(api.store, "load_result_revision", forbidden)
    monkeypatch.setattr(api.store, "replace_result_revision", forbidden)
    job = jobs[kind]
    if action == "auto":
        response = client.post(f"/api/jobs/{job}/classify", headers=auth(who))
    else:
        response = client.patch(f"/api/jobs/{job}/classification", headers=auth(who), json={"category":"invoice"})
    assert response.status_code == status
