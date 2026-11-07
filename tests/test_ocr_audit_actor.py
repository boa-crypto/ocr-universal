"""Attribution serveur des validations/corrections, pas preuve d'identité humaine."""
import json

import pytest
from test_ocr_dossier_scope import scoped as scoped
from test_ocr_dossier_scope import snapshot

from unocr import api
from unocr.rbac import RegistreRBAC

EVENTS = {"validate": "ocr_extraction_validee", "correct": "ocr_champ_corrige"}


def events(cfg):
    path = cfg.log_dir / "audit.log"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def act(scoped, action, user="a", folder="a", extraction="a", extra=None):
    client, folders, _, extractions, _, _ = scoped
    body = {"champ_nom": "sample", "nouvelle_valeur": "CORRECT75"} if action == "correct" else {}
    opts = {"headers": {"Authorization": "Bearer FAKE73-" + user} if user is not None else {}}
    url = f'/api/dossiers/{folders[folder]}/documents-ocr/{extractions.get(extraction, extraction)}'
    url += "/valider" if action == "validate" else "/corriger"
    if extra == "body":
        body.update(user="SPOOF75", acteur="SPOOF75", utilisateur="SPOOF75")
    elif extra == "header":
        opts["headers"].update({"X-User": "SPOOF75", "X-Actor": "SPOOF75"})
    elif extra == "query":
        opts["params"] = {"user": "SPOOF75", "acteur": "SPOOF75"}
    elif extra == "missing_field":
        body["champ_nom"] = "missing75"
    return client.post(url, json=body, **opts)


def assert_success(scoped, action, actor, extraction="a"):
    _, _, _, extractions, integration, cfg = scoped
    success = [e for e in events(cfg) if e["event"] in EVENTS.values()]
    assert len(success) == 1
    expected = {"event": EVENTS[action], "extraction_id": extractions[extraction], "user": actor}
    if action == "correct":
        expected["champ"] = "sample"
    assert {k: v for k, v in success[0].items() if k != "ts"} == expected
    text = json.dumps(success, ensure_ascii=False)
    assert all(secret not in text for secret in ("FAKE73-", "PRIVATE73", "CORRECT75", "SPOOF75"))
    stored = integration.extraction_store.get(extractions[extraction])
    if action == "validate":
        assert stored.statut == "validated"
    else:
        assert stored.champs_extraits[0].valeur_confirmee == "CORRECT75"


@pytest.mark.parametrize("action", EVENTS)
@pytest.mark.parametrize("user,folder,actor", [("a", "a", "a"), ("b", "b", "b"),
                                              ("admin", "b", "admin"), ("master", "b", "environnement")])
def test_success_names_server_resolved_principal(scoped, action, user, folder, actor):
    response = act(scoped, action, user, folder, folder)
    assert response.status_code == 200, response.text
    assert_success(scoped, action, actor, folder)


@pytest.mark.parametrize("action", EVENTS)
@pytest.mark.parametrize("extra", ["body", "header", "query"])
def test_client_actor_cannot_replace_resolved_principal(scoped, action, extra):
    assert act(scoped, action, extra=extra).status_code == 200
    assert_success(scoped, action, "a")


@pytest.mark.parametrize("action", EVENTS)
@pytest.mark.parametrize("token", [False, True], ids=["open", "shared-token"])
def test_no_rbac_names_local_not_individual_identity(scoped, monkeypatch, tmp_path, action, token):
    empty = tmp_path / "no-rbac"
    empty.mkdir()
    monkeypatch.setattr(api, "_rbac", RegistreRBAC.charger(empty))
    monkeypatch.setattr(api, "_AUTH_TOKEN", "FAKE73-master" if token else None)
    assert act(scoped, action, "master" if token else None).status_code == 200
    assert_success(scoped, action, "local")


@pytest.mark.parametrize("action", EVENTS)
@pytest.mark.parametrize("user,folder,extraction,status", [
    ("reader", "a", "a", 403), ("a", "b", "b", 403),
    ("a", "a", "b", 403), ("unknown", "a", "a", 401), (None, "a", "a", 401),
])
def test_refused_requests_have_no_success_or_modification(scoped, action, user, folder, extraction, status):
    cfg = scoped[-1]
    before = snapshot(cfg)
    assert act(scoped, action, user, folder, extraction).status_code == status
    assert snapshot(cfg) == before
    assert not [e for e in events(cfg) if e["event"] in EVENTS.values()]


def test_missing_field_still_has_no_attributed_phantom_success(scoped):
    cfg = scoped[-1]
    before = snapshot(cfg)
    assert act(scoped, "correct", extra="missing_field").status_code == 404
    assert snapshot(cfg) == before
    assert not [e for e in events(cfg) if e["event"] in EVENTS.values()]


@pytest.mark.parametrize("action", EVENTS)
def test_missing_extraction_has_no_success(scoped, action):
    cfg = scoped[-1]
    before = snapshot(cfg)
    assert act(scoped, action, extraction="missing75").status_code == 404
    assert snapshot(cfg) == before
    assert not [e for e in events(cfg) if e["event"] in EVENTS.values()]


@pytest.mark.parametrize("action", EVENTS)
def test_sequential_users_do_not_inherit_previous_actor(scoped, action):
    cfg = scoped[-1]
    for user in ("a", "b", "a"):
        assert act(scoped, action, user, user, user).status_code == 200
    success = [e for e in events(cfg) if e["event"] == EVENTS[action]]
    assert [e["user"] for e in success] == ["a", "b", "a"]
    assert [e["extraction_id"] for e in success] == [scoped[3][key] for key in ("a", "b", "a")]
