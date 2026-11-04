"""Routes de gestion des frais, finances et facturation (Module 10)."""

from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import tempfile
import uuid
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import List, Optional
from urllib.parse import quote

from fastapi import APIRouter, Body, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, ValidationError

from ..business_links import exiger_dossier
from ..business_store import BusinessStore
from ..config import get_config
from ..logging_setup import audit, get_logger
from ..models import Facture, Frais, Justificatif, new_id

log = get_logger("frais")

router = APIRouter(prefix="/api/frais", tags=["frais"])

cfg = get_config()


# ───────────────────────────────────────────────────────────────
# Frais, factures et métadonnées des justificatifs persistants
# ───────────────────────────────────────────────────────────────

MAX_JUSTIFICATIF = 20 * 1024 * 1024


def _get_justificatif_store(request: Request) -> BusinessStore[Justificatif]:
    return BusinessStore(cfg.data_dir / "metier.sqlite3", "justificatif", Justificatif)


def _get_frais_store(request: Request) -> BusinessStore[Frais]:
    return BusinessStore(cfg.data_dir / "metier.sqlite3", "frais", Frais)


def _get_facture_store(request: Request) -> BusinessStore[Facture]:
    return BusinessStore(cfg.data_dir / "metier.sqlite3", "facture", Facture)


# ───────────────────────────────────────────────────────────────
# Schémas Pydantic - Frais
# ───────────────────────────────────────────────────────────────

class FraisCreate(BaseModel):
    dossier_id: str
    categorie: str = ""
    fournisseur: str = ""
    montant: float = 0.0
    devise: str = "EUR"
    date: str = ""
    reference_facture: str = ""
    justificatif: str = ""
    statut_paiement: str = "en_attente"
    commentaire: str = ""
    avance_client: bool = False


class FraisUpdate(BaseModel):
    dossier_id: Optional[str] = None
    categorie: Optional[str] = None
    fournisseur: Optional[str] = None
    montant: Optional[float] = None
    devise: Optional[str] = None
    date: Optional[str] = None
    reference_facture: Optional[str] = None
    justificatif: Optional[str] = None
    statut_paiement: Optional[str] = None
    commentaire: Optional[str] = None
    avance_client: Optional[bool] = None


# ───────────────────────────────────────────────────────────────
# Schémas Pydantic - Facture
# ───────────────────────────────────────────────────────────────

class FactureCreate(BaseModel):
    dossier_id: str
    type_facture: str = ""  # emisee, recue
    numero_facture: str = ""
    date_facture: Optional[str] = None
    montant_ht: float = 0.0
    montant_tva: float = 0.0
    montant_ttc: float = 0.0
    devise: str = "EUR"
    statut_paiement: str = "en_attente"
    client_id: str = ""
    fournisseur_id: str = ""
    documents_joints: List[str] = []
    notes: str = ""


class FactureUpdate(BaseModel):
    dossier_id: Optional[str] = None
    type_facture: Optional[str] = None
    numero_facture: Optional[str] = None
    date_facture: Optional[str] = None
    montant_ht: Optional[float] = None
    montant_tva: Optional[float] = None
    montant_ttc: Optional[float] = None
    devise: Optional[str] = None
    statut_paiement: Optional[str] = None
    client_id: Optional[str] = None
    fournisseur_id: Optional[str] = None
    documents_joints: Optional[List[str]] = None
    notes: Optional[str] = None


# ───────────────────────────────────────────────────────────────
# Routes Frais
# ───────────────────────────────────────────────────────────────

