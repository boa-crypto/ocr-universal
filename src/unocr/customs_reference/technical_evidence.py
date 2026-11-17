"""Pièces textuelles déclarées, versionnées ; ni original authentifié ni expertise."""
import hashlib
import unicodedata
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .models import StrictModel


class DeclarationAttribut(StrictModel):
    critere: Literal["designation", "matiere", "fonction", "usage", "caracteristiques"]
    valeur_declaree: str = Field(min_length=1, max_length=256)
    debut: int = Field(ge=0, le=16384)
    fin: int = Field(ge=1, le=16384)
    citation: str = Field(min_length=1, max_length=4096)

    @field_validator("valeur_declaree")
    @classmethod
    def non_blanc(cls, value):
        if not value.strip():
            raise ValueError("Valeur déclarée vide")
        return value


class PieceTechnique(StrictModel):
    piece_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    nom: str = Field(min_length=1, max_length=128)
    nature: Literal["fiche_technique", "notice", "attestation", "declaration", "autre"]
    criteres_declares: list[Literal["designation", "matiere", "fonction", "usage", "caracteristiques"]] = Field(min_length=1, max_length=5)
    localisateur_declare: str = Field(min_length=1, max_length=256)
    texte: str = Field(min_length=1, max_length=16384)
    declarations_attributs: list[DeclarationAttribut] = Field(default_factory=list, max_length=5)

    @model_validator(mode="after")
    def citations_exactes(self):
        criteres = set()
        for declaration in self.declarations_attributs:
            if (declaration.critere not in self.criteres_declares or declaration.critere in criteres
                    or not 0 <= declaration.debut < declaration.fin <= len(self.texte)
                    or self.texte[declaration.debut:declaration.fin] != declaration.citation):
                raise ValueError("Citation ou critère incohérent avec le texte reçu")
            criteres.add(declaration.critere)
        return self


    @field_validator("nom", "localisateur_declare", "texte")
    @classmethod
    def texte_sur(cls, value, info):
        if not value.strip() or any(unicodedata.category(c) == "Cc" and c not in "\n\r\t" for c in value):
            raise ValueError("Texte vide ou contrôle interdit")
        if info.field_name != "texte" and any(c in value for c in "\n\r\t"):
            raise ValueError("Métadonnée sur une seule ligne requise")
        if info.field_name == "nom" and (value in {".", ".."} or any(c in value for c in "/\\:")):
            raise ValueError("Nom simple attendu, pas un chemin")
        if len(value.encode("utf-8")) > 32768:
            raise ValueError("Pièce limitée à 32768 octets UTF8")
        return value

    @field_validator("criteres_declares")
    @classmethod
    def criteres_uniques(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("Critères répétés")
        return value


def verifier_identifiants(pieces):
    if pieces is not None and len({p.piece_id for p in pieces}) != len(pieces):
        raise ValueError("Identifiants de pièces répétés")
    return pieces


def preparer_pieces(pieces, anciennes, acteur, horodatage):
    if pieces is None:
        return anciennes
    verifier_identifiants(pieces)
    precedentes = {p["piece_id"]: p for p in anciennes}
    resultat = []
    for piece in pieces:
        contenu = piece.model_dump()
        precedente = precedentes.get(piece.piece_id)
        if precedente and all(precedente.get(k) == v for k, v in contenu.items()):
            resultat.append(precedente)
        else:
            brut = piece.texte.encode("utf-8")
            resultat.append(contenu | {"format": "texte_utf8", "sha256": hashlib.sha256(brut).hexdigest(),
                                      "octets": len(brut), "fourni_par": acteur,
                                      "horodatage": horodatage, "verification": "non_verifiee"})
    return resultat


def verifier_pieces(pieces):
    if not isinstance(pieces, list) or len(pieces) > 5:
        raise ValueError("Liste de pièces incompatible")
    modeles = []
    for piece in pieces:
        if not isinstance(piece, dict) or set(piece) != set(PieceTechnique.model_fields) | {
                "format", "sha256", "octets", "fourni_par", "horodatage", "verification"}:
            raise ValueError("Pièce stockée incompatible")
        modele = PieceTechnique.model_validate({k: piece[k] for k in PieceTechnique.model_fields})
        brut = modele.texte.encode("utf-8")
        instant = datetime.fromisoformat(piece["horodatage"])
        if (piece["sha256"] != hashlib.sha256(brut).hexdigest() or type(piece["octets"]) is not int
                or piece["octets"] != len(brut) or piece["format"] != "texte_utf8"
                or piece["verification"] != "non_verifiee" or not isinstance(piece["fourni_par"], str)
                or not piece["fourni_par"].strip() or instant.utcoffset() is None):
            raise ValueError("Intégrité de pièce incompatible")
        modeles.append(modele)
    verifier_identifiants(modeles)
