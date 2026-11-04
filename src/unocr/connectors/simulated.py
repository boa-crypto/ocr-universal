"""Connecteur de démonstration — système **simulé** local (phase 6).

**Ce que c'est.** Un système cible factice, hébergé en mémoire dans le
processus, qui reçoit les données transmises et renvoie un accusé de
réception. Il sert à éprouver le Hub de bout en bout — mapping, validation,
transmission, statut, accusé, erreurs — **sans contacter aucun système réel**.

**Ce que ce n'est pas.** Une intégration réelle. `is_real_external_system`
vaut `False`, le mode est `simulated`, et l'interface le signale
explicitement. Aucun endpoint, aucune administration, aucun identifiant
d'accès n'est inventé : le « système » est une liste Python locale.

Le connecteur simulé respecte malgré tout les règles du Hub :
- il ne confirme une réception que lorsque le traitement factice a réussi ;
- il renvoie des erreurs de validation réalistes (champ obligatoire manquant,
  format invalide, valeur hors liste) ;
- il expose un numéro de référence et un statut consultable.
"""
from __future__ import annotations

import time

from .contract import (
    BaseConnector,
    ConnectionTestResult,
    ConnectorCapability,
    ConnectorState,
    FieldSchema,
    FormSchema,
    IntegrationMode,
    SubmissionResult,
)


class SimulatedTargetSystem:
    """Système cible factice, partagé entre les instances de test."""

    def __init__(self):
        self.dossiers: dict[str, dict] = {}
        self.by_key: dict[str, str] = {}     # clé d'idempotence -> référence
        self.counter = 0
        # formulaire « déclaré » (pas documenté : aucun organisme réel)
        self.form = FormSchema(
            form_id="demo_declaration",
            label="Déclaration de démonstration",
            organization="Système simulé (démonstration)",
            fields=[
                FieldSchema("containerNo", "N° de conteneur", "identifier", True,
                            max_length=11, source="declared"),
                FieldSchema("bl_reference", "Référence BL", "identifier", True,
                            source="declared"),
                FieldSchema("grossWeight", "Poids brut (kg)", "amount", True,
                            source="declared"),
                FieldSchema("arrivalDate", "Date d'arrivée", "date", False,
                            format_hint="AAAA-MM-JJ", source="declared"),
                FieldSchema("cargoType", "Type de marchandise", "list", False,
                            allowed_values=["Divers", "Frigo", "Dangereux"],
                            source="declared"),
            ],
            source="declared",
            version="1.0",
            notes="Schéma de démonstration — ne correspond à aucun organisme réel.",
        )
        self.healthy = True

    def next_reference(self) -> str:
        self.counter += 1
        return f"DEMO-{time.strftime('%Y')}-{self.counter:05d}"

    def validate(self, payload: dict) -> list[str]:
        """Erreurs de validation réalistes (comme le ferait un vrai système)."""
        errors = []
        for f in self.form.fields:
            if f.required and not payload.get(f.external_name):
                errors.append(f"champ obligatoire manquant : {f.external_name}")
            val = payload.get(f.external_name)
            if val is None:
                continue
            if f.field_type == "date" and len(str(val)) != 10:
                errors.append(f"{f.external_name} : date attendue AAAA-MM-JJ")
            if f.field_type == "amount":
                try:
                    float(str(val))
                except ValueError:
                    errors.append(f"{f.external_name} : montant non numérique")
            if f.allowed_values and str(val) not in f.allowed_values:
                errors.append(f"{f.external_name} : « {val} » hors liste autorisée")
        return errors

    def submit(self, payload: dict, idempotency_key: str) -> tuple[bool, dict]:
        if not self.healthy:
            return False, {"detail": "service momentanément indisponible"}
        if idempotency_key and idempotency_key in self.by_key:
            # même clé → même dossier, pas de doublon
            return True, self.dossiers[self.by_key[idempotency_key]]

        errors = self.validate(payload)
        if errors:
            return False, {"errors": errors}
        ref = self.next_reference()
        record = {"reference": ref, "payload": dict(payload),
                  "status": "accepted", "at": time.time(),
                  "idempotency_key": idempotency_key}
        self.dossiers[ref] = record
        if idempotency_key:
            self.by_key[idempotency_key] = ref
        return True, record


# instance partagée : persiste le temps du processus
SIMULATED = SimulatedTargetSystem()