@router.post("")
def create_frais(
    request: Request,
    frais: FraisCreate,
) -> dict:
    """Créer un nouveau frais."""
    store = _get_frais_store(request)
    frais_obj = Frais(
        id=new_id("frais_"),
        dossier_id=frais.dossier_id,
        categorie=frais.categorie,
        fournisseur=frais.fournisseur,
        montant=frais.montant,
        devise=frais.devise,
        date=frais.date,
        reference_facture=frais.reference_facture,
        justificatif=frais.justificatif,
        statut_paiement=frais.statut_paiement,
        commentaire=frais.commentaire,
        avance_client=frais.avance_client,
    )
    with store.transaction() as transaction:
        exiger_dossier(cfg, frais_obj.dossier_id)
        transaction[frais_obj.id] = frais_obj
    audit(cfg.log_dir, "frais_cree", dossier=frais.dossier_id, montant=frais.montant)
    return frais_obj.model_dump()


@router.get("")
def list_frais(
    request: Request,
    dossier_id: Optional[str] = None,
) -> list[dict]:
    """Lister tous les frais, optionnellement filtrés par dossier."""
    store = _get_frais_store(request)
    frais_list = list(store.values())
    if dossier_id:
        frais_list = [f for f in frais_list if f.dossier_id == dossier_id]
    return [f.model_dump() for f in frais_list]


@router.get("/facture")
def list_factures(
    request: Request,
    dossier_id: Optional[str] = None,
) -> list[dict]:
    """Lister toutes les factures."""
    store = _get_facture_store(request)
    factures = list(store.values())
    if dossier_id:
        factures = [f for f in factures if f.dossier_id == dossier_id]
    return [f.model_dump() for f in factures]


@router.get("/{frais_id}")
def get_frais(
    frais_id: str,
    request: Request,
) -> dict:
    """Obtenir un frais spécifique."""
    store = _get_frais_store(request)
    frais = store.get(frais_id)
    if not frais:
        raise HTTPException(404, "Frais introuvable")
    return frais.model_dump()


@router.put("/{frais_id}")
def update_frais(
    frais_id: str,
    request: Request,
    frais_update: FraisUpdate,
) -> dict:
    """Mettre à jour un frais."""
    store = _get_frais_store(request)
    with store.transaction() as transaction:
        frais = transaction.get(frais_id)
        if not frais:
            raise HTTPException(404, "Frais introuvable")
        update_data = frais_update.model_dump(exclude_unset=True)
        try:
            frais = Frais.model_validate({**frais.model_dump(), **update_data})
        except ValidationError as exc:
            raise HTTPException(422, exc.errors(include_context=False)) from exc
        exiger_dossier(cfg, frais.dossier_id)
        transaction[frais_id] = frais

    audit(cfg.log_dir, "frais_modifie", cible=frais_id)
    return frais.model_dump()


@router.delete("/{frais_id}")
def delete_frais(
    frais_id: str,
    request: Request,
) -> dict:
    """Supprimer un frais."""
    store = _get_frais_store(request)
    with store.transaction() as transaction:
        frais = transaction.get(frais_id)
        if frais is None:
            raise HTTPException(404, "Frais introuvable")
        if frais.justificatifs or any(j.frais_id == frais_id for j in
                transaction.related("justificatif", Justificatif).values()):
            raise HTTPException(409, "Ce frais possède des justificatifs : suppression refusée")
        del transaction[frais_id]
    audit(cfg.log_dir, "frais_supprime", cible=frais_id)
    return {"deleted": True, "id": frais_id}


# ───────────────────────────────────────────────────────────────
# Routes Factures
# ───────────────────────────────────────────────────────────────

@router.post("/facture")
def create_facture(
    request: Request,
    facture: FactureCreate,
) -> dict:
    """Créer une nouvelle facture."""
    store = _get_facture_store(request)
    facture_obj = Facture(
        id=new_id("fac_"),
        dossier_id=facture.dossier_id,
        type_facture=facture.type_facture,
        numero_facture=facture.numero_facture,
        date_facture=facture.date_facture,
        montant_ht=facture.montant_ht,
        montant_tva=facture.montant_tva,
        montant_ttc=facture.montant_ttc,
        devise=facture.devise,
        statut_paiement=facture.statut_paiement,
        client_id=facture.client_id,
        fournisseur_id=facture.fournisseur_id,
        documents_joints=facture.documents_joints,
        notes=facture.notes,
    )
    with store.transaction() as transaction:
        exiger_dossier(cfg, facture_obj.dossier_id)
        transaction[facture_obj.id] = facture_obj
    audit(cfg.log_dir, "facture_creee", dossier=facture.dossier_id, numero=facture.numero_facture)
    return facture_obj.model_dump()


