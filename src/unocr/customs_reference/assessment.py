"""Dossiers de proposition documentaire, jamais décisions fiscales ou publication."""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator

from .models import SourceRef, StrictModel
from .tariff_candidates import rechercher_pistes_tarifaires
from .tariff_criteria import CRITERES


class ProduitDeclare(StrictModel):
    designation: str = Field(min_length=1, max_length=256)
    matiere: str | None = Field(None, min_length=1, max_length=256)
    fonction: str | None = Field(None, min_length=1, max_length=256)
    usage: str | None = Field(None, min_length=1, max_length=256)
    caracteristiques: str | None = Field(None, min_length=1, max_length=256)

    @field_validator(*CRITERES)
    @classmethod
    def texte(cls, value):
        if value is not None and not value.strip():
            raise ValueError("Caractéristique blanche")
        return value


class CreationDossier(StrictModel):
    dossier_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
    produit: ProduitDeclare


class RevisionDossier(StrictModel):
    version_attendue: int = Field(ge=1, le=100)
    statut: Literal["en_revue", "a_completer", "proposition_humaine", "rejetee"]
    justification: str = Field(min_length=10, max_length=4000)
    produit: ProduitDeclare | None = None
    code_propose: str | None = Field(None, pattern=r"^[0-9]{10}$")
    raisonnement_rgi: str | None = Field(None, min_length=10, max_length=4000)
    notes_exclusions: str | None = Field(None, min_length=10, max_length=4000)
    references: list[SourceRef] = Field(default_factory=list, max_length=20)

    @field_validator("justification", "raisonnement_rgi", "notes_exclusions")
    @classmethod
    def texte(cls, value):
        if value is not None and len(value.strip()) < 10:
            raise ValueError("Motivation explicite requise")
        return value


TRANSITIONS = {
    "brouillon": {"en_revue", "a_completer", "rejetee"},
    "en_revue": {"en_revue", "a_completer", "proposition_humaine", "rejetee"},
    "a_completer": {"a_completer", "en_revue", "rejetee"},
    "proposition_humaine": {"en_revue", "rejetee"},
    "rejetee": {"en_revue"},
}


class DossierRefuse(ValueError):
    pass


class DossierInconnu(LookupError):
    pass


class RevisionDossierConflict(DossierRefuse):
    pass


def preparer_diagnostic(repertoire: Path, produit: ProduitDeclare) -> dict:
    recherche = rechercher_pistes_tarifaires(repertoire, **produit.model_dump(), limite=20,
                                             match_mode="mots_entiers")
    manquants = [k for k in CRITERES if getattr(produit, k) is None]
    return {"produit_declare": produit.model_dump(), "recherche": recherche,
            "informations_non_renseignees": manquants,
            "questions_a_documenter": [{"critere": k, "question": f"Documenter {k} du produit"}
                                        for k in manquants],
            "abstention_documentaire": recherche["total_correspondances"] == 0,
            "autres_candidats_non_affiches": recherche["total_correspondances"] > len(recherche["resultats"]),
            "classement_ia_effectue": False, "publication_active": False,
            "validation_juridique": "non_validee", "taux_calcules": False}


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