class SimulatedConnector(BaseConnector):
    """Connecteur de démonstration. Ne contacte AUCUN système externe."""

    connector_id = "demo_simulated"
    organization = "Système simulé — démonstration"
    system_type = "demo"
    mode = IntegrationMode.SIMULATED
    external_api_version = "demo-1.0"
    is_real_external_system = False
    capabilities = (
        ConnectorCapability.TEST_CONNECTION,
        ConnectorCapability.CHECK_AUTH,
        ConnectorCapability.FETCH_METADATA,
        ConnectorCapability.DISCOVER_FORMS,
        ConnectorCapability.PREFILL_FORM,
        ConnectorCapability.SUBMIT,
        ConnectorCapability.GET_STATUS,
        ConnectorCapability.GET_ACKNOWLEDGEMENT,
        ConnectorCapability.LIST_ERRORS,
        ConnectorCapability.CANCEL,
        ConnectorCapability.RESUME,
    )

    # ─────────────────────────── test réel ───────────────────────────

    def test_connection(self) -> ConnectionTestResult:
        """Le test est réel : il interroge le système simulé et mesure le temps."""
        t0 = time.perf_counter()
        try:
            meta = self.fetch_metadata()
        except Exception as exc:
            return ConnectionTestResult(False, f"système simulé injoignable : {exc}",
                              latency_ms=(time.perf_counter() - t0) * 1000)
        if not meta.get("healthy"):
            return ConnectionTestResult(False, "système simulé en panne",
                              latency_ms=(time.perf_counter() - t0) * 1000)
        return ConnectionTestResult(
            True, "système simulé joignable (démonstration, hors ligne)",
            latency_ms=(time.perf_counter() - t0) * 1000,
            evidence={"formulaires": 1, "mode": "simulated"})

    def check_auth(self) -> ConnectionTestResult:
        # aucun secret nécessaire pour la démonstration
        return ConnectionTestResult(True, "aucune authentification requise (démonstration)")

    def fetch_metadata(self) -> dict:
        return {"system": self.organization, "mode": "simulated",
                "healthy": SIMULATED.healthy, "api_version": self.external_api_version,
                "dossiers": len(SIMULATED.dossiers),
                "is_real_external_system": False}

    def discover_forms(self) -> list[FormSchema]:
        """Le schéma est **déclaré** par le connecteur de démonstration.

        Un connecteur réel ne pourrait renvoyer ici que des formulaires dont
        l'API de l'organisme l'autorise — jamais une structure devinée.
        """
        return [SIMULATED.form]

    # ─────────────────────────── opérations ───────────────────────────

    def prefill_form(self, form: FormSchema, payload: dict) -> dict:
        """Préremplit les champs cibles avec les valeurs mappées."""
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
        """Transmet au système simulé. `pending_confirmation` ne vaut False
        que si le système a réellement accepté et renvoyé une référence."""
        if form.form_id != SIMULATED.form.form_id:
            return SubmissionResult(
                False, pending_confirmation=False,
                detail=f"formulaire inconnu du système simulé : {form.form_id}",
                errors=[f"formulaire « {form.form_id} » inconnu"])
        ok, res = SIMULATED.submit(payload, idempotency_key)
        if not ok:
            return SubmissionResult(
                False, pending_confirmation=False,
                detail="rejeté par le système simulé",
                errors=res.get("errors") or [res.get("detail", "erreur inconnue")])
        return SubmissionResult(
            True, pending_confirmation=False, reference=res["reference"],
            detail=f"dossier accepté (simulé) — référence {res['reference']}",
            evidence={"simulated": True, "reference": res["reference"],
                      "at": res["at"]})

    def get_status(self, reference: str) -> dict:
        rec = SIMULATED.dossiers.get(reference)
        if rec is None:
            ref = SIMULATED.by_key.get(reference)
            if ref:
                rec = SIMULATED.dossiers[ref]
                return {"reference": ref, "status": rec["status"],
                        "at": rec["at"], "matched_by": "idempotency_key",
                        "simulated": True}
            return {"reference": reference, "status": "unknown",
                    "detail": "référence inconnue du système simulé"}
        return {"reference": reference, "status": rec["status"],
                "at": rec["at"], "simulated": True}

    def get_acknowledgement(self, reference: str) -> dict:
        """Accepte une référence **ou** une clé d'idempotence : sans référence
        connue, c'est la seule façon de rapprocher une transmission dont
        l'issue est incertaine."""
        rec = SIMULATED.dossiers.get(reference)
        if rec is None:
            ref = SIMULATED.by_key.get(reference)
            rec = SIMULATED.dossiers.get(ref) if ref else None
            if rec is not None:
                return {"reference": ref, "acknowledged": True,
                        "status": rec["status"], "at": rec["at"],
                        "matched_by": "idempotency_key", "simulated": True}
        if rec is None:
            return {"reference": reference, "acknowledged": False}
        return {"reference": reference, "acknowledged": True,
                "status": rec["status"], "at": rec["at"], "simulated": True}

    def list_errors(self, reference: str = "") -> list[dict]:
        if reference:
            rec = SIMULATED.dossiers.get(reference)
            if rec is None:
                return [{"reference": reference, "error": "inconnu"}]
            return [{"reference": reference, "errors": []}] if rec["status"] == "accepted" else []
        return [{"reference": r, "status": v["status"]}
                for r, v in SIMULATED.dossiers.items()
                if v["status"] != "accepted"]

    def cancel(self, reference: str) -> SubmissionResult:
        rec = SIMULATED.dossiers.get(reference)
        if rec is None:
            return SubmissionResult(False, pending_confirmation=False,
                                    detail="référence inconnue",
                                    errors=["référence inconnue"])
        rec["status"] = "cancelled"
        return SubmissionResult(True, pending_confirmation=False,
                                reference=reference,
                                detail="dossier annulé (simulé)",
                                evidence={"simulated": True})

    def resume(self, reference: str) -> SubmissionResult:
        rec = SIMULATED.dossiers.get(reference)
        if rec is None:
            return SubmissionResult(False, pending_confirmation=False,
                                    detail="référence inconnue",
                                    errors=["référence inconnue"])
        rec["status"] = "accepted"
        return SubmissionResult(True, pending_confirmation=False,
                                reference=reference,
                                detail="dossier repris (simulé)",
                                evidence={"simulated": True})

    # ─────────────────────────── utilitaires de test ───────────────────────────

    def set_healthy(self, healthy: bool) -> None:
        """Simule une panne du système cible (tests d'erreur)."""
        SIMULATED.healthy = healthy
        if not healthy:
            self._state = ConnectorState.DEGRADED
