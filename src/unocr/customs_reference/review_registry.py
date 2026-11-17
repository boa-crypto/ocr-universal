"""Allowlist locale de revue, jamais registre de publication juridique."""
import json
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from .importer import _json
from .models import StrictModel

MAX_REGISTRE = 1024 * 1024
IDENTIFIANT = r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$"


class LotRevue(StrictModel):
    id: str = Field(pattern=IDENTIFIANT)
    type_lot: Literal["tarif", "code", "mesures"]
    dossier: str = Field(pattern=IDENTIFIANT)
    manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    index_pdf_sha256: str | None = Field(None, pattern=r"^[a-f0-9]{64}$")


class RegistreRevue(StrictModel):
    schema_version: Literal["1"] = "1"
    reviseurs: list[str] = Field(max_length=64)
    lots: list[LotRevue] = Field(max_length=64)

    @model_validator(mode="after")
    def unicite(self):
        if (len(set(self.reviseurs)) != len(self.reviseurs)
                or any(not nom.strip() or len(nom) > 128 for nom in self.reviseurs)):
            raise ValueError("Réviseurs dupliqués ou noms invalides")
        if len({lot.id for lot in self.lots}) != len(self.lots) or len({lot.dossier for lot in self.lots}) != len(self.lots):
            raise ValueError("Identifiant/dossier de revue dupliqué")
        return self


class RegistreRevueIndisponible(ValueError):
    """Configuration absente/incohérente : ne pas découvrir de dossiers librement."""


def charger_registre(path: Path) -> RegistreRevue:
    try:
        if path.parent.is_symlink() or not path.parent.is_dir() or path.is_symlink() or not path.is_file():
            raise ValueError("Registre non régulier")
        with path.open("rb") as fichier:
            original = fichier.read(MAX_REGISTRE + 1)
        if len(original) > MAX_REGISTRE:
            raise ValueError("Registre trop volumineux")
        return RegistreRevue.model_validate_json(json.dumps(_json(original), ensure_ascii=False, allow_nan=False))
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        raise RegistreRevueIndisponible("Registre de revue absent ou invalide") from exc
