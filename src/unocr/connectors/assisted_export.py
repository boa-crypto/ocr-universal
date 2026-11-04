"""Connecteur « export structuré assisté » — Mode C (phase 6).

**Quand l'utiliser.** Ni API exploitable, ni automatisation de formulaire
autorisée. Le système produit malgré tout de la valeur : un dossier structuré,
un tableau de correspondance et un écran de saisie assistée.

**Ce qu'il fait.** Génère, pour un document et un formulaire cible :
- un fichier CSV des valeurs mappées (format accepté le plus courant) ;
- un tableau de correspondance champ cible ↔ valeur ↔ source OCR ↔ page ;
- un fichier JSON conservant la traçabilité complète.

**Ce qu'il ne fait pas.** Transmettre quoi que ce soit à un système externe :
il n'y a rien à transmettre, l'utilisateur recopie ou importe le fichier dans
le système cible. `submit` lève donc `NotSupportedError` — annoncer un envoi
qui n'a pas lieu serait un mensonge.
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from .contract import (
    BaseConnector,
    ConnectionTestResult,
    ConnectorCapability,
    FormSchema,
    IntegrationMode,
    NotSupportedError,
    SubmissionResult,
)
from .validation import ValidationReport


class AssistedExportConnector(BaseConnector):
    """Mode C — export assisté, sans contact avec un système externe."""

    connector_id = "assisted_export"
    organization = "Export assisté (local)"
    system_type = "local"
    mode = IntegrationMode.ASSISTED_EXPORT
    external_api_version = "n/a"
    is_real_external_system = False
    capabilities = (
        ConnectorCapability.TEST_CONNECTION,
        ConnectorCapability.EXPORT_DATA,
        ConnectorCapability.PREFILL_FORM,
    )

    def __init__(self, settings=None):
        super().__init__(settings)
        self.output_dir = Path((settings or {}).get("output_dir", "data/exports"))

    # ─────────────────────────── test ───────────────────────────

    def test_connection(self) -> ConnectionTestResult:
        """Vérifie réellement que le répertoire de sortie est utilisable."""
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            probe = self.output_dir / ".write_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
        except OSError as exc:
            return ConnectionTestResult(False, f"répertoire de sortie inutilisable : {exc}")
        return ConnectionTestResult(True, f"répertoire utilisable : {self.output_dir}",
                          evidence={"writable": True, "path": str(self.output_dir)})

    def configure(self, settings: dict) -> None:
        super().configure(settings)
        self.output_dir = Path((settings or {}).get("output_dir",
                                                    "data/exports"))

    # ─────────────────────────── génération ───────────────────────────

    def prefill_form(self, form: FormSchema, payload: dict) -> dict:
        """Prépare l'écran de saisie assistée (valeurs + champs manquants)."""
        filled, missing = {}, []
        for f in form.fields:
            if payload.get(f.external_name) is not None:
                filled[f.external_name] = payload[f.external_name]
            elif f.required:
                missing.append(f.external_name)
        return {"form_id": form.form_id, "filled": filled, "missing": missing,
                "ready": not missing}

    def build_csv(self, form: FormSchema, report: ValidationReport) -> str:
        """CSV des valeurs mappées — anti-injection de formules."""
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["champ_cible", "libelle", "valeur", "type",
                    "obligatoire", "confiance", "source_ocr", "page"])
        for f in form.fields:
            mv = report.values.get(f.external_name)
            if mv is None:
                continue
            w.writerow([f.external_name, f.label, mv.value or "",
                        f.field_type, "oui" if f.required else "non",
                        mv.confidence, mv.source_field or "", mv.source_page or ""])
        return buf.getvalue()

    def build_crosswalk(self, form: FormSchema, report: ValidationReport) -> str:
        """Tableau de correspondance lisible (Markdown)."""
        lines = ["| Champ cible | Libellé | Valeur | Source OCR | Page | Confiance |",
                 "|---|---|---|---|---|---|"]
        for f in form.fields:
            mv = report.values.get(f.external_name)
            if mv is None:
                continue
            lines.append(
                f"| `{f.external_name}` | {f.label} | {mv.value or '—'} | "
                f"`{mv.source_field or '—'}` | {mv.source_page or '—'} | "
                f"{mv.confidence} |")
        return "\n".join(lines) + "\n"

    def export(self, form: FormSchema, report: ValidationReport,
               job_id: str = "") -> dict:
        """Écrit les trois fichiers du dossier assisté. Renvoie les chemins."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        stem = f"{job_id or 'document'}_{form.form_id}"
        csv_path = self.output_dir / f"{stem}.csv"
        md_path = self.output_dir / f"{stem}_correspondance.md"
        json_path = self.output_dir / f"{stem}_tracabilite.json"

        csv_path.write_text(self.build_csv(form, report), encoding="utf-8")
        md_path.write_text(self.build_crosswalk(form, report), encoding="utf-8")
        json_path.write_text(json.dumps({
            "form_id": form.form_id, "form_source": form.source,
            "job_id": job_id, "mode": "assisted_export",
            "is_real_external_system": False,
            "validation": report.as_dict(),
        }, ensure_ascii=False, indent=2), encoding="utf-8")

        return {"csv": str(csv_path), "crosswalk": str(md_path),
                "traceability": str(json_path),
                "values": len(report.payload())}

    # ─────────────────────────── opérations refusées ───────────────────────────

    def submit(self, form: FormSchema, payload: dict,
               idempotency_key: str = "") -> SubmissionResult:
        raise NotSupportedError(self.connector_id, "submit")

    def get_status(self, reference: str) -> dict:
        raise NotSupportedError(self.connector_id, "get_status")

    def get_acknowledgement(self, reference: str) -> dict:
        raise NotSupportedError(self.connector_id, "get_acknowledgement")