@router.get("/facture/{facture_id}")
def get_facture(
    facture_id: str,
    request: Request,
) -> dict:
    """Obtenir une facture spécifique."""
    store = _get_facture_store(request)
    facture = store.get(facture_id)
    if not facture:
        raise HTTPException(404, "Facture introuvable")
    return facture.model_dump()


@router.put("/facture/{facture_id}")
def update_facture(
    facture_id: str,
    request: Request,
    facture_update: FactureUpdate,
) -> dict:
    """Mettre à jour une facture."""
    store = _get_facture_store(request)
    with store.transaction() as transaction:
        facture = transaction.get(facture_id)
        if not facture:
            raise HTTPException(404, "Facture introuvable")
        update_data = facture_update.model_dump(exclude_unset=True)
        try:
            facture = Facture.model_validate({**facture.model_dump(), **update_data})
        except ValidationError as exc:
            raise HTTPException(422, exc.errors(include_context=False)) from exc
        exiger_dossier(cfg, facture.dossier_id)
        transaction[facture_id] = facture

    audit(cfg.log_dir, "facture_modifiee", cible=facture_id)
    return facture.model_dump()


@router.delete("/facture/{facture_id}")
def delete_facture(
    facture_id: str,
    request: Request,
) -> dict:
    """Supprimer une facture."""
    store = _get_facture_store(request)
    if facture_id not in store:
        raise HTTPException(404, "Facture introuvable")

    del store[facture_id]
    audit(cfg.log_dir, "facture_supprimee", cible=facture_id)
    return {"deleted": True, "id": facture_id}


# ───────────────────────────────────────────────────────────────
# Routes Statistiques Financières
# ───────────────────────────────────────────────────────────────

@router.get("/dossier/{dossier_id}/resume")
def resume_financier_dossier(
    dossier_id: str,
    request: Request,
) -> dict:
    """Résumé financier complet d'un dossier."""
    frais_store = _get_frais_store(request)
    facture_store = _get_facture_store(request)

    frais_dossier = [f for f in frais_store.values() if f.dossier_id == dossier_id]
    factures_dossier = [f for f in facture_store.values() if f.dossier_id == dossier_id]

    total_frais = sum(f.montant for f in frais_dossier)
    total_avances = sum(f.montant for f in frais_dossier if f.avance_client)
    total_honoraires = sum(f.montant for f in frais_dossier if f.categorie == "honoraires_transitaire")
    total_factures_client = sum(f.montant_ttc for f in factures_dossier if f.type_facture == "emisee")
    total_factures_fournisseurs = sum(f.montant_ttc for f in factures_dossier if f.type_facture == "recue")

    frais_payes = sum(f.montant for f in frais_dossier if f.statut_paiement == "paye")
    frais_en_attente = sum(f.montant for f in frais_dossier if f.statut_paiement == "en_attente")
    factures_payees = sum(f.montant_ttc for f in factures_dossier if f.statut_paiement == "payee")
    factures_en_attente = sum(f.montant_ttc for f in factures_dossier if f.statut_paiement == "en_attente")

    return {
        "dossier_id": dossier_id,
        "total_frais": total_frais,
        "total_avances": total_avances,
        "total_honoraires": total_honoraires,
        "total_factures_client": total_factures_client,
        "total_factures_fournisseurs": total_factures_fournisseurs,
        "frais_payes": frais_payes,
        "frais_en_attente": frais_en_attente,
        "factures_payees": factures_payees,
        "factures_en_attente": factures_en_attente,
        "solde_restant": total_factures_client - total_frais,
        "rentabilite": total_factures_client - total_frais,
        "par_categorie": {
            cat: sum(f.montant for f in frais_dossier if f.categorie == cat)
            for cat in set(f.categorie for f in frais_dossier)
        },
        "par_statut_frais": {
            "payes": frais_payes,
            "en_attente": frais_en_attente,
            "en_retard": sum(f.montant for f in frais_dossier if f.statut_paiement == "en_retard"),
        },
        "par_statut_factures": {
            "payees": factures_payees,
            "en_attente": factures_en_attente,
            "annulees": sum(f.montant_ttc for f in factures_dossier if f.statut_paiement == "annulee"),
        },
    }

