"""Routes de gestion des frais, finances et facturation (Module 10)."""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Body, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from ..config import get_config
from ..logging_setup import audit, get_logger
from ..models import Facture, Frais, Justificatif, new_id

log = get_logger("frais")

router = APIRouter(prefix="/api/frais", tags=["frais"])

cfg = get_config()


# ───────────────────────────────────────────────────────────────
# Stores en mémoire
# ───────────────────────────────────────────────────────────────

_frais_store: dict[str, Frais] = {}
_facture_store: dict[str, Facture] = {}


def _get_justificatif_store(request: Request) -> dict:
    if not hasattr(request.app.state, 'justificatif_store'):
        request.app.state.justificatif_store = {}
    return request.app.state.justificatif_store


def _get_frais_store(request: Request) -> dict:
    if not hasattr(request.app.state, 'frais_store'):
        request.app.state.frais_store = {}
    return request.app.state.frais_store


def _get_facture_store(request: Request) -> dict:
    if not hasattr(request.app.state, 'facture_store'):
        request.app.state.facture_store = {}
    return request.app.state.facture_store


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
    store[frais_obj.id] = frais_obj
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
    frais = store.get(frais_id)
    if not frais:
        raise HTTPException(404, "Frais introuvable")

    update_data = frais_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(frais, key, value)

    audit(cfg.log_dir, "frais_modifie", cible=frais_id)
    return frais.model_dump()


@router.delete("/{frais_id}")
def delete_frais(
    frais_id: str,
    request: Request,
) -> dict:
    """Supprimer un frais."""
    store = _get_frais_store(request)
    if frais_id not in store:
        raise HTTPException(404, "Frais introuvable")

    del store[frais_id]
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
    store[facture_obj.id] = facture_obj
    audit(cfg.log_dir, "facture_creee", dossier=facture.dossier_id, numero=facture.numero_facture)
    return facture_obj.model_dump()


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
    facture = store.get(facture_id)
    if not facture:
        raise HTTPException(404, "Facture introuvable")

    update_data = facture_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(facture, key, value)

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

@router.post("/justificatif/upload")
async def upload_justificatif(
    request: Request,
    frais_id: str = Body(...),
    fichier: UploadFile = File(...),
) -> dict:
    """Upload un justificatif pour un frais."""
    import hashlib

    import aiofiles

    from ..config import get_config

    cfg = get_config()
    upload_dir = Path(cfg.data_dir) / "justificatifs"
    upload_dir.mkdir(parents=True, exist_ok=True)

    frais_store = _get_frais_store(request)
    frais = frais_store.get(frais_id)
    if not frais:
        raise HTTPException(404, "Frais introuvable")

    # Lire le fichier et calculer hash
    content = await fichier.read()
    sha256 = hashlib.sha256(content).hexdigest()

    # Sauvegarder le fichier
    ext = Path(fichier.filename).suffix
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = Path("data") / "justificatifs" / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # Créer le justificatif
    justificatif = Justificatif(
        id=new_id("just_"),
        frais_id=frais_id,
        nom_fichier=fichier.filename,
        chemin_fichier=str(file_path),
        type_mime=fichier.content_type or "application/octet-stream",
        taille_octets=len(content),
        uploaded_by="user",  # TODO: récupérer user réel
        hash_sha256=sha256,
    )

    # Sauvegarder le justificatif
    justificatif_store = _get_justificatif_store(request)
    justificatif_store[frais_id] = justificatif_store.get(frais_id, []) + [justificatif]

    # Lier au frais
    frais.justificatifs.append(f.id)
    frais_store[frais_id] = frais

    return {"id": justificatif.id, "nom_fichier": justificatif.nom_fichier, "hash": justificatif.hash_sha256}


@router.get("/justificatif/{justificatif_id}/download")
async def download_justificatif(justificatif_id: str, request: Request):
    """Télécharger un justificatif."""
    import os

    from fastapi.responses import FileResponse

    justificatif_store = _get_justificatif_store(request)
    for frais_id, justificatifs in justificatif_store.items():
        for j in justificatifs:
            if j.id == justificatif_id:
                if os.path.exists(j.chemin_fichier):
                    return FileResponse(
                        j.chemin_fichier,
                        filename=j.nom_fichier,
                        media_type=j.type_mime
                    )
    raise HTTPException(404, "Justificatif introuvable")


@router.delete("/justificatif/{justificatif_id}")
async def delete_justificatif(justificatif_id: str, request: Request):
    """Supprimer un justificatif."""
    justificatif_store = _get_justificatif_store(request)
    for frais_id, justificatifs in justificatif_store.items():
        for i, j in enumerate(justificatifs):
            if j.id == justificatif_id:
                # Supprimer fichier physique
                if os.path.exists(j.chemin_fichier):
                    os.remove(j.chemin_fichier)
                # Retirer de la liste
                justificatif_store[frais_id].pop(i)
                # Retirer du frais
                frais_store = _get_frais_store(request)
                for f in frais_store.values():
                    if j.id in f.justificatifs:
                        f.justificatifs.remove(j.id)
                return {"deleted": True, "id": justificatif_id}
    raise HTTPException(404, "Justificatif introuvable")