class MagasinDossiers:
    """État et versions/auteurs atomiques SQLite ; pas journal signé ou WORM."""
    def __init__(self, path: Path):
        self.path = path

    def _connect(self):
        if self.path.is_symlink():
            raise DossierRefuse("Stockage symbolique refusé")
        conn = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        try:
            conn.execute("CREATE TABLE IF NOT EXISTS dossiers (id TEXT PRIMARY KEY, lot TEXT NOT NULL, "
                         "manifest TEXT NOT NULL, version INTEGER NOT NULL, contenu TEXT NOT NULL)")
            conn.execute("CREATE TABLE IF NOT EXISTS versions (id TEXT NOT NULL, version INTEGER NOT NULL, "
                         "contenu TEXT NOT NULL, PRIMARY KEY(id,version))")
        except Exception:
            conn.close()
            raise
        return conn

    @staticmethod
    def _verifier(contenu, evenement):
        document = json.loads(contenu)
        trace = json.loads(evenement)
        if (trace["sha256_contenu"] != hashlib.sha256(contenu.encode()).hexdigest()
                or _json(trace["dossier"]) != contenu
                or document["publication_active"] is not False
                or document["validation_juridique"] != "non_validee"):
            raise DossierRefuse("État et trace du dossier incohérents")
        return document, trace["sha256_contenu"]

    def lire(self, dossier_id, lot_id, manifest, historique=False):
        if not self.path.exists():
            raise DossierInconnu(dossier_id)
        conn = self._connect()
        try:
            conn.execute("BEGIN")
            row = conn.execute("SELECT lot,manifest,version,contenu FROM dossiers WHERE id=?", (dossier_id,)).fetchone()
            if row is None or row[0] != lot_id:
                raise DossierInconnu(dossier_id)
            if row[1] != manifest:
                raise RevisionDossierConflict("Source du dossier différente")
            event = conn.execute("SELECT contenu FROM versions WHERE id=? AND version=?", (dossier_id,row[2])).fetchone()
            if event is None:
                raise DossierRefuse("Trace de version absente")
            document, _ = self._verifier(row[3],event[0])
            if (document["id"], document["lot_id"], document["manifest_sha256"], document["version"]) != (dossier_id,lot_id,manifest,row[2]):
                raise DossierRefuse("Identité de dossier incohérente")
            if historique:
                versions = []
                for version, contenu in conn.execute("SELECT version,contenu FROM versions WHERE id=? ORDER BY version", (dossier_id,)):
                    trace = json.loads(contenu)
                    d, empreinte = self._verifier(_json(trace["dossier"]), contenu)
                    if (d["id"],d["lot_id"],d["manifest_sha256"],d["version"]) != (dossier_id,lot_id,manifest,version):
                        raise DossierRefuse("Historique incohérent")
                    versions.append({k:d[k] for k in ("version","statut","acteur","horodatage","decision_declaree")}
                                    | {"produit_declare":d["diagnostic"]["produit_declare"], "sha256_contenu":empreinte})
                if [v["version"] for v in versions] != list(range(1,row[2]+1)):
                    raise DossierRefuse("Versions manquantes")
                document["historique"] = versions
            return document
        finally:
            conn.close()

    def enregistrer(self, dossier_id, lot_id, manifest, diagnostic, acteur, revision=None):
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT lot,manifest,version,contenu FROM dossiers WHERE id=?", (dossier_id,)).fetchone()
            if revision is None:
                if row is not None:
                    raise RevisionDossierConflict("Identifiant déjà utilisé")
                version, statut = 1, "brouillon"
            else:
                if row is None or row[0] != lot_id:
                    raise DossierInconnu(dossier_id)
                if row[1] != manifest or row[2] != revision.version_attendue:
                    raise RevisionDossierConflict("Révision ou source modifiée")
                trace = conn.execute("SELECT contenu FROM versions WHERE id=? AND version=?", (dossier_id,row[2])).fetchone()
                if trace is None:
                    raise DossierRefuse("Trace de version absente")
                precedent, _ = self._verifier(row[3], trace[0])
                if revision.statut not in TRANSITIONS[precedent["statut"]]:
                    raise DossierRefuse("Transition de revue interdite")
                if precedent["statut"] in {"proposition_humaine", "rejetee"} and revision.produit is not None:
                    raise DossierRefuse("Rouvrir avant modification du produit")
                if revision.statut == "proposition_humaine":
                    candidats = diagnostic["recherche"]["resultats"]
                    retenus = [c["ligne"] for c in candidats if c["ligne"]["code_tarifaire_10"] == revision.code_propose]
                    if (diagnostic["informations_non_renseignees"] or not retenus
                            or not revision.raisonnement_rgi or not revision.notes_exclusions
                            or retenus[0]["reference"] not in [r.model_dump() for r in revision.references]):
                        raise DossierRefuse("Proposition incomplète ou référence de candidat absente")
                elif any((revision.code_propose, revision.raisonnement_rgi, revision.notes_exclusions, revision.references)):
                    raise DossierRefuse("Code/argumentation réservés à une proposition humaine")
                version, statut = row[2]+1, revision.statut
                if version > 100:
                    raise DossierRefuse("Limite de versions atteinte")
            document = {"id": dossier_id, "lot_id": lot_id, "manifest_sha256": manifest,
                        "version": version, "statut": statut, "acteur": acteur,
                        "horodatage": datetime.now(timezone.utc).isoformat(),
                        "diagnostic": diagnostic,
                        "decision_declaree": revision.model_dump(exclude={"produit"}) if revision else None,
                        "publication_active": False, "validation_juridique": "non_validee",
                        "archive": diagnostic["recherche"]["archive"]}
            contenu = _json(document)
            if len(contenu.encode()) > 512*1024:
                raise DossierRefuse("Dossier trop volumineux")
            evenement = _json({"dossier": document, "sha256_contenu": hashlib.sha256(contenu.encode()).hexdigest()})
            conn.execute("INSERT INTO versions VALUES (?,?,?)", (dossier_id, version, evenement))
            conn.execute("INSERT INTO dossiers VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
                         "version=excluded.version,contenu=excluded.contenu", (dossier_id,lot_id,manifest,version,contenu))
            conn.commit()
            return document
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
