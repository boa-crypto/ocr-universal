"""Tests d'intégration API du Connecteur Hub.

Vérifient le parcours complet exposé par HTTP, et surtout que les verrous de
sécurité sont côté serveur : pas de transmission sans validation, pas de
fonctionnel sans test réel, aucun secret exposé.
"""
import json
import pathlib

import pytest
from fastapi.testclient import TestClient

from unocr import api
from unocr.api import app
from unocr.connectors.simulated import SIMULATED


@pytest.fixture()
def client(tmp_cfg, fixtures_dir, tmp_path):
    SIMULATED.healthy = True
    # hub isolé dans le répertoire tempornaire
    from unocr.connectors.forms import FormStore
    from unocr.connectors.hub import ConnectorHub
    from unocr.connectors.transmission import TransmissionEngine

    api._watch.stop()
    api._watch.reset()
    api.connector_hub = ConnectorHub(tmp_path / "connectors", tmp_path / "logs")
    api.transmissions = TransmissionEngine(tmp_path / "connectors",
                                           tmp_path / "logs")
    api.form_store = FormStore(tmp_path / "connectors" / "forms")
    yield TestClient(app)
    api._watch.stop()
    api._watch.reset()
    SIMULATED.healthy = True


# ─────────────────────────── catalogue & cycle de vie ───────────────────────────

def test_catalog_lists_adapters(client):
    rows = client.get("/api/connectors/catalog").json()
    ids = {r["connector_id"] for r in rows}
    assert ids == {"demo_simulated", "assisted_export", "customs_api"}
    assert {r["connector_id"] for r in rows if r["is_real_external_system"]} == {"customs_api"}


def test_overview_endpoint(client):
    body = client.get("/api/connectors").json()
    assert "summary" in body and "catalog" in body and "configured" in body
    assert body["summary"]["real_external_adapters"] == 1
    assert body["configured"] == []


def test_create_then_state_is_to_test(client):
    r = client.post("/api/connectors/demo_simulated",
                    json={"settings": {"env": "test"}, "note": "essai"})
    assert r.status_code == 200
    assert r.json()["state"] == "to_test"


def test_unknown_connector_is_404(client):
    assert client.post("/api/connectors/inconnu", json={}).status_code == 404
    assert client.get("/api/connectors/inconnu").status_code == 404
    assert client.delete("/api/connectors/inconnu").status_code == 404


def test_test_endpoint_changes_state(client):
    client.post("/api/connectors/demo_simulated", json={"settings": {}})
    r = client.post("/api/connectors/demo_simulated/test")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["state"] == "functional"
    assert r.json()["latency_ms"] >= 0


def test_failed_test_reports_error_state(client, monkeypatch):
    client.post("/api/connectors/demo_simulated", json={"settings": {}})
    SIMULATED.healthy = False
    r = client.post("/api/connectors/demo_simulated/test")
    assert r.json()["ok"] is False
    assert r.json()["state"] == "error"


def test_disable_keeps_configuration(client):
    client.post("/api/connectors/demo_simulated", json={"settings": {"env": "test"}})
    client.post("/api/connectors/demo_simulated/test")
    r = client.post("/api/connectors/demo_simulated/disable")
    assert r.json()["state"] == "disabled"
    rows = {c["connector_id"]: c for c in client.get("/api/connectors/configured").json()}
    assert rows["demo_simulated"]["state"] == "disabled"
    assert rows["demo_simulated"]["test_count"] == 1


def test_enable_returns_to_to_test(client):
    client.post("/api/connectors/demo_simulated", json={"settings": {}})
    client.post("/api/connectors/demo_simulated/test")
    client.post("/api/connectors/demo_simulated/disable")
    r = client.post("/api/connectors/demo_simulated/enable")
    assert r.json()["state"] == "to_test"


def test_delete_removes_connector(client):
    client.post("/api/connectors/demo_simulated", json={"settings": {}})
    assert client.delete("/api/connectors/demo_simulated").status_code == 200
    assert client.get("/api/connectors/demo_simulated").status_code == 404


