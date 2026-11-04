"""Contrats de préparation, pas attestations de validité juridique.

Une URL sur domaine officiel et une empreinte identifient une source déclarée,
mais ne prouvent ni son authenticité, ni sa complétude, ni son applicabilité.
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SourceDocument(StrictModel):
    id: str = Field(min_length=1)
    titre: str = Field(min_length=1)
    url: str
    organisme: str = Field(min_length=1)
    version_source: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    format: Literal["json", "csv", "xlsx", "xls", "pdf", "xml", "zip"]
    date_publication: date | None = None
    verification: Literal["non_verifiee"] = "non_verifiee"

    @field_validator("url")
    @classmethod
    def domaine_officiel(cls, value):
        parsed = urlsplit(value)
        domaines = {"joradp.dz", "douane.gov.dz", "commerce.gov.dz", "wcoomd.org", "wto.org", "un.org"}
        host = parsed.hostname or ""
        if (parsed.scheme != "https" or parsed.username or parsed.password
                or parsed.port not in {None, 443}
                or not any(host == d or host.endswith("." + d) for d in domaines)):
            raise ValueError("URL HTTPS sur domaine officiel attendu ; cela ne vaut pas authentification")
        return value


class SourceRef(StrictModel):
    source_id: str = Field(min_length=1)
    localisateur: str = Field(min_length=1, description="Page, article, feuille/cellules ou ligne source")


class Periode(StrictModel):
    date_entree_vigueur: date | None = None
    date_fin_validite: date | None = None

    @model_validator(mode="after")
    def ordre_dates(self):
        if self.date_entree_vigueur and self.date_fin_validite and self.date_fin_validite < self.date_entree_vigueur:
            raise ValueError("Fin de validité antérieure à l'entrée en vigueur")
        return self


class Section(StrictModel):
    id: str = Field(min_length=1)
    designation: str = Field(min_length=1)
    reference: SourceRef


class Chapitre(StrictModel):
    code: str = Field(pattern=r"^[0-9]{2}$")
    section_id: str
    designation: str = Field(min_length=1)
    reference: SourceRef


class Position(StrictModel):
    code: str = Field(pattern=r"^[0-9]{4}$")
    chapitre: str = Field(pattern=r"^[0-9]{2}$")
    designation: str = Field(min_length=1)
    reference: SourceRef


class SousPosition(StrictModel):
    code: str = Field(pattern=r"^[0-9]{6}$")
    position: str = Field(pattern=r"^[0-9]{4}$")
    designation: str = Field(min_length=1)
    reference: SourceRef


class LigneTarifaire(Periode):
    id: str = Field(min_length=1)
    code_tarifaire_10: str = Field(pattern=r"^[0-9]{10}$")
    code_sh_6: str = Field(pattern=r"^[0-9]{6}$")
    chapitre: str = Field(pattern=r"^[0-9]{2}$")
    position: str = Field(pattern=r"^[0-9]{4}$")
    sous_position: str = Field(pattern=r"^[0-9]{6}$")
    section_id: str
    designation_officielle_fr: str | None = None
    designation_officielle_ar: str | None = None
    unite_statistique: str | None = None
    unite_supplementaire: str | None = None
    # Inconnus, et non zéro. Les mesures documentées sont séparées du libellé.
    taux_droits_douane: None = None
    taux_tva: None = None
    autres_taxes: None = None
    mesures_reglementaires: None = None
    restrictions: None = None
    autorisations_requises: None = None
    pays_origine_concerne_si_applicable: None = None
    regime_douanier_applicable: None = None
    statut: Literal["a_verifier"] = "a_verifier"
    reference: SourceRef
    date_validation: None = None

    @model_validator(mode="after")
    def coherente(self):
        code = self.code_tarifaire_10
        if (self.chapitre != code[:2] or self.position != code[:4]
                or self.code_sh_6 != code[:6] or self.sous_position != self.code_sh_6):
            raise ValueError("Préfixes hiérarchiques incohérents")
        if not any(t and t.strip() for t in (self.designation_officielle_fr, self.designation_officielle_ar)):
            raise ValueError("Désignation française ou arabe obligatoire")
        for unite in (self.unite_statistique, self.unite_supplementaire):
            if unite is not None and not unite.strip():
                raise ValueError("Unité vide : utiliser null si inconnue")
        return self


class Mesure(Periode):
    id: str = Field(min_length=1)
    code_tarifaire_10: str = Field(pattern=r"^[0-9]{10}$")
    type_mesure: Literal["droit", "tva", "autre_taxe", "restriction", "autorisation", "regime"]
    description: str = Field(min_length=1)
    taux: Decimal | None = Field(default=None, ge=0)
    unite_taux: Literal["pourcent"] | None = None
    reference: SourceRef
    statut: Literal["a_verifier"] = "a_verifier"

    @model_validator(mode="after")
    def taux_documente(self):
        if (self.taux is None) != (self.unite_taux is None):
            raise ValueError("Taux et unité doivent être renseignés ensemble")
        if self.taux is not None and self.type_mesure not in {"droit", "tva", "autre_taxe"}:
            raise ValueError("Taux réservé aux mesures fiscales")
        return self


class TariffBatch(StrictModel):
    schema_version: Literal["1"] = "1"
    source: SourceDocument
    sections: list[Section]
    chapitres: list[Chapitre]
    positions: list[Position]
    sous_positions: list[SousPosition]
    lignes: list[LigneTarifaire] = Field(min_length=1)
    mesures: list[Mesure] = Field(default_factory=list)
    statut: Literal["quarantaine"] = "quarantaine"

    @model_validator(mode="after")
    def integrite(self):
        def index(values, key):
            result = {}
            for item in values:
                cle = getattr(item, key)
                if cle in result:
                    raise ValueError("Doublon : " + cle)
                result[cle] = item
            return result
        sections = index(self.sections, "id")
        chapitres = index(self.chapitres, "code")
        positions = index(self.positions, "code")
        sh6 = index(self.sous_positions, "code")
        codes = index(self.lignes, "code_tarifaire_10")
        index(self.lignes, "id")
        index(self.mesures, "id")
        for item in [*self.sections, *self.chapitres, *self.positions, *self.sous_positions, *self.lignes, *self.mesures]:
            if item.reference.source_id != self.source.id:
                raise ValueError("Source référencée absente du lot ; utiliser un lot distinct pour une autre source")
        for c in chapitres.values():
            if c.section_id not in sections:
                raise ValueError("Section parente absente")
        for p in positions.values():
            if p.chapitre not in chapitres or p.code[:2] != p.chapitre:
                raise ValueError("Chapitre parent absent ou incohérent")
        for s in sh6.values():
            if s.position not in positions or s.code[:4] != s.position:
                raise ValueError("Position parente absente ou incohérente")
        for ligne in self.lignes:
            if ligne.code_sh_6 not in sh6 or ligne.chapitre not in chapitres:
                raise ValueError("Parent SH6/chapitre absent")
            if ligne.section_id != chapitres[ligne.chapitre].section_id:
                raise ValueError("Section incohérente")
        for m in self.mesures:
            if m.code_tarifaire_10 not in codes:
                raise ValueError("Mesure liée à un code absent")
        return self


NIVEAUX = ["texte_legislatif", "livre", "titre", "chapitre", "section", "sous_section", "article", "paragraphe", "alinea", "annexe"]


class NiveauJuridique(StrictModel):
    niveau: Literal["texte_legislatif", "livre", "titre", "chapitre", "section", "sous_section", "article", "paragraphe", "alinea", "annexe"]
    identifiant: str
    intitule: str | None = None


class ArticleVersion(Periode):
    id: str = Field(min_length=1)
    numero_article: str = Field(min_length=1)
    intitule: str | None = None
    hierarchie: list[NiveauJuridique]
    nature_version: Literal["originale", "modificative", "consolidee_provisoire"]
    texte_integral: str = Field(min_length=1)
    texte_francais: str | None = None
    texte_arabe: str | None = None
    texte_origine: str | None = None
    texte_modificatif: str | None = None
    date_publication: date | None = None
    date_abrogation: date | None = None
    reference_jo: str | None = None
    numero_jo: str | None = None
    reference: SourceRef
    version_juridique: str = Field(min_length=1)
    statut_juridique_declare: Literal["applicable", "modifie", "abroge", "suspendu", "a_verifier"] = "a_verifier"
    validation_juridique: Literal["non_validee"] = "non_validee"
    articles_lies: list[str] = Field(default_factory=list)
    historique_modifications: list[SourceRef] = Field(default_factory=list)
    notes_explicatives_non_officielles: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def separation(self):
        niveaux = [NIVEAUX.index(n.niveau) for n in self.hierarchie]
        if niveaux != sorted(set(niveaux)):
            raise ValueError("Hiérarchie juridique désordonnée ou dupliquée")
        if self.nature_version == "originale" and self.texte_modificatif is not None:
            raise ValueError("Ne pas fusionner texte original et disposition modificative")
        if self.date_abrogation and self.date_entree_vigueur and self.date_abrogation < self.date_entree_vigueur:
            raise ValueError("Abrogation antérieure à la prise d'effet")
        return self


class RelationDocumentee(StrictModel):
    id: str
    origine_id: str
    cible_id: str
    type_relation: str
    justification: str = Field(min_length=1)
    reference: SourceRef
    validation_juridique: Literal["non_validee"] = "non_validee"


# Aucune substitution ou zfill sur des codes réglementaires.
def code10_strict(value: str) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9]{10}", value) is not None
