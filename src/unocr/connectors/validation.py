"""Validation avant transmission (phase 8).

Produit l'écran de contrôle : ce qui part, ce qui manque, ce qui est douteux,
et d'où vient chaque valeur. **Aucune transmission ne doit être possible sans
que ce rapport soit passé en paramètre** — c'est le verrou qui empêche un envoi
de valeur non vérifiée.

Niveaux de risque (configurables) :
- `low`     : export assisté, conséquence limitée
- `medium`  : dossier administratif réversible
- `high`    : déclaration à effet juridique ou fiscal

Le niveau `high` exige une confirmation explicite **et** l'absence d'erreur
bloquante. Une valeur issue d'une similarité (`suggested`) non validée bloque
toujours l'envoi vers un système réel.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum

from ..logging_setup import get_logger
from .contract import FormSchema
from .mapping import MappedValue

log = get_logger("connectors.validation")


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# niveaux exigeant une confirmation explicite
CONFIRMATION_REQUIRED = {RiskLevel.MEDIUM, RiskLevel.HIGH}


@dataclass
class ValidationIssue:
    field: str
    kind: str                  # missing_required | bad_format | unknown_field |
                               # ambiguous | contradiction | unvalidated_suggestion
    severity: str              # error | warning | info
    message: str

    def as_dict(self) -> dict:
        return {"field": self.field, "kind": self.kind,
                "severity": self.severity, "message": self.message}


@dataclass
class ValidationReport:
    """Rapport de contrôle affiché avant tout envoi."""
    form_id: str
    risk: RiskLevel
    issues: list[ValidationIssue] = field(default_factory=list)
    values: dict[str, MappedValue] = field(default_factory=dict)
    confirmed: bool = False               # confirmation humaine explicite
    confirmed_by: str = ""
    confirmed_at: float = 0.0
    created_at: float = field(default_factory=time.time)

    # ── agrégats ──
    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def blocking(self) -> bool:
        return bool(self.errors)

    def can_transmit(self) -> tuple[bool, str]:
        """Verdict. Renvoie (autorisé, raison si refus)."""
        if self.blocking:
            return False, (f"{len(self.errors)} erreur(s) bloquante(s) : "
                           + "; ".join(e.message for e in self.errors[:3]))
        if self.risk in CONFIRMATION_REQUIRED and not self.confirmed:
            return False, (f"confirmation humaine exigée (niveau de risque "
                           f"« {self.risk.value} »)")
        return True, ""

    def confirm(self, by: str = "") -> None:
        self.confirmed = True
        self.confirmed_by = by
        self.confirmed_at = time.time()

    def payload(self) -> dict:
        """Données réellement envoyées : seules les valeurs non douteuses."""
        return {k: v.value for k, v in self.values.items()
                if v.value is not None and v.confidence != "suggested"}

    def traceability(self) -> list[dict]:
        """Traçabilité champ par champ : source, page, valeur OCR, règle."""
        out = []
        for name, v in self.values.items():
            out.append({
                "target_field": name,
                "value": v.value,
                "confidence": v.confidence,
                "source_field": v.source_field,
                "source_page": v.source_page,
                "ocr_raw": v.ocr_raw,
                "normalized": v.normalized,
                "transform": v.transform,
                "warning": v.warning,
            })
        return out

    def as_dict(self) -> dict:
        ok, why = self.can_transmit()
        return {
            "form_id": self.form_id, "risk": self.risk.value,
            "issues": [i.as_dict() for i in self.issues],
            "errors": len(self.errors), "warnings": len(self.warnings),
            "can_transmit": ok, "reason": why,
            "confirmed": self.confirmed, "confirmed_by": self.confirmed_by,
            "confirmed_at": self.confirmed_at,
            "payload": self.payload(),
            "traceability": self.traceability(),
            "created_at": self.created_at,
        }


# ─────────────────────────── le validateur ───────────────────────────

_TYPE_CHECKS = {
    "date": lambda v: _looks_iso_date(v),
    "amount": lambda v: _looks_decimal(v),
    "number": lambda v: _looks_decimal(v),
    "currency": lambda v: _looks_decimal(v),
    "checkbox": lambda v: v.lower() in ("true", "false", "1", "0", "oui", "non"),
    "identifier": lambda v: bool(v.strip()),
    "list": lambda v: bool(v.strip()),
    "reference": lambda v: bool(v.strip()),
    "text": lambda v: True,
    "table": lambda v: True,
}


def _looks_iso_date(v: str) -> bool:
    import re
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", v or ""))


def _looks_decimal(v: str) -> bool:
    import re
    return bool(re.fullmatch(r"-?\d+(\.\d+)?", v or ""))


class Validator:
    """Contrôle un mapping par rapport au schéma du formulaire cible."""

    def __init__(self, risk: RiskLevel = RiskLevel.MEDIUM):
        self.risk = risk

    def validate(self, form: FormSchema,
                 values: dict[str, MappedValue]) -> ValidationReport:
        rep = ValidationReport(form_id=form.form_id, risk=self.risk, values=values)
        schema = {f.external_name: f for f in form.fields}

        for name, f in schema.items():
            mv = values.get(name)
            if mv is None or mv.value is None:
                if f.required:
                    rep.issues.append(ValidationIssue(
                        name, "missing_required", "error",
                        f"champ obligatoire « {f.label or name} » sans valeur"))
                continue

            # une suggestion non validée ne doit jamais partir vers un système réel
            if mv.confidence == "suggested":
                rep.issues.append(ValidationIssue(
                    name, "unvalidated_suggestion", "error",
                    "correspondance suggérée non validée — à confirmer manuellement"))
                continue

            # format
            check = _TYPE_CHECKS.get(f.field_type)
            if check and not check(mv.value):
                rep.issues.append(ValidationIssue(
                    name, "bad_format", "error",
                    f"« {mv.value} » n'est pas un {f.field_type} valide"
                    + (f" ({f.format_hint})" if f.format_hint else "")))
                continue

            # longueur
            if f.max_length and len(mv.value) > f.max_length:
                rep.issues.append(ValidationIssue(
                    name, "bad_format", "error",
                    f"{len(mv.value)} caractères > maximum {f.max_length}"))

            # liste de valeurs
            if f.allowed_values and mv.value not in f.allowed_values:
                rep.issues.append(ValidationIssue(
                    name, "bad_format", "error",
                    f"« {mv.value} » n'est pas dans les valeurs autorisées"))

            # avertissements de transformation
            if mv.warning:
                rep.issues.append(ValidationIssue(
                    name, "ambiguous", "warning", mv.warning))

        # champs envoyés qui n'existent pas dans le schéma cible
        for name in values:
            if name not in schema:
                rep.issues.append(ValidationIssue(
                    name, "unknown_field", "warning",
                    "champ absent du schéma du formulaire cible — non envoyé"))
        return rep