# ─────────────────────────── formulaires ───────────────────────────

def test_forms_are_discovered_with_source(client):
    client.post("/api/connectors/demo_simulated", json={"settings": {}})
    body = client.get("/api/connectors/demo_simulated/forms").json()
    assert body["forms"], "le connecteur de démonstration déclare un formulaire"
    form = body["forms"][0]
    assert form["source"] == "declared"
    assert form["fields"] and form["fields"][0]["external_name"]


# ─────────────────────────── secrets ───────────────────────────

def test_secret_roundtrip_never_exposes_value(client):
    client.post("/api/connectors/demo_simulated", json={"settings": {}})
    r = client.put("/api/connectors/demo_simulated/secrets",
                   json={"key": "api_key", "value": "valeur-ultra-secrète"})
    assert r.status_code == 200 and r.json()["stored"] is True

    keys = client.get("/api/connectors/demo_simulated/secrets").json()
    assert keys["keys"] == ["api_key"]
    # la valeur ne fuite dans AUCUNE réponse
    for path in ("/api/connectors", "/api/connectors/configured",
                 "/api/connectors/demo_simulated",
                 "/api/connectors/secrets/status"):
        assert "valeur-ultra-secrète" not in client.get(path).text

    assert client.delete(
        "/api/connectors/demo_simulated/secrets/api_key").status_code == 200
    assert client.get("/api/connectors/demo_simulated/secrets").json()["keys"] == []


def test_secrets_status_reports_encryption(client):
    body = client.get("/api/connectors/secrets/status").json()
    assert body["encrypted"] is True
    assert body["algorithm"] == "AES-256-GCM"


def test_empty_secret_is_refused(client):
    client.post("/api/connectors/demo_simulated", json={"settings": {}})
    r = client.put("/api/connectors/demo_simulated/secrets",
                   json={"key": "", "value": "x"})
    assert r.status_code == 400


# ─────────────────────────── mapping / prévisualisation ───────────────────────────

def _doc(client, values):
    """Enregistre un document traité déterministe (champs de démonstration).

    Le document réel n'est pas utile ici : on teste la chaîne hub, pas l'OCR.
    """
    from unocr.models import DocumentResult, FieldValue

    fields = {k: FieldValue(name=k, normalized_value=v, value_origin="normalized",
                            source="rule", confidence=0.9, page_num=1)
              for k, v in values.items()}
    job_id = "job_hub_test"
    api.store.job_dir(job_id).mkdir(parents=True, exist_ok=True)
    api.store.save_result(job_id, DocumentResult(
        document_id=job_id, source_path="hub_test.png", fields=fields,
        text="document de démonstration").model_dump())
    return job_id


def _setup(client, test=False):
    """Configure (et teste si demandé) le connecteur de démonstration."""
    client.post("/api/connectors/demo_simulated", json={"settings": {}})
    if test:
        assert client.post("/api/connectors/demo_simulated/test").json()["ok"]


def _upload(client, fixtures_dir):
    r = client.post("/api/documents", files={"file": (
        "carte_grise.png", (fixtures_dir / "photo_carte_grise.png").read_bytes(),
        "image/png")})
    assert r.status_code == 200
    return r.json()["job_id"]


def _wait(client, job_id):
    for _ in range(120):
        st = client.get(f"/api/jobs/{job_id}").json()
        if st.get("status") in ("done", "error"):
            return st
    raise AssertionError("traitement trop long")


def test_preview_returns_mapping_and_validation(client, fixtures_dir):
    _setup(client)
    job_id = _upload(client, fixtures_dir)
    _wait(client, job_id)
    body = client.post("/api/connectors/preview", json={
        "job_id": job_id, "form_id": "demo_declaration",
        "rules": [{"source_field": "container_number",
                   "target_field": "containerNo", "transform": "clean"}],
        "risk": "high"}).json()
    assert body["form"]["form_id"] == "demo_declaration"
    assert "containerNo" in body["values"]
    v = body["validation"]
    assert "can_transmit" in v and v["risk"] == "high"
    assert v["can_transmit"] is False
    # soit il manque des champs, soit la confirmation humaine est exigée
    assert "erreur" in v["reason"] or "confirmation" in v["reason"]


