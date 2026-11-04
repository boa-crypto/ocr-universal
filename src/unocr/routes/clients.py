"""Routes de gestion des clients (Module 01)."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, ValidationError

from ..config import get_config
from ..logging_setup import audit, get_logger
from ..models import new_id

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
    country: str = Field("DZ", max_length=2,
                         description="Pays (code ISO 3166-1 alpha-2)")
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
    country: Optional[str] = Field(None, max_length=2,
                                   description="Pays (code ISO 3166-1 alpha-2)")
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
) -> dict:
    """Créer un nouveau client."""
    from ..models import Client, ClientStatus

    store = _get_client_store(request)
    client_id = new_id("client_")
    try:
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
    except ValidationError as exc:
        # Le corps est validé avant d'atteindre le modèle : sans ce garde-fou,
        # un champ hors contraintes produisait une erreur 500 opaque.
        detail = "; ".join(
            f"{'.'.join(str(x) for x in err['loc'])} : {err['msg']}"
            for err in exc.errors()
        ) or "données client invalides"
        raise HTTPException(422, detail) from exc
    store[client_id] = client_obj
    audit(request.app.state.cfg.log_dir, "client_cree", acteur="admin", nom=client.name)
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
        voulu = status.lower()
        clients = [c for c in clients
                   if str(getattr(c.status, "value", c.status)).lower() == voulu]

    if search:
        terme = search.lower()
        champs = ("name", "legal_name", "tax_id", "email")
        clients = [c for c in clients
                   if any(terme in str(getattr(c, champ, "") or "").lower()
                          for champ in champs)]

    return [c.as_dict() for c in clients]


@router.get("/{client_id}")
def get_client(
    client_id: str,
    request: Request,
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
    request: Request,
) -> dict:
    """Mettre à jour un client."""
    store = _get_client_store(request)
    client = store.get(client_id)
    if not client:
        raise HTTPException(404, "Client introuvable")

    from ..models import ClientStatus

    update_data = client_update.model_dump(exclude_unset=True)
    if "status" in update_data and not isinstance(update_data["status"], ClientStatus):
        update_data["status"] = ClientStatus(update_data["status"])
    for key, value in update_data.items():
        setattr(client, key, value)

    audit(request.app.state.cfg.log_dir, "client_modifie", cible=client_id)
    return client.as_dict()


@router.delete("/{client_id}")
def delete_client(
    client_id: str,
    request: Request,
) -> dict:
    """Supprimer un client."""
    store = _get_client_store(request)
    if client_id not in store:
        raise HTTPException(404, "Client introuvable")

    del store[client_id]
    audit(request.app.state.cfg.log_dir, "client_supprime", cible=client_id)
    return {"deleted": True, "id": client_id}


@router.get("/{client_id}/dossiers")
def list_client_dossiers(
    client_id: str,
    request: Request,
) -> list[dict]:
    """Lister les dossiers rattachés à un client."""
    client = _get_client_store(request).get(client_id)
    if not client:
        raise HTTPException(404, "Client introuvable")

    from ..dossier import DossierStore

    cfg = request.app.state.cfg
    store = DossierStore(cfg.data_dir / "dossiers", log_dir=cfg.log_dir)
    # Le dossier peut référencer le client par son identifiant ou par son nom
    # selon qu'il vient de l'API transit ou de l'atelier documentaire.
    cibles = {client.id, client.name, client.legal_name}
    dossiers = [
        d for d in store.liste()
        if getattr(d, "client_id", "") in cibles
        or getattr(d, "client_importateur", "") in cibles
    ]
    return [d.as_dict() for d in dossiers]