# ───────────────────────────────────────────────────────────────
# Rapprochement Bancaire / Factures Automatique
# ───────────────────────────────────────────────────────────────

@router.post("/rapprochement/auto")
async def auto_rapprochement(
    request: Request,
    dossier_id: str = Body(...),
    date_debut: str = Body(...),
    date_fin: str = Body(...),
) -> dict:
    """Rapprochement automatique des opérations bancaires avec les factures."""

    facture_store = _get_facture_store(request)

    # Récupérer les opérations bancaires (simulé - en réalité viendrait d'un import bancaire)
    operations_bancaires = []  # TODO: récupérer depuis import bancaire

    # Récupérer factures du dossier non rapprochées
    factures = [f for f in facture_store.values() if f.dossier_id == dossier_id and not f.rapprochee]

    rapprochees = []
    non_rapprochees = []

    for facture in factures:
        # Recherche de correspondance par montant, date, référence
        matches = []
        for op in operations_bancaires:
            if _match_transaction(facture, op):
                matches.append(op)

        if len(matches) == 1:
            # Rapprochement automatique unique
            facture.rapprochee = True
            facture.operation_bancaire_id = matches[0].get("id")
            facture_store[facture.id] = facture
            rapprochees.append({
                "facture_id": facture.id,
                "operation_id": matches[0].get("id"),
                "type": "automatique",
                "confiance": 1.0
            })
        elif len(matches) > 1:
            # Ambiguïté - mettre en attente
            non_rapprochees.append({
                "facture_id": facture.id,
                "candidats": [m.get("id") for m in matches],
                "raison": "multiples_correspondances"
            })
        else:
            # Aucune correspondance
            non_rapprochees.append({
                "facture_id": facture.id,
                "raison": "aucune_correspondance"
            })

    return {
        "rapprochees": rapprochees,
        "non_rapprochees": non_rapprochees,
        "total_factures": len(factures),
        "taux_rapprochement": len(rapprochees) / len(factures) if factures else 0
    }


def _match_transaction(facture: Facture, operation: dict) -> bool:
    """Vérifie si une opération bancaire correspond à une facture."""
    # Comparaison par montant (avec tolérance)
    montant_facture = facture.montant_ttc
    montant_op = operation.get("montant", 0)
    if abs(montant_facture - montant_op) > 0.01:  # tolérance 1 centime
        return False

    # Comparaison par date (fenêtre de 3 jours)
    date_facture = facture.date_facture
    date_op = operation.get("date")
    if date_facture and date_op:
        try:
            df = datetime.fromisoformat(date_facture)
            do = datetime.fromisoformat(date_op)
            if abs((df - do).days) > 3:
                return False
        except (TypeError, ValueError):
            pass

    # Comparaison par référence (numéro facture, IBAN, etc.)
    ref_facture = facture.numero_facture
    ref_op = operation.get("reference", "")
    if ref_facture and ref_facture in ref_op:
        return True

    return False
# ───────────────────────────────────────────────────────────────