def test_preview_suggests_without_filling(client, fixtures_dir):
    _setup(client)
    """Une similarité est proposée, jamais appliquée."""
    job_id = _upload(client, fixtures_dir)
    _wait(client, job_id)
    body = client.post("/api/connectors/preview", json={
        "job_id": job_id, "form_id": "demo_declaration", "rules": []}).json()
    for s in body["suggestions"]:
        assert s["confidence"] == "suggested"
    assert body["values"]["containerNo"]["value"] is None


def test_preview_unknown_job_is_404(client):
    r = client.post("/api/connectors/preview",
                    json={"job_id": "job_absent", "form_id": "demo_declaration"})
    assert r.status_code == 404


# ─────────────────────────── transmission ───────────────────────────

def test_transmit_refused_without_confirmation(client, fixtures_dir):
    _setup(client)
    job_id = _upload(client, fixtures_dir)
    _wait(client, job_id)
    r = client.post("/api/connectors/transmit", json={
        "job_id": job_id, "form_id": "demo_declaration",
        "rules": [{"source_field": "container_number",
                   "target_field": "containerNo"},
                  {"source_field": "vin", "target_field": "bl_reference"},
                  {"source_field": "amount", "target_field": "grossWeight",
                   "transform": "decimal"}],
        "risk": "high", "confirmed": False})
    assert r.status_code == 409, r.text


def test_transmit_full_flow_with_confirmation(client, fixtures_dir):
    _setup(client, test=True)
    job_id = _doc(client, {"container_number": "TGHU1234567",
                           "vin": "BL-2026-0042", "amount": "10.00"})

    # configurer + tester le connecteur simulé
    client.post("/api/connectors/demo_simulated", json={"settings": {}})
    assert client.post("/api/connectors/demo_simulated/test").json()["ok"]

    r = client.post("/api/connectors/transmit", json={
        "job_id": job_id, "form_id": "demo_declaration",
        "rules": [{"source_field": "container_number",
                   "target_field": "containerNo"},
                  {"source_field": "vin", "target_field": "bl_reference"},
                  {"source_field": "amount", "target_field": "grossWeight",
                   "transform": "decimal"}],
        "risk": "medium", "confirmed": True, "confirmed_by": "test.api"})
    assert r.status_code == 200, r.text
    tx = r.json()["transmission"]
    assert tx["status"] in ("accepted", "rejected")
    assert r.json()["is_real_external_system"] is False
    # l'identifiant interne est unique et traçable
    assert tx["transmission_id"].startswith("tx_")


def test_transmit_blocked_when_no_operational_connector(client, fixtures_dir):
    """Aucun connecteur testé → refus explicite, pas d'envoi à l'aveugle."""
    _setup(client)          # configuré mais jamais testé
    job_id = _doc(client, {"container_number": "TGHU1234567"})
    r = client.post("/api/connectors/transmit", json={
        "job_id": job_id, "form_id": "demo_declaration",
        "rules": [{"source_field": "container_number",
                   "target_field": "containerNo"}],
        "risk": "low", "confirmed": True})
    assert r.status_code == 409
    assert "opérationnel" in r.json()["detail"]


def test_transmissions_history_and_stats(client, fixtures_dir):
    _setup(client, test=True)
    job_id = _doc(client, {"container_number": "TGHU1234567",
                           "vin": "BL-2026-0043", "amount": "12.00"})
    client.post("/api/connectors/demo_simulated", json={"settings": {}})
    client.post("/api/connectors/demo_simulated/test")
    client.post("/api/connectors/transmit", json={
        "job_id": job_id, "form_id": "demo_declaration",
        "rules": [{"source_field": "container_number",
                   "target_field": "containerNo"},
                  {"source_field": "vin", "target_field": "bl_reference"},
                  {"source_field": "amount", "target_field": "grossWeight",
                   "transform": "decimal"}],
        "risk": "low", "confirmed": True})

    body = client.get("/api/connectors/transmissions").json()
    assert body["stats"]["total"] >= 1
    assert body["transmissions"][0]["connector_id"] == "demo_simulated"


