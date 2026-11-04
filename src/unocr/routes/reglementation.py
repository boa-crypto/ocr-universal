"""Routes API pour la réglementation et nomenclature tarifaire (Module 05)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..config import get_config
from ..logging_setup import audit, get_logger
from ..reglementation import (
    REGLES_REGLEMENTAIRES,
    TYPES_CERTIFICATS,
    calculer_droits,
    exiger_certificat,
    get_reglementation_store,
    initialiser_reglementation,
    normaliser_code_sh,
    obtenir_droits_complets,
    rechercher_classe_sh,
    verifier_code_sh,
)

log = get_logger("reglementation")

router = APIRouter(prefix="/api/reglementation", tags=["reglementation"])

cfg = get_config()


# ───────────────────────────────────────────────────────────────
# Schémas Pydantic
# ───────────────────────────────────────────────────────────────

class RechercheSH(BaseModel):
    mot_cle: str
    chapitre: Optional[str] = None


class CalculDroits(BaseModel):
    code_sh: str
    valeur: float
    devise: str = "EUR"


class CertificatRequest(BaseModel):
    type_certificat: str
    dossier_id: str


class CodeSHCreate(BaseModel):
    code_sh: str
    libelle: str
    chapitre: str


# ───────────────────────────────────────────────────────────────
# Routes
# ───────────────────────────────────────────────────────────────

@router.post("/initialiser")
def initialiser_base_reglementation(request: Request) -> dict:
    """Initialise la base de données réglementaire."""
    base = initialiser_reglementation()
    return {
        "message": "Base réglementaire initialisée",
        "version": base.get("version"),
        "codes_sh": len(base.get("codes_sh_algerie", {})),
        "regles": len(base.get("regles_reglementaires", {})),
        "certificats": len(base.get("types_certificats", {})),
    }


@router.get("/codes-sh")
def lister_codes_sh(
    chapitre: Optional[str] = None,
) -> list[dict]:
    """Liste tous les codes SH algériens, optionnellement filtrés par chapitre."""
    store = get_reglementation_store()
    base = store.get("base", {})
    codes = base.get("codes_sh_algerie", {})

    resultats = []
    for code, info in codes.items():
        if chapitre is None or info.get("chapitre") == chapitre:
            resultats.append({
                "code_sh": code,
                "libelle": info["libelle"],
                "chapitre": info["chapitre"],
            })

    resultats.sort(key=lambda x: x["code_sh"])
    return resultats


@router.post("/codes-sh/rechercher")
def rechercher_code_sh(
    request: Request,
    body: RechercheSH,
) -> list[dict]:
    """Recherche de classes SH par mot-clé."""
    resultats = rechercher_classe_sh(body.mot_cle, body.chapitre)
    return resultats


@router.get("/codes-sh/{code_sh}")
def get_code_sh(
    code_sh: str,
) -> dict:
    """Obtient les détails d'un code SH spécifique."""
    code_norm = normaliser_code_sh(code_sh)
    store = get_reglementation_store()
    base = store.get("base", {})
    codes = base.get("codes_sh_algerie", {})

    if code_norm not in codes:
        raise HTTPException(404, f"Code SH {code_sh} non trouvé")

    return {
        "code_sh": code_norm,
        "libelle": codes[code_norm]["libelle"],
        "chapitre": codes[code_norm]["chapitre"],
    }


@router.post("/codes-sh")
def creer_code_sh(
    request: Request,
    code: CodeSHCreate,
) -> dict:
    """Crée un nouveau code SH (admin uniquement)."""
    store = get_reglementation_store()
    base = store.get("base", {})
    codes = base.get("codes_sh_algerie", {})

    code_norm = normaliser_code_sh(code.code_sh)
    if code_norm in codes:
        raise HTTPException(409, f"Code SH {code_norm} existe déjà")

    codes[code_norm] = {
        "libelle": code.libelle,
        "chapitre": code.chapitre,
    }
    base["codes_sh_algerie"] = codes
    base["mise_a_jour"] = __import__('datetime').datetime.now().isoformat()
    store.set("base", base)

    audit(cfg.log_dir, "code_sh_cree", code=code_norm, libelle=code.libelle)
    return {"code_sh": code_norm, "libelle": code.libelle, "chapitre": code.chapitre}


@router.post("/droits/calculer")
def calculer_droits_douane(
    request: Request,
    body: CalculDroits,
) -> dict:
    """Calcule les droits de douane pour un code SH et une valeur."""
    if not verifier_code_sh(body.code_sh):
        raise HTTPException(400, f"Code SH invalide: {body.code_sh}")

    droits = calculer_droits("", body.code_sh, body.valeur, body.devise)
    audit(cfg.log_dir, "droits_calcules", code_sh=body.code_sh, valeur=body.valeur)
    return droits


@router.post("/droits/complets")
def droits_complets(
    request: Request,
    body: CalculDroits,
) -> dict:
    """Obtient tous les droits et taxes complets pour une classification."""
    result = obtenir_droits_complets(body.code_sh, body.valeur, body.devise)
    return result


@router.post("/certificats/exiger")
def exiger_certificat_route(
    request: Request,
    body: CertificatRequest,
) -> dict:
    """Exige un certificat pour un dossier."""
    try:
        certif = exiger_certificat(body.type_certificat, body.dossier_id)
        audit(cfg.log_dir, "certificat_exige", type=body.type_certificat, dossier=body.dossier_id)
        return certif
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/certificats")
def lister_certificats() -> list[dict]:
    """Liste tous les types de certificats exigibles."""
    return [
        {
            "type": k,
            "libelle": v["libelle"],
            "auteur": v["auteur"],
            "delai_validite_mois": v["delai_validite_mois"],
            "exigences": v["exigences"],
        }
        for k, v in TYPES_CERTIFICATS.items()
    ]


@router.get("/certificats/{type_cert}")
def get_certificat(
    type_cert: str,
) -> dict:
    """Obtient les détails d'un type de certificat."""
    if type_cert not in TYPES_CERTIFICATS:
        raise HTTPException(404, f"Type de certificat {type_cert} inconnu")

    return {
        "type": type_cert,
        **TYPES_CERTIFICATS[type_cert],
    }


@router.get("/regles")
def lister_regles() -> dict:
    """Liste toutes les règles réglementaires."""
    return {
        "regles": [
            {
                "nom": k,
                "obligatoire": v["obligatoire"],
                "source": v["source"],
                "documents_requis": v["documents_requis"],
                "description": v["description"],
            }
            for k, v in REGLES_REGLEMENTAIRES.items()
        ]
    }


@router.get("/regles/{nom_regle}")
def get_regle(
    nom_regle: str,
) -> dict:
    """Obtient les détails d'une règle réglementaire."""
    if nom_regle not in REGLES_REGLEMENTAIRES:
        raise HTTPException(404, f"Règle {nom_regle} inconnue")

    return {
        "nom": nom_regle,
        **REGLES_REGLEMENTAIRES[nom_regle],
    }


@router.get("/chapitres")
def lister_chapitres() -> list[dict]:
    """Liste les chapitres SH disponibles."""
    store = get_reglementation_store()
    base = store.get("base", {})
    codes = base.get("codes_sh_algerie", {})

    chapitres = {}
    for code, info in codes.items():
        chap = info["chapitre"]
        if chap not in chapitres:
            chapitres[chap] = {"chapitre": chap, "codes_count": 0}
        chapitres[chap]["codes_count"] += 1

    return list(chapitres.values())
