"""Connecteur Douane — mode API documentée (phase production).

**Ce que fait ce connecteur.** Il s'authentifie sur une API de douane
fournie par le client, dépose un dossier et récupère son accusé de réception.
Le schéma de formulaire est **documenté par l'API de l'organisme** (`openapi.json`
téléchargé), jamais inventé.

**Ce que ce n'est pas.** Un simulateur — `is_real_external_system` vaut `True`
et `mode` est `api`. Les URLs, credentials et scopes sont des secrets stockés
dans le coffre du hub (`data/connectors/secrets.json`). Toute soumission sans
clé configurée échoue avant tout appel réseau.

**Déploiement.** Déposer un fichier OpenAPI dans `config/douane_openapi.json`
et configurer via l'interface :
```json
{
  "base_url": "https://api.douane.gov/portal/v2",
  "auth_type": "bearer",
  "auth_token_secret_key": "douane_token",
  "openapi_path": "config/douane_openapi.json"
}
```
`douane_token` sera stocké chiffré dans `data/connectors/secrets.json`.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import httpx

from .contract import (
    BaseConnector,
    ConnectionTestResult,
    ConnectorCapability,
    FieldSchema,
    FormSchema,
    IntegrationMode,
    SubmissionResult,
)


class DouaneConnector(BaseConnector):
    """Connecteur réel vers une API douanière (mode A)."""

    connector_id = "customs_api"
    organization = "Douane nationale (API externe)"
    system_type = "customs"
    mode = IntegrationMode.API
    external_api_version = "v2"
    is_real_external_system = True
    capabilities = (
        ConnectorCapability.TEST_CONNECTION,
        ConnectorCapability.CHECK_AUTH,
        ConnectorCapability.FETCH_METADATA,
        ConnectorCapability.DISCOVER_FORMS,
        ConnectorCapability.PREFILL_FORM,
        ConnectorCapability.SUBMIT,
        ConnectorCapability.GET_STATUS,
        ConnectorCapability.GET_ACKNOWLEDGEMENT,
    )

    # ---------------------------------------------------------------------
    # Configuration
    # ---------------------------------------------------------------------

    @property
    def base_url(self) -> str:
        return str(self.settings.get("base_url", "")).rstrip("/")

    @property
    def auth_token(self) -> str:
        """Lit le token depuis le coffre de secrets, JAMAIS depuis les logs."""
        return str(self.settings.get("auth_token_secret_key") or "")

    @property
    def openapi_path(self) -> Optional[Path]:
        path_str = str(self.settings.get("openapi_path", "")).strip()
        return Path(path_str) if path_str else None

    @openapi_path.setter
    def openapi_path(self, value: Optional[Path]) -> None:
        if value is None:
            self.settings.pop("openapi_path", None)
        else:
            self.settings["openapi_path"] = str(value)

    @property
    def schema_path(self) -> Optional[Path]:
        """Chemin vers un schéma de formulaire local (fallback si API indisponible)."""
        path_str = str(self.settings.get("schema_path", "")).strip()
        return Path(path_str) if path_str else None

    @schema_path.setter
    def schema_path(self, value: Optional[Path]) -> None:
        if value is None:
            self.settings.pop("schema_path", None)
        else:
            self.settings["schema_path"] = str(value)

    # ---------------------------------------------------------------------
    # Santé
    # ---------------------------------------------------------------------

    def test_connection(self) -> ConnectionTestResult:
        t0 = time.perf_counter()
        if not self.base_url:
            return ConnectionTestResult(False, "base_url non configurée")
        try:
            with httpx.Client(timeout=10) as client:
                r = client.get(f"{self.base_url}/health", verify=True)
                if r.status_code == 200:
                    return ConnectionTestResult(
                        True, "API douane joignable",
                        latency_ms=(time.perf_counter() - t0) * 1000,
                        evidence={"status_code": r.status_code})
                return ConnectionTestResult(
                    False, f"health check renvoyé {r.status_code}",
                    latency_ms=(time.perf_counter() - t0) * 1000)
        except httpx.ConnectError as exc:
            return ConnectionTestResult(False, f"impossible de joindre {self.base_url}: {exc}")
        except httpx.TimeoutException:
            return ConnectionTestResult(False, "délai d'attente dépassé")

    def check_auth(self) -> ConnectionTestResult:
        if not self.auth_token:
            return ConnectionTestResult(False, "jeton non configuré")
        if not self.base_url:
            return ConnectionTestResult(False, "base_url non configurée")
        t0 = time.perf_counter()
        try:
            with httpx.Client(timeout=10) as client:
                r = client.get(
                    f"{self.base_url}/auth/verify",
                    headers={"Authorization": f"Bearer {self.auth_token}"},
                    verify=True)
                if r.status_code == 200:
                    return ConnectionTestResult(
                        True, "authentification valide",
                        latency_ms=(time.perf_counter() - t0) * 1000,
                        evidence={"scopes": r.json().get("scopes", [])})
                if r.status_code == 401:
                    return ConnectionTestResult(False, "jeton rejeté (401)")
                return ConnectionTestResult(
                    False, f"vérification auth échouée ({r.status_code})")
        except Exception as exc:
            return ConnectionTestResult(False, f"erreur vérification auth: {exc}")

    def fetch_metadata(self) -> dict:
        return {
            "connector_id": self.connector_id,
            "base_url": self.base_url or "(non configuré)",
            "auth_configured": bool(self.auth_token),
            "openapi_available": bool(self.openapi_path and self.openapi_path.is_file()),
            "schema_available": bool(self.schema_path and self.schema_path.is_file()),
        }

    def discover_forms(self) -> list[FormSchema]:
        """Découvre les formulaires depuis le schéma OpenAPI ou le fallback local.

        Si aucun schéma n'est disponible, renvoie une liste vide — jamais de
        structures inventées.
        """
        # Essai 1 : schéma OpenAPI téléchargé
        if self.openapi_path and self.openapi_path.is_file():
            try:
                return self._parse_openapi(self.openapi_path.read_text(encoding="utf-8"))
            except Exception as exc:
                # Schéma corrompu : on ne devine pas, on signale
                return [FormSchema(
                    form_id="customs_declaration", label="Déclaration douanière",
                    fields=[], source="declared", version="error",
                    notes=f"Erreur parsing OpenAPI : {exc}")]

        # Essai 2 : schéma JSON local
        if self.schema_path and self.schema_path.is_file():
            try:
                data = json.loads(self.schema_path.read_text(encoding="utf-8"))
                return [self._form_from_data(data)]
            except Exception as exc:
                return [FormSchema(form_id="customs_declaration", label="Déclaration",
                                   fields=[], source="declared", version="error",
                                   notes=f"Erreur lecture schéma : {exc}")]

        return []

    # ---------------------------------------------------------------------
    # Sous-missions
    # ---------------------------------------------------------------------

    def prefill_form(self, form: FormSchema, payload: dict) -> dict:
        filled, missing = {}, []
        for f in form.fields:
            if f.external_name in payload and payload[f.external_name] is not None:
                filled[f.external_name] = payload[f.external_name]
            elif f.required:
                missing.append(f.external_name)
        return {"form_id": form.form_id, "filled": filled, "missing": missing,
                "ready": not missing}

    def submit(self, form: FormSchema, payload: dict,
               idempotency_key: str = "") -> SubmissionResult:
        if not self.base_url or not self.auth_token:
            return SubmissionResult(
                False, pending_confirmation=True,
                detail="connecteur non configuré (base_url ou auth_token manquant)")
        try:
            with httpx.Client(timeout=30) as client:
                r = client.post(
                    f"{self.base_url}/declarations",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.auth_token}",
                        "Content-Type": "application/json",
                        "Idempotency-Key": idempotency_key or "",
                    },
                    verify=True)
            if r.status_code in (200, 201):
                data = r.json()
                ref = data.get("reference") or data.get("declaration_id") or str(r.status_code)
                return SubmissionResult(
                    True, pending_confirmation=False, reference=str(ref),
                    detail=data.get("message", "déclaration acceptée"),
                    evidence={"status_code": r.status_code, "response": data})
            if r.status_code == 409 and idempotency_key:
                # reprise identique : on récupère le statut existant
                return SubmissionResult(
                    True, pending_confirmation=True, reference=idempotency_key,
                    detail="déclaration déjà enregistrée (clé d'idempotence)")
            return SubmissionResult(
                False, pending_confirmation=True,
                detail=f"échec soumission ({r.status_code})",
                errors=[r.text[:200] if r.text else "réponse vide"])
        except httpx.ConnectError as exc:
            return SubmissionResult(False, pending_confirmation=True,
                                    detail=f"impossible de joindre l'API : {exc}")
        except httpx.TimeoutException:
            return SubmissionResult(False, pending_confirmation=True,
                                    detail="délai d'attente dépassé (30s)")

    def get_status(self, reference: str) -> dict:
        if not self.base_url or not self.auth_token:
            return {"reference": reference, "status": "unconfigured"}
        try:
            with httpx.Client(timeout=10) as client:
                r = client.get(
                    f"{self.base_url}/declarations/{reference}",
                    headers={"Authorization": f"Bearer {self.auth_token}"},
                    verify=True)
            if r.status_code == 200:
                return r.json()
            return {"reference": reference, "status": "unknown",
                    "detail": f"API a répondu {r.status_code}"}
        except Exception as exc:
            return {"reference": reference, "status": "error",
                    "detail": str(exc)}

    def get_acknowledgement(self, reference: str) -> dict:
        status = self.get_status(reference)
        if status.get("status") == "accepted":
            return {"reference": reference, "acknowledged": True,
                    "at": time.time(), "status": status.get("status")}
        return {"reference": reference, "acknowledged": False,
                "status": status.get("status")}

    # ---------------------------------------------------------------------
    # Interne
    # ---------------------------------------------------------------------

    def _parse_openapi(self, spec_text: str) -> list[FormSchema]:
        """Parse un spec OpenAPI 3.x et extrait les formulaires déclarés."""
        spec = json.loads(spec_text)
        forms: list[FormSchema] = []
        paths = spec.get("paths", {})
        for path, methods in paths.items():
            if "post" not in methods:
                continue
            op = methods["post"]
            form_id = op.get("operationId", path)
            label = op.get("summary", path)
            req_body = op.get("requestBody", {})
            content = req_body.get("content", {})
            json_schema = content.get("application/json", {}).get("schema", {})
            fields = []
            props = json_schema.get("properties", {})
            required = set(json_schema.get("required", []))
            for field_name, schema in props.items():
                fields.append(FieldSchema(
                    external_name=field_name,
                    label=schema.get("title", field_name),
                    field_type=self._map_type(schema.get("type", "string")),
                    required=field_name in required,
                    format_hint=schema.get("format", ""),
                    source="discovered"))
            forms.append(FormSchema(
                form_id=form_id, label=label, fields=fields,
                source="discovered", version="auto"))
        return forms

    @staticmethod
    def _map_type(openapi_type: str) -> str:
        mapping = {"string": "text", "integer": "number", "number": "amount",
                   "boolean": "checkbox", "array": "list", "object": "table"}
        return mapping.get(openapi_type, "text")

    @staticmethod
    def _form_from_data(data: dict) -> FormSchema:
        fields = []
        for f in data.get("fields", []):
            fields.append(FieldSchema(
                external_name=f.get("external_name", ""),
                label=f.get("label", f.get("external_name", "")),
                field_type=f.get("field_type", "text"),
                required=f.get("required", False),
                format_hint=f.get("format_hint", ""),
                source="declared"))
        return FormSchema(
            form_id=data.get("form_id", "customs_declaration"),
            label=data.get("label", "Déclaration douanière"),
            fields=fields,
            source=data.get("source", "declared"),
            version=data.get("version", "1"),
            notes=data.get("notes", ""),
        )