def test_reconcile_and_retry_endpoints(client, fixtures_dir):
    _setup(client, test=True)
    job_id = _doc(client, {"container_number": "TGHU1234567",
                           "vin": "BL-2026-0044", "amount": "14.00"})
    client.post("/api/connectors/demo_simulated", json={"settings": {}})
    client.post("/api/connectors/demo_simulated/test")
    r = client.post("/api/connectors/transmit", json={
        "job_id": job_id, "form_id": "demo_declaration",
        "rules": [{"source_field": "container_number",
                   "target_field": "containerNo"},
                  {"source_field": "vin", "target_field": "bl_reference"},
                  {"source_field": "amount", "target_field": "grossWeight",
                   "transform": "decimal"}],
        "risk": "low", "confirmed": True})
    tid = r.json()["transmission"]["transmission_id"]

    # rapprochement : sans changement de statut, ne casse rien
    rec = client.post(f"/api/connectors/transmissions/{tid}/reconcile")
    assert rec.status_code == 200

    # annulation
    can = client.post(f"/api/connectors/transmissions/{tid}/cancel")
    assert can.status_code == 200
    assert can.json()["status"] == "cancelled"


def test_unknown_transmission_is_404(client):
    assert client.post(
        "/api/connectors/transmissions/tx_absent/reconcile").status_code == 404
    assert client.post(
        "/api/connectors/transmissions/tx_absent/retry").status_code == 404


# ─────────────────── modèles de formulaires (phase 5) ───────────────────

def test_form_templates_are_proposals_not_official(client):
    rows = client.get("/api/connectors/forms/templates").json()
    assert {r["form_id"] for r in rows} == {"customs_declaration", "port_call"}
    assert all(r["fields"] > 0 for r in rows)


def test_form_create_update_disable_cycle(client):
    r = client.post("/api/connectors/forms", json={
        "form_id": "essai", "name": "Essai", "fields": [
            {"key": "a", "label": "A", "type": "text", "required": True},
            {"key": "b", "label": "B", "type": "date"}]})
    assert r.status_code == 200 and r.json()["fields"] == 2

    det = client.get("/api/connectors/forms/essai").json()
    assert det["schema"]["source"] == "declared"
    assert det["form"]["version"] == 1

    up = client.post("/api/connectors/forms/essai", json={"name": "Essai v2"})
    assert up.json()["version"] == 2

    dis = client.post("/api/connectors/forms/essai/disable")
    assert dis.json()["active"] is False
    # le modèle existe toujours (pas de suppression)
    assert client.get("/api/connectors/forms/essai").status_code == 200
    assert client.get("/api/connectors/forms").json()["forms"] == []


def test_form_from_template(client):
    r = client.post("/api/connectors/forms/port_call/from-template")
    assert r.status_code == 200
    assert r.json()["fields"] > 0
    # 2e copie refusée : pas d'écrasement silencieux
    assert client.post(
        "/api/connectors/forms/port_call/from-template").status_code == 409


def test_form_requires_at_least_one_field(client):
    r = client.post("/api/connectors/forms", json={"form_id": "vide", "fields": []})
    assert r.status_code == 400


def test_form_unknown_is_404(client):
    assert client.get("/api/connectors/forms/absent").status_code == 404
    assert client.post("/api/connectors/forms/absent/disable").status_code == 404
    assert client.delete("/api/connectors/forms/absent").status_code == 404


def test_form_invalid_field_type_is_400(client):
    r = client.post("/api/connectors/forms", json={
        "form_id": "mauvais", "fields": [{"key": "a", "type": "carte_bancaire"}]})
    assert r.status_code == 400


