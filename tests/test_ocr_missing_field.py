"""Pas de correction fictive : service et API sur JSON/cache temporaires réels."""
import json

import pytest
from test_ocr_dossier_scope import scoped as scoped
from test_ocr_dossier_scope import snapshot

from unocr import ocr_integration
from unocr.models import ChampExtrait
from unocr.ocr_integration import ExtractionOCRStore, OCRTransitIntegration


@pytest.fixture
def service(tmp_cfg, monkeypatch):
    monkeypatch.setattr(ocr_integration, "cfg", tmp_cfg)
    return OCRTransitIntegration(tmp_cfg.data_dir), tmp_cfg


def events(cfg):
    path = cfg.log_dir / "audit.log"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def assert_correction(result, before, name, value):
    expected = before.model_copy(deep=True)
    target = next(champ for champ in expected.champs_extraits if champ.nom == name)
    target.valeur_correctee = target.valeur_confirmee = value
    target.origine = target.statut = "corrected"
    expected.modifie_le = result.modifie_le
    assert result.modifie_le and result.modifie_le != "BEFORE74"
    assert result.model_dump() == expected.model_dump()


@pytest.mark.parametrize("cold", [False, True], ids=["cache", "disk"])
@pytest.mark.parametrize("names, requested", [
    ([], "missing"), (["reference"], "missing"), (["reference", "second"], "absent"),
    (["reference"], "Reference"), (["reference"], "reference "),
    (["référence"], "re\u0301fe\u0301rence"), (["المرجع"], "مرجع"),
])
def test_missing_field_refuses_before_any_write_or_success_audit(service, monkeypatch, cold, names, requested):
    integration, cfg = service
    record = integration.extraction_store.creer(
        dossier_id="synthetic74", modifie_le="BEFORE74",
        champs_extraits=[ChampExtrait(nom=name, valeur_raw="RAW74", confiance=0.2) for name in names])
    before_model, before_files, before_events = record.model_dump(), snapshot(cfg), events(cfg)
    if cold:
        integration.extraction_store._cache.clear()
    def forbidden(*args, **kwargs):
        raise AssertionError("écriture ou audit après champ absent")
    monkeypatch.setattr(integration.extraction_store, "_ecrire", forbidden)
    monkeypatch.setattr(ocr_integration, "audit", forbidden)
    assert integration.correct_field(record.id, requested, "VALUE74", "FAKE74-test") is False
    assert integration.extraction_store.get(record.id).model_dump() == before_model
    assert snapshot(cfg) == before_files and events(cfg) == before_events


@pytest.mark.parametrize("cold", [False, True])
def test_missing_extraction_still_returns_false_without_writing(service, monkeypatch, cold):
    integration, cfg = service
    if cold:
        integration.extraction_store._cache.clear()
    before_files, before_events = snapshot(cfg), events(cfg)
    def forbidden(*args, **kwargs):
        raise AssertionError("écriture ou audit après extraction absente")
    monkeypatch.setattr(integration.extraction_store, "_ecrire", forbidden)
    monkeypatch.setattr(ocr_integration, "audit", forbidden)
    assert integration.correct_field("missing74", "reference", "VALUE74", "FAKE74-test") is False
    assert snapshot(cfg) == before_files and events(cfg) == before_events


@pytest.mark.parametrize("cold", [False, True], ids=["cache", "disk"])
@pytest.mark.parametrize("name,value", [
    ("reference", "CORRECT74"), ("référence", "corrigé"), ("المرجع", "تصحيح"),
    ("reference", ""), ("reference", "0"), ("reference", "two\nlines"),
])
def test_existing_field_correction_keeps_values_and_persists_success(service, cold, name, value):
    integration, cfg = service
    record = integration.extraction_store.creer(
        dossier_id="synthetic74", modifie_le="BEFORE74", confiance_globale=0.37,
        champs_extraits=[ChampExtrait(nom="unrelated74", valeur_raw="UNCHANGED74"),
                         ChampExtrait(nom=name, valeur_raw="RAW74", confiance=0.2, anomalies=["NOTE74"])])
    before = record.model_copy(deep=True)
    if cold:
        integration.extraction_store._cache.clear()
    assert integration.correct_field(record.id, name, value, "FAKE74-test") is True
    assert_correction(integration.extraction_store.get(record.id), before, name, value)
    reloaded = ExtractionOCRStore(integration.extraction_store.root).get(record.id)
    assert_correction(reloaded, before, name, value)
    success = [event for event in events(cfg) if event["event"] == "ocr_champ_corrige"]
    assert len(success) == 1
    assert {k: v for k, v in success[0].items() if k != "ts"} == {
        "event": "ocr_champ_corrige", "extraction_id": record.id, "champ": name, "user": "FAKE74-test"}


@pytest.mark.parametrize("cold", [False, True], ids=["cache", "disk"])
@pytest.mark.parametrize("status", ["extracted", "validated", "corrected"])
def test_api_missing_field_returns_404_without_mutation_or_success(scoped, cold, status):
    client, folders, _, extractions, integration, cfg = scoped
    record = integration.extraction_store.get(extractions["a"])
    record.statut, record.modifie_le = status, "BEFORE74"
    integration.extraction_store._ecrire(record)
    before_model, before_files, before_events = record.model_dump(), snapshot(cfg), events(cfg)
    if cold:
        integration.extraction_store._cache.clear()
    response = client.post(f'/api/dossiers/{folders["a"]}/documents-ocr/{record.id}/corriger',
        headers={"Authorization": "Bearer FAKE73-a"}, json={"champ_nom": "missing74", "nouvelle_valeur": "VALUE74"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Document OCR ou champ introuvable"}
    assert "PRIVATE73" not in response.text
    assert integration.extraction_store.get(record.id).model_dump() == before_model
    assert snapshot(cfg) == before_files and events(cfg) == before_events
    assert ExtractionOCRStore(integration.extraction_store.root).get(record.id).model_dump() == before_model


@pytest.mark.parametrize("value", ["", "0", "corrigé", "تصحيح"])
def test_api_existing_field_still_returns_actual_correction(scoped, value):
    client, folders, _, extractions, integration, cfg = scoped
    record = integration.extraction_store.get(extractions["a"])
    record.modifie_le = "BEFORE74"
    integration.extraction_store._ecrire(record)
    before = record.model_copy(deep=True)
    response = client.post(f'/api/dossiers/{folders["a"]}/documents-ocr/{record.id}/corriger',
        headers={"Authorization": "Bearer FAKE73-a"}, json={"champ_nom": "sample", "nouvelle_valeur": value})
    assert response.status_code == 200
    result = ExtractionOCRStore(integration.extraction_store.root).get(record.id)
    assert response.json() == result.model_dump(mode="json")
    assert_correction(result, before, "sample", value)
    assert len([event for event in events(cfg) if event["event"] == "ocr_champ_corrige"]) == 1