def _repertoire_justificatifs() -> Path:
    repertoire = cfg.data_dir / "justificatifs"
    if repertoire.is_symlink():
        raise HTTPException(503, "Répertoire des justificatifs non sûr")
    repertoire.mkdir(parents=True, exist_ok=True)
    return repertoire


def _chemin_justificatif(justificatif: Justificatif) -> Path:
    relatif = PurePosixPath(justificatif.chemin_fichier)
    if (len(relatif.parts) != 2 or relatif.parts[0] != "justificatifs"
            or not re.fullmatch(r"[a-f0-9]{32}\.bin", relatif.parts[1])):
        raise HTTPException(403, "Chemin de justificatif refusé")
    chemin = _repertoire_justificatifs() / relatif.parts[1]
    if chemin.is_symlink():
        raise HTTPException(403, "Lien symbolique de justificatif refusé")
    return chemin


@router.post("/justificatif/upload")
async def upload_justificatif(
    request: Request,
    frais_id: str = Form(...),
    fichier: UploadFile = File(...),
) -> dict:
    """Conserve une pièce (20 Mio max) et son lien au frais dans le magasin local."""
    try:
        contenu = await fichier.read(MAX_JUSTIFICATIF + 1)
    finally:
        await fichier.close()
    if not contenu:
        raise HTTPException(422, "Le justificatif est vide")
    if len(contenu) > MAX_JUSTIFICATIF:
        raise HTTPException(413, "Justificatif trop volumineux (maximum 20 Mio)")
    nom = (fichier.filename or "justificatif").replace("\\", "/").rsplit("/", 1)[-1]
    nom = "".join(c for c in nom if ord(c) >= 32 and ord(c) != 127)[:200] or "justificatif"
    mime = fichier.content_type or "application/octet-stream"
    if not re.fullmatch(r"[a-zA-Z0-9.+-]+/[a-zA-Z0-9.+-]+", mime):
        mime = "application/octet-stream"
    utilisateur = getattr(request.state, "utilisateur", None)
    justificatif = Justificatif(
        id=new_id("just_"), frais_id=frais_id, nom_fichier=nom,
        chemin_fichier="justificatifs/" + uuid.uuid4().hex + ".bin",
        type_mime=mime, taille_octets=len(contenu),
        uploaded_by=getattr(utilisateur, "nom", "utilisateur"),
        hash_sha256=hashlib.sha256(contenu).hexdigest(),
    )
    chemin = _chemin_justificatif(justificatif)
    temporaire = None
    try:
        with _get_frais_store(request).transaction() as transaction:
            frais = transaction.get(frais_id)
            if frais is None:
                raise HTTPException(404, "Frais introuvable")
            exiger_dossier(cfg, frais.dossier_id)
            with tempfile.NamedTemporaryFile(dir=chemin.parent, suffix=".tmp", delete=False) as fichier_tmp:
                temporaire = Path(fichier_tmp.name)
                fichier_tmp.write(contenu)
                fichier_tmp.flush()
                os.fsync(fichier_tmp.fileno())
            os.replace(temporaire, chemin)
            transaction.related("justificatif", Justificatif)[justificatif.id] = justificatif
            frais.justificatifs.append(justificatif.id)
            transaction[frais_id] = frais
    except Exception as exc:
        chemin.unlink(missing_ok=True)
        if temporaire is not None:
            temporaire.unlink(missing_ok=True)
        if isinstance(exc, (OSError, sqlite3.Error)):
            raise HTTPException(503, "Enregistrement du justificatif impossible") from exc
        raise
    audit(cfg.log_dir, "justificatif_ajoute", cible=justificatif.id, frais=frais_id)
    return {"id": justificatif.id, "nom_fichier": nom, "hash": justificatif.hash_sha256}


