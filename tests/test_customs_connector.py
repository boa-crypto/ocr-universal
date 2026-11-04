"""Tests du connecteur douane réel.

Valide le contrat BaseConnector, le parsing OpenAPI, la soumission,
la vérification d'authentification et les cas d'erreur.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from unocr.connectors.contract import (
    FieldSchema,
    FormSchema,
    IntegrationMode,
)
from unocr.connectors.customs import DouaneConnector

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_settings():
    return {
        "base_url": "https://api.douane.test/v2",
        "auth_token_secret_key": "test-token-12345",
    }


@pytest.fixture
def connector(valid_settings):
    return DouaneConnector(settings=valid_settings)


@pytest.fixture
def openapi_spec():
    return json.dumps({
        "openapi": "3.0.0",
        "info": {"title": "Douane API", "version": "2.0"},
        "paths": {
            "/declarations": {
                "post": {
                    "operationId": "submitDeclaration",
                    "summary": "Soumettre une déclaration",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["containerNo", "blReference", "grossWeight"],
                                    "properties": {
                                        "containerNo": {"type": "string", "title": "N° conteneur"},
                                        "blReference": {"type": "string", "title": "Référence BL"},
                                        "grossWeight": {"type": "number", "title": "Poids brut"},
                                        "arrivalDate": {"type": "string", "format": "date", "title": "Date d'arrivée"},
                                    }
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "OK"}, "400": {"description": "Erreur"}}
                }
            }
        }
    })


# ---------------------------------------------------------------------------
# Tests de configuration
# ---------------------------------------------------------------------------

class TestDouaneConnectorConfig:
    def test_connector_id(self):
        assert DouaneConnector.connector_id == "customs_api"

    def test_is_real_external_system(self):
        assert DouaneConnector.is_real_external_system is True

    def test_mode_api(self):
        assert DouaneConnector.mode == IntegrationMode.API

    def test_capabilities_required(self):
        caps = [c.value for c in DouaneConnector.capabilities]
        assert "test_connection" in caps
        assert "submit" in caps
        assert "check_auth" in caps

    def test_without_base_url(self):
        c = DouaneConnector()
        assert c.base_url == ""
        assert c.auth_token == ""
        assert c.openapi_path is None


# ---------------------------------------------------------------------------
# Tests de test_connection
# ---------------------------------------------------------------------------

class TestConnection:
    def test_no_base_url(self, connector):
        connector.settings = {}
        result = connector.test_connection()
        assert result.ok is False
        assert "base_url" in result.detail.lower()

    def test_with_base_url_mocked(self, connector):
        with patch("unocr.connectors.customs.httpx.Client") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            MockClient.return_value = mock_client
            result = connector.test_connection()
            assert result.ok is True
            assert "joignable" in result.detail.lower()

    def test_connect_error(self, connector):
        with patch("unocr.connectors.customs.httpx.Client") as MockClient:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            import httpx
            mock_client.get.side_effect = httpx.ConnectError("host unreachable")
            MockClient.return_value = mock_client
            result = connector.test_connection()
            assert result.ok is False
            assert "impossible" in result.detail.lower()


# ---------------------------------------------------------------------------
# Tests de check_auth
# ---------------------------------------------------------------------------

class TestAuth:
    def test_no_token(self, connector):
        connector.settings = {"base_url": "https://test"}
        result = connector.check_auth()
        assert result.ok is False
        assert "jeton" in result.detail.lower()

    def test_valid_token_mocked(self, connector):
        with patch("unocr.connectors.customs.httpx.Client") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"scopes": ["submit", "read"]}
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            MockClient.return_value = mock_client
            result = connector.check_auth()
            assert result.ok is True
            assert "valide" in result.detail.lower()

    def test_unauthorized(self, connector):
        with patch("unocr.connectors.customs.httpx.Client") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 401
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            MockClient.return_value = mock_client
            result = connector.check_auth()
            assert result.ok is False
            assert "rejeté" in result.detail.lower()


# ---------------------------------------------------------------------------
# Tests de discover_forms
# ---------------------------------------------------------------------------

class TestDiscoverForms:
    def test_no_schema(self, connector):
        connector.openapi_path = None
        connector.schema_path = None
        forms = connector.discover_forms()
        assert forms == []

    def test_valid_openapi(self, connector, openapi_spec, tmp_path):
        spec_file = tmp_path / "openapi.json"
        spec_file.write_text(openapi_spec, encoding="utf-8")
        connector.openapi_path = spec_file
        forms = connector.discover_forms()
        assert len(forms) == 1
        form = forms[0]
        assert form.form_id == "submitDeclaration"
        assert form.source == "discovered"
        field_names = {f.external_name for f in form.fields}
        assert "containerNo" in field_names
        assert "blReference" in field_names
        assert "grossWeight" in field_names

    def test_invalid_openapi(self, connector, tmp_path):
        bad_spec = tmp_path / "bad.json"
        bad_spec.write_text("{invalid json", encoding="utf-8")
        connector.openapi_path = bad_spec
        forms = connector.discover_forms()
        assert len(forms) == 1
        assert forms[0].source == "declared"
        assert "error" in forms[0].version


# ---------------------------------------------------------------------------
# Tests de prefill_form
# ---------------------------------------------------------------------------

class TestPrefillForm:
    def test_prefill_complete(self, connector):
        form = FormSchema(
            form_id="test", label="Test",
            fields=[
                FieldSchema("containerNo", "N° conteneur", "identifier", required=True),
                FieldSchema("grossWeight", "Poids", "amount", required=True),
            ])
        result = connector.prefill_form(form, {"containerNo": "CSQU3054383", "grossWeight": "3500"})
        assert result["ready"] is True
        assert result["filled"]["containerNo"] == "CSQU3054383"
        assert result["missing"] == []

    def test_prefill_missing_required(self, connector):
        form = FormSchema(
            form_id="test", label="Test",
            fields=[
                FieldSchema("containerNo", "N° conteneur", "identifier", required=True),
            ])
        result = connector.prefill_form(form, {})
        assert result["ready"] is False
        assert "containerNo" in result["missing"]


# ---------------------------------------------------------------------------
# Tests de submit
# ---------------------------------------------------------------------------

class TestSubmit:
    def test_no_config(self, connector):
        connector.settings = {}
        form = FormSchema(form_id="test", fields=[])
        result = connector.submit(form, {})
        assert result.accepted is False
        assert "configuré" in result.detail.lower()

    def test_successful_submit_mocked(self, connector):
        with patch("unocr.connectors.customs.httpx.Client") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 201
            mock_resp.json.return_value = {"reference": "DOUANE-2024-00001", "message": "OK"}
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_resp
            MockClient.return_value = mock_client
            form = FormSchema(form_id="test", fields=[])
            result = connector.submit(form, {"containerNo": "CSQU3054383"})
            assert result.accepted is True
            assert result.reference == "DOUANE-2024-00001"
            assert result.pending_confirmation is False

    def test_idempotent_duplicate(self, connector):
        with patch("unocr.connectors.customs.httpx.Client") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 409
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_resp
            MockClient.return_value = mock_client
            form = FormSchema(form_id="test", fields=[])
            result = connector.submit(form, {"containerNo": "CSQU3054383"},
                                      idempotency_key="key-123")
            assert result.accepted is True
            assert result.pending_confirmation is True

    def test_network_error(self, connector):
        with patch("unocr.connectors.customs.httpx.Client") as MockClient:
            import httpx
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.side_effect = httpx.ConnectError("timeout")
            MockClient.return_value = mock_client
            form = FormSchema(form_id="test", fields=[])
            result = connector.submit(form, {"containerNo": "CSQU3054383"})
            assert result.accepted is False
            assert "joindre" in result.detail.lower()


# ---------------------------------------------------------------------------
# Tests de get_status / get_acknowledgement
# ---------------------------------------------------------------------------

class TestStatus:
    def test_no_config(self, connector):
        connector.settings = {}
        status = connector.get_status("REF-123")
        assert status["status"] == "unconfigured"

    def test_success_mocked(self, connector):
        with patch("unocr.connectors.customs.httpx.Client") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"status": "accepted", "reference": "REF-123"}
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            MockClient.return_value = mock_client
            status = connector.get_status("REF-123")
            assert status["status"] == "accepted"

    def test_acknowledged(self, connector):
        with patch("unocr.connectors.customs.httpx.Client") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"status": "accepted"}
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            MockClient.return_value = mock_client
            ack = connector.get_acknowledgement("REF-123")
            assert ack["acknowledged"] is True
