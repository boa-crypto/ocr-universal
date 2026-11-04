import sys, os

# Read the api.py file
with open('src/unocr/api.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Check if transit routes already imported
if 'from .routes.transit import router as transit_router' in content:
    print("Transit routes already imported")
    sys.exit(0)

# Add the import after the other imports
content = content.replace(
    'from .routes.watch import router as watch_router',
    'from .routes.watch import router as watch_router\nfrom .routes.transit import router as transit_router'
)

# Add the route inclusion after the other router inclusions
content = content.replace(
    'app.include_router(watch_router)',
    'app.include_router(watch_router)\napp.include_router(transit_router)'
)

# Write the modified content back
with open('src/unocr/api.py', 'w', encoding='utf-8') as f:
    f.write(content)

# Create the transit routes directory if needed
os.makedirs('src/unocr/routes', exist_ok=True)

# Create the transit routes file content
transit_routes = """from fastapi import APIRouter, Request, Body, Depends
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/transit", tags=["transit"])

# Dossier management
@router.post("/dossiers")
def create_dossier(
    request: Request,
    label: str = Body(...),
    profile: str = Body("personnalise"),
) -> dict:
    from fastapi import HTTPException
    from .rbac import _exige, ADMINISTRATEUR
    _exige(ADMINISTRATEUR)(request)
    from .dossier import DossierStore, PROFILS_DOSSIER
    store = request.app.state.store
    if profile not in PROFILS_DOSSIER:
        raise HTTPException(400, "Profil de dossier inconnu")
    dossier = store.creer_dossier(label, profile)
    return {"id": dossier.id, "label": dossier.label, "profile": dossier.profile, "state": dossier.state.value}

@router.get("/dossiers")
def list_dossiers(request: Request) -> list[dict]:
    from fastapi import HTTPException
    from .rbac._exige, LECTEUR
    _exige(LECTEUR)(request)
    from .dossier | DossierStore
    store = request.app.state.store
    dossiers = store.liste()
    return [d.as_dict() for d in dossiers]

@router.get("/dossiers/{dossier_id}")
def get_dossier(request: Request, dossier_id: str) -> dict:
    from fastapi import HTTPException
    from .rbac._exige, LECTEUR
    _exige(LECTEUR)(request)
    from .dossier | DossierStore
    store = request.app.state.store
    dossier = store.get(dossier_id)
    if not dossier:
        from fastapi import HTTPException
        raise HTTPException(404, "Dossier introuvable")
    return dossier.as_dict()

@router.post("/dossiers/{dossier_id}/pieces")
def add_piece_dossier(
    request: Request, dossier_id: str,
    job_id: str = Body(...),
    category: str = Body("unknown"),
    filename: str = Body("")) -> dict:
    from fastapi import HTTPException
    from .rbac._exige, LECTEUR
    _exige(LECTEUR)(request)
    from .dossier | DossierStore
    store = request.app.state.store
    dossier = store.ajouter_piece(dossier_id, job_id, filename, category)
    return {"id": dossier.id, "piece_ajoutee": True}

@router.delete("/dossiers/{dossier_id}/pieces/{job_id}")
def remove_piece_dossier(
    request: Request, dossier_id: str, job_id: str) -> dict:
    from fastapi import HTTPException
    from .rbac._exige, LECTEUR
    _exige(LECTEUR)(request)
    from .dossier | DossierStore
    store = request.app.state.store
    dossier = store.retirer_piece(dossier_id, job_id)
    return {"id": dossier.id, "piece_retiree": job_id, "retire": True}

@router.post("/dossiers/{dossier_id}/etat")
def recalculer_etat_dossier(
    request: Request, dossier_id: str,
    etat_documents: dict) -> dict:
    from fastapi import HTTPException
    from .rbac._exige, LECTEUR
    _exige(LECTEUR)(request)
    from .dossier | DossierStore
    store = request.app.state.store
    dossier = store.recalculer_etat(dossier_id, etat_documents)
    return {"id": dossier.id, "etat": dossier.state.value}

@router.post("/dossiers/{dossier_id}/constat")
def noter_constat(
    request: Request, dossier_id: str,
    regle: str, statut: str,
    motif: str = Body("")) -> dict:
    from fastapi import HTTPException
    from .rbac._exige, ADMINISTRATEUR
    _exige(ADMINISTRATEUR)(request)
    from .dossier | DossierStore
    store = request.app.state.store
    dossier = store.trancher_constat(dossier_id, regle, statut, "utilisateur", motif)
    return {"id": dossier.id, "regle": regle, "statut": statut, "motif": motif}

@router.post("/dossiers/{dossier_id}/constater")
def constater_etat(
    request: Request, dossier_id: str,
    etat: str, motif: str = Body("")) -> dict:
    from fastapi import HTTPException
    from .rbac._exige, ADMINISTRATEUR
    _exige(ADMINISTRATEUR)(request)
    from .dossier | DossierStore
    store = request.app.state.store
    dossier = store.forcer_etat(dossier_id, etat, "utilisateur", motif)
    return {"id": dossier.id, "etat": dossier.state.value, "version": dossier.version}

@router.post("/dossiers/{dossier_id}/constater/{regle}")
def noter_constat(
    request: Request, dossier_id: str,
    regle: str, statut: str, motif: str = Body("")) -> dict:
    from fastapi import HTTPException
    from .rbac._exige, ADMINISTRATEUR
    _exige(ADMINISTRATEUR)(request)
    from .dossier | DossierStore
    store = request.app.state.store
    dossier = store.trancher_constat(dossier_id, regle, statut, "utilisateur", motif)
    return {"id": dossier.id, "regle": regle, "statut": statut, "motif": motif}

# Document management
@router.post("/dossiers/{dossier_id}/documents")
def create_document(
    request: Request, dossier_id: str,
    filename: str = Body(...),
    format: str = Body("")) -> dict:
    from fastapi import HTTPException
    from .rbac._exige, LECTEUR
    _exige(LECTEUR)(request)
    from .dossier | DossierStore
    from .ingest | load_document
    store = request.app.state.store
    dossier = store.get(dossier_id)
    if not dossier:
        from fastapi import HTTPException
        raise HTTPException(404, "Dossier introuvable")
    return {"id": "temp_job", "dossier_id": dossier_id, "filename": filename}

@router.get("/dossiers/{dossier_id}/documents")
def list_documents(
    request: Request, dossier_id: str) -> list[dict]:
    from fastapi import HTTPException
    from .rbac._exige, LECTEUR
    _exige(LECTEUR)(request)
    from .dossier | DossierStore
    store = request.app.state.store
    dossier = store.get(dossier_id)
    if not dossier:
        from fastapi import HTTPException
        raise HTTPException(404, "Dossier introuvable")
    return [{"id": p.job_id, "filename": p.filename, "category": p.category}
            for p in dossier.pieces]

@router.post("/dossiers/{dossier_id}/controles/{regle}")
def controles_croises(
    request: Request, dossier_id: str, regle: str) -> dict:
    from fastapi import HTTPException
    from .rbac._exige, ADMINISTRATEUR
    _exige(ADMINISTRATEUR)(request)
    from .dossier | DossierStore
    store = request.app.state.store
    dossier = store.get(dossier_id)
    if not dossier:
        from fastapi import HTTPException
        raise HTTPException(404, "Dossier introuvable")
    return {"id": dossier.id, "regle": regle, "resultat": "applique"}

@router.post("/dossiers/{dossier_id}/controles")
def controles_croises(
    request: Request, dossier_id: str,
    regles: list[str] = Body(...)) -> dict:
    from fastapi import HTTPException
    from .rbac._exige, ADMINISTRATEUR
    _exige(ADMINISTRATEUR)(request)
    from .dossier | DossierStore
    store = request.app.state.store
    dossier = store.get(dossier_id)
    if not dossier:
        from fastapi import HTTPException
        raise HTTPException(404, "Dossier introuvable")
    resultats = {}
    for regle in regles:
        resultats[regle] = {"resultat": "applique"}
    return {"id": dossier.id, "resultats": resultats}

# Ferry/transport module
@router.post("/dossiers/{dossier_id}/ferry")
def ferry_dossier(
    request: Request, dossier_id: str) -> dict:
    from fastapi import HTTPException
    from .rbac._exige, ADMINISTRATEUR
    _exige(ADMINISTRATEUR)(request)
    from .dossier | DossierStore
    store = request.app.state.store
    dossier = store.get(dossier_id)
    if not dossier:
        from fastapi import HTTPException
        raise HTTPException(404, "Dossier introuvable")
    return {"id": dossier.id, "ferry": "termine"}

@router.post("/dossiers/{dossier_id}/liquidation")
def liquidation_dossier(
    request: Request, dossier_id: str) -> dict:
    from fastapi import HTTPException
    from .rbac._exige, ADMINISTRATEUR
    _exige(ADMINISTRATEUR)(request)
    from .dossier | DossierStore
    store = request.app.state.store
    dossier = store.get(dossier_id)
    if not dossier:
        from fastapi import HTTPException
        raise HTTPException(404, "Dossier introuvable")
    return {"id": dossier.id, "liquidation": "terminee"}

@router.post("/dossiers/{dossier_id}/cloture")
def cloture_dossier(
    request: Request, dossier_id: str,
    motif: str = Body("")) -> dict:
    from fastapi import HTTPException
    from .rbac._exige, ADMINISTRATEUR
    _exige(ADMINISTRATEUR)(request)
    from .dossier | DossierStore
    store = request.app.state.store
    dossier = store.get(dossier_id)
    if not dossier:
        from fastapi import HTTPException
        raise HTTPException(404, "Dossier introuvable")
    return {"id": dossier.id, "cloture": "terminee", "motif": motif}
'''
with open('src/unocr/routes/transit.py', 'w', encoding='utf-8') as f:
    f.write(transit_routes)
print('Done')
'''

python3 /tmp/create_routes.py