"""Routes de gestion des clients (Module 01)."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Request, HTTPException
from pydantic import BaseModel
from typing import Any, Optional, List

from ..rbac import ADMINISTRATEUR, LECTEUR, SUPERVISEUR, TOUS
from ..models import Client, ClientStatus, new_id, CategorieFrais
from ..config import get_config
from ..logging_setup import audit, get_logger

log = get_logger("clients")

router = APIRouter(prefix="/api/clients", tags=["clients"])

cfg = get_config()


class ClientCreate(BaseModel):
    name: str
    legal_name: str
    status: str = "active"
    website: str = ""
    tax_id: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    city: str = ""
    country: str = "DZ"
    region: str = ""
    postal_code: str = ""
    contacts: list[str] = []
    notes: str = ""
    entreprise: str = ""
    wilaya: str = ""
    telephone_contact: str = ""
    email_contact: str = ""
    banque_domiciliataire: str = ""
    mandant_representant: str = ""


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    legal_name: Optional[str] = None
    status: Optional[str] = None
    website: Optional[str] = None
    tax_id: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    postal_code: Optional[str] = None
    contacts: Optional[list[str]] = None
    notes: Optional[str] = None
    entreprise: Optional[str] = None
    wilaya: Optional[str] = None
    telephone_contact: Optional[str] = None
    email_contact: Optional[str] = None
    banque_domiciliataire: Optional[str] = None
    mandant_representant: Optional[str] = None


_client_store: dict[str, Any] = {}


def _get_client_store(request: Request) -> dict:
    if not hasattr(request.app.state, 'client_store'):
        request.app.state.client_store = {}
    return request.app.state.client_store


@router.post("")
def create_client(
    request: Request,
    client: ClientCreate,
    current_user: Any = Depends(lambda r: None),
) -> dict:
    """Créer un nouveau client."""
    from ..models import Client, ClientStatus

    store = _get_client_store(request)
    client_id = f"client_{new_id().hex[:12]}"
    client_obj = Client(
        id=client_id,
        name=client.name,
        legal_name=client.legal_name,
        status=ClientStatus(client.status if client.status else "active"),
        website=client.website,
        tax_id=client.tax_id,
        phone=client.phone,
        email=client.email,
        address=client.address,
        city=client.city,
        country=client.country,
        region=client.region,
        postal_code=client.postal_code,
        contacts=client.contacts,
        notes=client.notes,
        entreprise=client.entreprise,
        wilaya=client.wilaya,
        telephone_contact=client.telephone_contact,
        email_contact=client.email_contact,
        banque_domiciliataire=client.banque_domiciliataire,
        mandant_representant=client.mandant_representant,
    )
    store[client_id] = client_obj
    audit(cfg.log_dir, "client_cree", acteur="admin", nom=client.name)
    return client_obj.as_dict()


@router.get("")
def list_clients(
    request: Request,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> list[dict]:
    """Lister tous les clients."""
    store = _get_client_store(request)
    clients = list(store.values())

    if status:
        clients = [c for c in clients if c.get("status", "").lower() == status.lower()]

    if search:
        search_lower = search.lower()
        clients = [c for c in clients if
            search_lower in c.get("name", "").lower() or
            search_lower in c.get("legal_name", "").lower() or
            search_lower in c.get("tax_id", "").lower() or
            search_lower in c.get("email", "").lower()
        ]

    return [c.as_dict() for c in clients]


@router.get("/{client_id}")
def get_client(
    client_id: str,
) -> dict:
    """Obtenir un client spécifique."""
    store = _get_client_store(request)
    client = store.get(client_id)
    if not client:
        raise HTTPException(404, "Client introuvable")
    return client.as_dict()


@router.put("/{client_id}")
def update_client(
    client_id: str,
    client_update: ClientUpdate,
) -> dict:
    """Mettre à jour un client."""
    store = _get_client_store(request)
    client = store.get(client_id)
    if not client:
        raise HTTPException(404, "Client introuvable")

    update_data = client_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(client, key, value)

    audit(cfg.log_dir, "client_modifie", cible=client_id)
    return client.as_dict()


@router.delete("/{client_id}")
def delete_client(
    client_id: str,
) -> dict:
    """Supprimer un client."""
    store = _get_client_store(request)
    if client_id not in store:
        raise HTTPException(404, "Client introuvable")

    del store[client_id]
    audit(cfg.log_dir, "client_supprime", cible=client_id)
    return {"deleted": True, "id": client_id}


@router.get("/{client_id}/dossiers")
def list_client_dossiers(
    client_id: str,
) -> list[dict]:
    """Lister les dossiers pour un client spécifique."""
    from ..dossier import DossierStore
    store = request.app.state.store

    dossiers = store.liste()
    return [d.as_dict() for d in dossiers]