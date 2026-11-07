"""Mesures autonomes en quarantaine, sans nomenclature ou fiscalité applicable."""
import re
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .models import Mesure, SourceDocument, StrictModel


class SourceMesuresDocumentaires(SourceDocument):
    format: Literal["json", "csv", "xlsx"]


# Alias conservé pour les utilisateurs Python du premier contrat (lot 36).
SourceMesuresJSON = SourceMesuresDocumentaires


class MetadataMesuresAutonomes(StrictModel):
    schema_version: Literal["1"] = "1"
    source: SourceMesuresDocumentaires
    statut: Literal["quarantaine"] = "quarantaine"
    validation_juridique: Literal["non_validee"] = "non_validee"
    publication_active: Literal[False] = False

    @field_validator("publication_active", mode="before")
    @classmethod
    def aucune_publication(cls, valeur):
        if valeur is not False:
            raise ValueError("Publication strictement false requise")
        return valeur

    @model_validator(mode="after")
    def source_non_blanche(self):
        if any(not getattr(self.source, c).strip() for c in ("id", "titre", "organisme", "version_source")):
            raise ValueError("Métadonnées de source non blanches requises")
        return self


class MesuresAutonomesBatch(MetadataMesuresAutonomes):
    mesures: list[Mesure] = Field(default_factory=list, max_length=100_000)

    @model_validator(mode="after")
    def integrite_mesures(self):
        ids = set()
        for m in self.mesures:
            if not m.id.strip() or not m.description.strip() or not m.reference.localisateur.strip():
                raise ValueError("ID, description et localisateur de mesure non blancs requis")
            if m.id in ids:
                raise ValueError("ID de mesure dupliqué dans ce lot")
            ids.add(m.id)
            if m.reference.source_id != self.source.id:
                raise ValueError("Référence de mesure étrangère à la source autonome")
            if re.fullmatch(r"[0-9]{10}", m.code_tarifaire_10) is None:
                raise ValueError("Code déclaré exact de dix chiffres ASCII requis")
        return self


class ConfigurationMesuresAutonomes(MetadataMesuresAutonomes):
    colonnes: dict[str, str] | None = None
    delimiteur: str = ";"
    feuille: str | None = None
    ligne_entete: int = Field(default=1, strict=True, ge=1, le=50)
