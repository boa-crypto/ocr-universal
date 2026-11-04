"""Routes de gestion des déclarations douanières et liquidations (Modules 08-09)."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..config import get_config
from ..logging_setup import audit, get_logger
from ..models import DeclarationDouaniere, Liquidation, new_id

log = get_logger("declarations")

router = APIRouter(prefix="/api/declarations", tags=["declarations"])

cfg = get_config()


# ───────────────────────────────────────────────────────────────
# Stores en mémoire
# ───────────────────────────────────────────────────────────────

_declaration_store: dict[str, DeclarationDouaniere] = {}
_liquidation_store: dict[str, Liquidation] = {}


def _get_declaration_store(request: Request) -> dict:
    if not hasattr(request.app.state, 'declaration_store'):
        request.app.state.declaration_store = {}
    return request.app.state.declaration_store


def _get_liquidation_store(request: Request) -> dict:
    if not hasattr(request.app.state, 'liquidation_store'):
        request.app.state.liquidation_store = {}
    return request.app.state.liquidation_store


# ───────────────────────────────────────────────────────────────
# Schémas Pydantic - Déclaration Douanière
# ───────────────────────────────────────────────────────────────

class DeclarationCreate(BaseModel):
    dossier_id: str
    numero_declaration: str = ""
    bureau_douane: str = ""
    date_depot: Optional[str] = None
    date_validation: Optional[str] = None
    statut: str = "en_preparation"
    agent_declarant: str = ""
    regime_douanier: str = ""
    origines: List[str] = []
    provenances: List[str] = []
    positions_tarifaires: List[str] = []
    valeurs_en_douane: List[float] = []
    droits_calcules: float = 0.0
    taxes_calculees: float = 0.0
    montant_total: float = 0.0
    documents_justificatifs: List[str] = []
    observations_douane: str = ""
    observations_agent: str = ""
    mainlevee_obtenue: bool = False
    date_mainlevee: Optional[str] = None


class DeclarationUpdate(BaseModel):
    dossier_id: Optional[str] = None
    numero_declaration: Optional[str] = None
    bureau_douane: Optional[str] = None
    date_depot: Optional[str] = None
    date_validation: Optional[str] = None
    statut: Optional[str] = None
    agent_declarant: Optional[str] = None
    regime_douanier: Optional[str] = None
    origines: Optional[List[str]] = None
    provenances: Optional[List[str]] = None
    positions_tarifaires: Optional[List[str]] = None
    valeurs_en_douane: Optional[List[float]] = None
    droits_calcules: Optional[float] = None
    taxes_calculees: Optional[float] = None
    montant_total: Optional[float] = None
    documents_justificatifs: Optional[List[str]] = None
    observations_douane: Optional[str] = None
    observations_agent: Optional[str] = None
    mainlevee_obtenue: Optional[bool] = None
    date_mainlevee: Optional[str] = None


# ───────────────────────────────────────────────────────────────
# Schémas Pydantic - Liquidation
# ───────────────────────────────────────────────────────────────

class LiquidationCreate(BaseModel):
    dossier_id: str
    declaration_id: str
    date_liquidation: Optional[str] = None
    droits_importation: float = 0.0
    tva: float = 0.0
    tpc: float = 0.0
    taxes_internes: float = 0.0
    total_douane: float = 0.0
    majorations: float = 0.0
    total_a_payer: float = 0.0
    statut: str = "en_attente"
    documents_liquidation: List[str] = []
    observations: str = ""


class LiquidationUpdate(BaseModel):
    dossier_id: Optional[str] = None
    declaration_id: Optional[str] = None
    date_liquidation: Optional[str] = None
    droits_importation: Optional[float] = None
    tva: Optional[float] = None
    tpc: Optional[float] = None
    taxes_internes: Optional[float] = None
    total_douane: Optional[float] = None
    majorations: Optional[float] = None
    total_a_payer: Optional[float] = None
    statut: Optional[str] = None
    documents_liquidation: Optional[List[str]] = None
    observations: Optional[str] = None


# ───────────────────────────────────────────────────────────────
# Routes Déclarations Douanières
# ───────────────────────────────────────────────────────────────

@router.post("")
def create_declaration(
    request: Request,
    declaration: DeclarationCreate,
) -> dict:
    """Créer une nouvelle déclaration douanière."""
    store = _get_declaration_store(request)
    decl_obj = DeclarationDouaniere(
        id=new_id("decl_"),
        dossier_id=declaration.dossier_id,
        numero_declaration=declaration.numero_declaration,
        bureau_douane=declaration.bureau_douane,
        date_depot=declaration.date_depot,
        date_validation=declaration.date_validation,
        statut=declaration.statut,
        agent_declarant=declaration.agent_declarant,
        regime_douanier=declaration.regime_douanier,
        origines=declaration.origines,
        provenances=declaration.provenances,
        positions_tarifaires=declaration.positions_tarifaires,
        valeurs_en_douane=declaration.valeurs_en_douane,
        droits_calcules=declaration.droits_calcules,
        taxes_calculees=declaration.taxes_calculees,
        montant_total=declaration.montant_total,
        documents_justificatifs=declaration.documents_justificatifs,
        observations_douane=declaration.observations_douane,
        observations_agent=declaration.observations_agent,
        mainlevee_obtenue=declaration.mainlevee_obtenue,
        date_mainlevee=declaration.date_mainlevee,
    )
    store[decl_obj.id] = decl_obj
    audit(cfg.log_dir, "declaration_creee", dossier=declaration.dossier_id, numero=declaration.numero_declaration)
    return decl_obj.model_dump()


@router.get("")
def list_declarations(
    request: Request,
    dossier_id: Optional[str] = None,
) -> list[dict]:
    """Lister toutes les déclarations douanières."""
    store = _get_declaration_store(request)
    decls = list(store.values())
    if dossier_id:
        decls = [d for d in decls if d.dossier_id == dossier_id]
    return [d.model_dump() for d in decls]


@router.get("/liquidation")
def list_liquidations(
    request: Request,
    dossier_id: Optional[str] = None,
) -> list[dict]:
    """Lister toutes les liquidations."""
    store = _get_liquidation_store(request)
    liqs = list(store.values())
    if dossier_id:
        liqs = [liq for liq in liqs if liq.dossier_id == dossier_id]
    return [liq.model_dump() for liq in liqs]


@router.get("/{declaration_id}")
def get_declaration(
    declaration_id: str,
    request: Request,
) -> dict:
    """Obtenir une déclaration spécifique."""
    store = _get_declaration_store(request)
    decl = store.get(declaration_id)
    if not decl:
        raise HTTPException(404, "Déclaration introuvable")
    return decl.model_dump()


@router.put("/{declaration_id}")
def update_declaration(
    declaration_id: str,
    request: Request,
    declaration_update: DeclarationUpdate,
) -> dict:
    """Mettre à jour une déclaration."""
    store = _get_declaration_store(request)
    decl = store.get(declaration_id)
    if not decl:
        raise HTTPException(404, "Déclaration introuvable")

    update_data = declaration_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(decl, key, value)

    audit(cfg.log_dir, "declaration_modifiee", cible=declaration_id)
    return decl.model_dump()


@router.delete("/{declaration_id}")
def delete_declaration(
    declaration_id: str,
    request: Request,
) -> dict:
    """Supprimer une déclaration."""
    store = _get_declaration_store(request)
    if declaration_id not in store:
        raise HTTPException(404, "Déclaration introuvable")

    del store[declaration_id]
    audit(cfg.log_dir, "declaration_supprimee", cible=declaration_id)
    return {"deleted": True, "id": declaration_id}


# ───────────────────────────────────────────────────────────────
# Routes Liquidations
# ───────────────────────────────────────────────────────────────

@router.post("/liquidation")
def create_liquidation(
    request: Request,
    liquidation: LiquidationCreate,
) -> dict:
    """Créer une nouvelle liquidation."""
    store = _get_liquidation_store(request)
    liq_obj = Liquidation(
        id=new_id("liqu_"),
        dossier_id=liquidation.dossier_id,
        declaration_id=liquidation.declaration_id,
        date_liquidation=liquidation.date_liquidation,
        droits_importation=liquidation.droits_importation,
        tva=liquidation.tva,
        tpc=liquidation.tpc,
        taxes_internes=liquidation.taxes_internes,
        total_douane=liquidation.total_douane,
        majorations=liquidation.majorations,
        total_a_payer=liquidation.total_a_payer,
        statut=liquidation.statut,
        documents_liquidation=liquidation.documents_liquidation,
        observations=liquidation.observations,
    )
    store[liq_obj.id] = liq_obj
    audit(cfg.log_dir, "liquidation_creee", dossier=liquidation.dossier_id, declaration=liquidation.declaration_id)
    return liq_obj.model_dump()


@router.get("/liquidation/{liquidation_id}")
def get_liquidation(
    liquidation_id: str,
    request: Request,
) -> dict:
    """Obtenir une liquidation spécifique."""
    store = _get_liquidation_store(request)
    liq = store.get(liquidation_id)
    if not liq:
        raise HTTPException(404, "Liquidation introuvable")
    return liq.model_dump()


@router.put("/liquidation/{liquidation_id}")
def update_liquidation(
    liquidation_id: str,
    request: Request,
    liquidation_update: LiquidationUpdate,
) -> dict:
    """Mettre à jour une liquidation."""
    store = _get_liquidation_store(request)
    liq = store.get(liquidation_id)
    if not liq:
        raise HTTPException(404, "Liquidation introuvable")

    update_data = liquidation_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(liq, key, value)

    audit(cfg.log_dir, "liquidation_modifiee", cible=liquidation_id)
    return liq.model_dump()


@router.delete("/liquidation/{liquidation_id}")
def delete_liquidation(
    liquidation_id: str,
    request: Request,
) -> dict:
    """Supprimer une liquidation."""
    store = _get_liquidation_store(request)
    if liquidation_id not in store:
        raise HTTPException(404, "Liquidation introuvable")

    del store[liquidation_id]
    audit(cfg.log_dir, "liquidation_supprimee", cible=liquidation_id)
    return {"deleted": True, "id": liquidation_id}