@router.get("/{frais_id}/justificatifs")
def list_justificatifs(frais_id: str, request: Request) -> list[dict]:
    with _get_frais_store(request).transaction() as transaction:
        if frais_id not in transaction:
            raise HTTPException(404, "Frais introuvable")
        return [j.model_dump(exclude={"chemin_fichier"}) for j in
                transaction.related("justificatif", Justificatif).values() if j.frais_id == frais_id]


@router.get("/justificatif/{justificatif_id}/download")
def download_justificatif(justificatif_id: str, request: Request) -> Response:
    with _get_justificatif_store(request).transaction() as transaction:
        justificatif = transaction.get(justificatif_id)
        if justificatif is None:
            raise HTTPException(404, "Justificatif introuvable")
        chemin = _chemin_justificatif(justificatif)
        try:
            with chemin.open("rb") as fichier:
                contenu = fichier.read(MAX_JUSTIFICATIF + 1)
        except FileNotFoundError:
            raise HTTPException(404, "Fichier justificatif absent") from None
        if (len(contenu) > MAX_JUSTIFICATIF or len(contenu) != justificatif.taille_octets
                or hashlib.sha256(contenu).hexdigest() != justificatif.hash_sha256):
            raise HTTPException(409, "Le fichier justificatif ne correspond plus à son empreinte")
    return Response(contenu, media_type=justificatif.type_mime, headers={
        "Content-Disposition": "attachment; filename*=UTF-8''" + quote(justificatif.nom_fichier, safe=""),
        "X-Content-Type-Options": "nosniff",
    })


@router.delete("/justificatif/{justificatif_id}")
def delete_justificatif(justificatif_id: str, request: Request) -> dict:
    chemin = quarantaine = None
    quarantaine_creee = False
    source_retiree = False
    try:
        with _get_justificatif_store(request).transaction() as transaction:
            justificatif = transaction.get(justificatif_id)
            if justificatif is None:
                raise HTTPException(404, "Justificatif introuvable")
            chemin = _chemin_justificatif(justificatif)
            quarantaine = chemin.with_name("." + chemin.name + ".deleted.tmp")
            if quarantaine.exists() or quarantaine.is_symlink():
                raise HTTPException(409, "Quarantaine déjà présente : examiner avec pieces-check avant suppression")
            if chemin.exists():
                # Réserve le nom sans écraser une preuve, même apparue depuis
                # le contrôle précédent. Aucun fallback vers replace.
                os.link(chemin, quarantaine)
                quarantaine_creee = True
                chemin.unlink()
                source_retiree = True
            frais_store = transaction.related("frais", Frais)
            frais = frais_store.get(justificatif.frais_id)
            if frais is not None:
                frais.justificatifs = [j for j in frais.justificatifs if j != justificatif_id]
                frais_store[frais.id] = frais
            del transaction[justificatif_id]
    except Exception as exc:
        if quarantaine_creee:
            try:
                if source_retiree:
                    # Ne jamais remplacer un fichier apparu pendant le rollback.
                    os.link(quarantaine, chemin)
                elif not os.path.samefile(quarantaine, chemin):
                    raise OSError("Le fichier source a changé pendant la suppression")
                quarantaine.unlink()
            except OSError as restauration:
                log.exception("Rétablissement impossible ; quarantaine conservée : %s", quarantaine)
                raise HTTPException(503, "Suppression annulée ; rétablissement incomplet, examiner avec pieces-check") from restauration
        if isinstance(exc, FileExistsError):
            raise HTTPException(409, "Quarantaine apparue pendant la suppression : aucun écrasement") from exc
        if isinstance(exc, (OSError, sqlite3.Error)):
            raise HTTPException(503, "Suppression du justificatif impossible") from exc
        raise
    if quarantaine_creee:
        try:
            quarantaine.unlink(missing_ok=True)
        except OSError:
            log.error("justificatif supprimé, nettoyage de quarantaine requis : %s", quarantaine)
    audit(cfg.log_dir, "justificatif_supprime", cible=justificatif_id)
    return {"deleted": True, "id": justificatif_id}