def test_preview_accepts_declared_form(client):
    """Un formulaire créé localement sert directement de cible de mapping."""
    client.post("/api/connectors/forms", json={
        "form_id": "essai", "fields": [
            {"key": "container_number", "label": "Conteneur",
             "type": "text", "required": True}]})
    job_id = _doc(client, {"container_number": "TGHU1234567"})
    r = client.post("/api/connectors/preview", json={
        "job_id": job_id, "form_id": "essai",
        "rules": [{"source_field": "container_number",
                   "target_field": "container_number"}], "risk": "low"})
    assert r.status_code == 200
    body = r.json()
    assert body["values"]["container_number"]["value"] == "TGHU1234567"
    v = body["validation"]
    assert v["can_transmit"] is True, v["reason"]


# ─────────────── interface commune (métadonnées, statut, accusé, export) ───────────────

def test_connector_status_reports_real_state(client):
    _setup(client)
    assert client.post("/api/connectors/demo_simulated/test").json()["ok"]
    d = client.get("/api/connectors/demo_simulated/status").json()
    assert d["state"] == "functional"
    assert d["last_test"]["ok"] is True


def test_connector_status_unknown_is_404(client):
    assert client.get("/api/connectors/absent/status").status_code == 404


def test_metadata_declares_it_is_not_real(client):
    _setup(client)
    m = client.get("/api/connectors/demo_simulated/metadata").json()
    assert m["is_real_external_system"] is False
    assert m["mode"] == "simulated"


def test_check_auth_endpoint(client):
    _setup(client)
    r = client.post("/api/connectors/demo_simulated/auth",
                    headers={"content-type": "application/json"},
                    content="{}")
    assert r.status_code == 200 and r.json()["ok"] is True


def test_submission_status_and_acknowledgement(client):
    _setup(client, test=True)
    job_id = _doc(client, {"container_number": "TGHU1234567",
                           "vin": "BL-2026-0099", "amount": "9.00"})
    r = client.post("/api/connectors/transmit", json={
        "job_id": job_id, "form_id": "demo_declaration",
        "rules": [{"source_field": "container_number", "target_field": "containerNo"},
                  {"source_field": "vin", "target_field": "bl_reference"},
                  {"source_field": "amount", "target_field": "grossWeight",
                   "transform": "decimal"}],
        "risk": "low", "confirmed": True})
    ref = r.json()["transmission"]["reference"]
    assert ref
    d = client.get(f"/api/connectors/demo_simulated/submission/{ref}").json()
    assert d["status"]["status"] == "accepted"
    assert d["acknowledgement"]["acknowledged"] is True
    # list_errors renvoie une entrée par référence, ici sans erreur
    assert d["errors"][0]["errors"] == []


def test_export_mode_c_writes_three_files(client, tmp_path):
    _setup(client)
    client.post("/api/connectors/assisted_export",
                json={"settings": {"output_dir": str(tmp_path / "exp")}})
    job_id = _doc(client, {"container_number": "TGHU1234567",
                           "vin": "BL-2026-0100", "amount": "3.00"})
    r = client.post("/api/connectors/assisted_export/export", json={
        "job_id": job_id, "form_id": "demo_declaration",
        "rules": [{"source_field": "container_number", "target_field": "containerNo"},
                  {"source_field": "vin", "target_field": "bl_reference"},
                  {"source_field": "amount", "target_field": "grossWeight",
                   "transform": "decimal"}]})
    assert r.status_code == 200, r.text
    body = r.json()
    csv = pathlib.Path(body["csv"])
    assert csv.is_file()
    assert "containerNo" in csv.read_text(encoding="utf-8")
    assert pathlib.Path(body["crosswalk"]).is_file()
    assert pathlib.Path(body["traceability"]).is_file()
    # la traçabilité reprend le rapport de validation
    tr = json.loads(pathlib.Path(body["traceability"]).read_text(encoding="utf-8"))
    assert tr["is_real_external_system"] is False
    assert "validation" in tr


def test_export_refused_by_connector_without_capability(client):
    _setup(client, test=True)
    job_id = _doc(client, {"container_number": "TGHU1234567"})
    r = client.post("/api/connectors/demo_simulated/export",
                    json={"job_id": job_id, "form_id": "demo_declaration", "rules": []})
    assert r.status_code == 400
