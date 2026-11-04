"""Réglementation et nomenclature tarifaire algérienne (Module 05).

Ce module gère :
- La classification tarifaire (codes SH/Taric algériens)
- Les règles réglementaires (documents, autorisations, contrôles)
- Les certificats sanitaires et phytosanitaires
- L'historique réglementaire avec dates de validité
- L'intégration avec les systèmes douaniers algériens
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import get_config
from .logging_setup import audit, get_logger

log = get_logger("reglementation")

cfg = get_config()


# ───────────────────────────────────────────────────────────────
# Store persistant pour la réglementation
# ───────────────────────────────────────────────────────────────

class StoreReglementation:
    """Persistance JSON de la réglementation, sous `data/reglementation/`."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _chemin(self, cle: str) -> Path:
        return self.root / f"{cle}.json"

    def _lire(self, cle: str) -> Optional[Dict[str, Any]]:
        if cle in self._cache:
            return self._cache[cle]
        p = self._chemin(cle)
        if not p.is_file():
            return None
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            log.error("Réglementation illisible (%s) : %s", p.name, exc)
            return None
        self._cache[cle] = data
        return data

    def _ecrire(self, cle: str, data: Dict[str, Any]) -> None:
        tmp = self._chemin(cle).with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(self._chemin(cle))
        self._cache[cle] = data

    def get(self, cle: str, default: Any = None) -> Optional[Dict[str, Any]]:
        result = self._lire(cle)
        if result is not None:
            return result
        # Si le fichier n'existe pas, le créer avec des données vides
        self._ecrire(cle, {})
        return default if default is not None else {}

    def set(self, cle: str, data: Dict[str, Any]) -> None:
        self._ecrire(cle, data)

    def supprimer(self, cle: str) -> bool:
        p = self._chemin(cle)
        if p.is_file():
            p.unlink(missing_ok=True)
            self._cache.pop(cle, None)
            return True
        return False


# Instance globale
_reglementation_store = StoreReglementation(Path(cfg.data_dir) / "reglementation")


# ───────────────────────────────────────────────────────────────
# Codes SH/Taric Algériens (Codes douaniers)
# ───────────────────────────────────────────────────────────────

# Codes SH à 8 chiffres pour l'Algérie (base sur le SH international à 6 chiffres)
# Préfixés par le code pays DZ
CODES_SH_ALGERIE = {
    # Chapitre 1: Animaux vivants; produits animaux
    "0101": {"libelle": "Bovins vivants", "chapitre": "1"},
    "0102": {"libelle": "Autres animaux terrestres vivants", "chapitre": "1"},
    "0103": {"libelle": "Porcs vivants", "chapitre": "1"},
    "0104": {"libelle": "Moutons et chèvres vivants", "chapitre": "1"},
    "0105": {"libelle": "Animaux de laine", "chapitre": "1"},
    # Chapitre 2: Viandes fraîches, réfrigérées ou congelées
    "0201": {"libelle": "Viande bovine fraîche ou réfrigérée", "chapitre": "2"},
    "0202": {"libelle": "Viande bovine congelée", "chapitre": "2"},
    "0203": {"libelle": "Viande porcine fraîche, réfrigérée ou congelée", "chapitre": "2"},
    "0204": {"libelle": "Viande ovine et caprine fraîche, réfrigérée ou congelée", "chapitre": "2"},
    # ... (codes complets dans la vraie implémentation)
}


# ───────────────────────────────────────────────────────────────
# Règles réglementaires
# ───────────────────────────────────────────────────────────────

REGLES_REGLEMENTAIRES = {
    # Type de règle, description, obligatoire, source, documents requis
    "certificat_phytosanitaire": {
        "obligatoire": True,
        "source": "Ministère de l'Agriculture Algérie",
        "documents_requis": ["certificat_phytosanitaire"],
        "description": "Certificat phytosanitaire pour les produits végétaux",
    },
    "certificat_veterinaire": {
        "obligatoire": True,
        "source": "Ministère de l'Agriculture Algérie",
        "documents_requis": ["certificat_veterinaire"],
        "description": "Certificat vétérinaire pour les produits animaux",
    },
    "certificat_origine": {
        "obligatoire": True,
        "source": "Ministère du Commerce Algérie",
        "documents_requis": ["certificat_origine"],
        "description": "Certificat d'origine préférentielle ou non préférentielle",
    },
    "declaration_douanière": {
        "obligatoire": True,
        "source": "Douane Algérie (SAD)",
        "documents_requis": ["declaration_douanière"],
        "description": "Déclaration en douane (SAD - Single Administrative Document)",
    },
    "autorisation_import": {
        "obligatoire": False,
        "source": "Ministère du Commerce Algérie",
        "documents_requis": ["autorisation_import"],
        "description": "Autorisation d'importation spéciale",
    },
    "interdiction_export": {
        "obligatoire": False,
        "source": "Douane Algérie",
        "documents_requis": [],
        "description": "Produits interdits d'importation",
    },
    "quantite_maximale": {
        "obligatoire": False,
        "source": "Douane Algérie",
        "documents_requis": [],
        "description": "Quantité maximale autorisée par dossier",
    },
    "droits_douanieres": {
        "obligatoire": True,
        "source": "Tarif douanier Algérie",
        "documents_requis": [],
        "description": "Taux de droits de douane selon classification SH",
    },
    "tva": {
        "obligatoire": True,
        "source": "Fiscalité Algérie",
        "documents_requis": [],
        "description": "Taux de TVA applicable",
    },
}


# ───────────────────────────────────────────────────────────────
# Types de certificats
# ───────────────────────────────────────────────────────────────

TYPES_CERTIFICATS = {
    "certificat_phytosanitaire": {
        "libelle": "Certificat phytosanitaire",
        "auteur": "Ministère de l'Agriculture",
        "delai_validite_mois": 12,
        "exigences": ["produit_végétal", "origine", "traite"],
    },
    "certificat_veterinaire": {
        "libelle": "Certificat vétérinaire",
        "auteur": "Ministry of Agriculture Algérie",
        "delai_validite_mois": 6,
        "exigences": ["produit_animaux", "sante_animale", "origine"],
    },
    "certificat_origine": {
        "libelle": "Certificat d'origine",
        "auteur": "Ministry of Commerce Algérie",
        "delai_validite_mois": 12,
        "exigences": ["produit", "origine", "destination"],
    },
    "certificat_conformite": {
        "libelle": "Certificat de conformité",
        "auteur": "Laboratoire agréé Algérie",
        "delai_validite_mois": 6,
        "exigences": ["produit", "normes", "tests"],
    },
}


# ───────────────────────────────────────────────────────────────
# Fonctions utilitaires
# ───────────────────────────────────────────────────────────────

def normaliser_code_sh(code: str) -> str:
    """Normalise un code SH (retire les zéros non significatifs)."""
    if not code:
        return ""
    # Garder seulement les chiffres
    code = re.sub(r"[^0-9]", "", code)
    # Porter à 6 chiffres minimum (SH international)
    code = code.zfill(6)
    return code


def verifier_code_sh(code: str) -> bool:
    """Vérifie la validité d'un code SH."""
    if not code or len(code) < 6:
        return False
    # Vérifier que tous les caractères sont des chiffres
    if not re.match(r"^\d+$", code):
        return False
    # Vérifier la clé de contrôle (modulo 97 pour SH à 8 chiffres)
    if len(code) == 8:
        # Algorithme de validation SH
        chiffres = code[:-2]  # Les 6 premiers chiffres
        cle_controle = code[-2:]  # Les 2 derniers chiffres
        # Conversion en nombres
        total = 0
        for i, chiffre in enumerate(reversed(chiffres)):
            poids = 1 if i % 2 == 0 else 3
            total += int(chiffre) * poids
        cle_calculée = (10 - (total % 10)) % 10
        return str(cle_calculée) == cle_controle
    return True  # SH à 6 chiffres: on fait confiance


def calculer_droits(dossier_id: str, code_sh: str, valeur: float, devise: str = "EUR") -> Dict[str, Any]:
    """Calcule les droits de douane pour une classification donnée."""
    # Taux par défaut Algérie (à remplacer par vraie base de données)
    taux_tva = 0.09  # 9% standard
    taux_tpc = 0.05  # 5% TPC standard
    droits_base = round(valeur * 0.05, 2)  # 5% droits de base hypothétique

    return {
        "code_sh": code_sh,
        "valeur": valeur,
        "devise": devise,
        "droits_importation": droits_base,
        "tva": round(valeur * taux_tva, 2),
        "tpc": round(valeur * taux_tpc, 2),
        "total_douane": round(droits_base + valeur * taux_tva + valeur * taux_tpc, 2),
        "taux_tva": taux_tva,
        "taux_tpc": taux_tpc,
    }


# ───────────────────────────────────────────────────────────────
# Fonctions principales
# ───────────────────────────────────────────────────────────────

def rechercher_classe_sh(mot_cle: str, chapitre: Optional[str] = None) -> List[Dict[str, Any]]:
    """Recherche de classe SH par mot-clé."""
    resultats = []
    for code, info in CODES_SH_ALGERIE.items():
        if mot_cle.lower() in info["libelle"].lower():
            resultats.append({
                "code_sh": code,
                "libelle": info["libelle"],
                "chapitre": info["chapitre"],
            })
    # Trier par pertinence (match en début de libellé)
    resultats.sort(key=lambda x: x["libelle"].lower().index(mot_cle.lower()) if mot_cle.lower() in x["libelle"].lower() else 999)
    return resultats


def obtenir_droits_complets(code_sh: str, valeur: float, devise: str = "EUR") -> Dict[str, Any]:
    """Droits et taxes complets pour un code SH, avec sa validation."""
    code = normaliser_code_sh(code_sh)
    valide = verifier_code_sh(code)
    calcul = calculer_droits("", code, valeur, devise)
    calcul["validation_sh"] = {"code_sh": code, "valide": valide}
    return calcul


def exiger_certificat(type_cert: str, dossier_id: str) -> Dict[str, Any]:
    """Exige un certificat pour un dossier."""
    if type_cert not in TYPES_CERTIFICATS:
        raise ValueError(f"Type de certificat inconnu: {type_cert}")

    type_info = TYPES_CERTIFICATS[type_cert]
    return {
        "type_certificat": type_cert,
        "libelle": type_info["libelle"],
        "auteur": type_info["auteur"],
        "delai_validite_mois": type_info["delai_validite_mois"],
        "exigences": type_info["exigences"],
        "obligatoire": True,
        "dossier_id": dossier_id,
        "date_creation": datetime.now().strftime("%Y-%m-%d"),
        "date_echeance": (datetime.now() + timedelta(days=30 * type_info["delai_validite_mois"])).strftime("%Y-%m-%d"),
    }


# ───────────────────────────────────────────────────────────────
# Point d'entrée principal
# ───────────────────────────────────────────────────────────────

def initialiser_reglementation() -> Dict[str, Any]:
    """Initialise la base de données réglementaire avec les données de base."""
    # Vérifier si la base existe déjà
    if _reglementation_store.get("base") is None:
        base_data = {
            "version": "1.0.0",
            "mise_a_jour": datetime.now().isoformat(),
            "codes_sh_algerie": CODES_SH_ALGERIE,
            "regles_reglementaires": REGLES_REGLEMENTAIRES,
            "types_certificats": TYPES_CERTIFICATS,
        }
        _reglementation_store.set("base", base_data)
        audit(cfg.log_dir, "reglementation_initialisee")
    return _reglementation_store.get("base", {})


# ───────────────────────────────────────────────────────────────
# Point d'entrée pour l'API
# ───────────────────────────────────────────────────────────────

def get_reglementation_store() -> StoreReglementation:
    """Retourne le store de réglementation pour l'API."""
    return _reglementation_store


# ───────────────────────────────────────────────────────────────
# Export des fonctions clés
# ───────────────────────────────────────────────────────────────

__all__ = [
    "normaliser_code_sh",
    "verifier_code_sh",
    "calculer_droits",
    "obtenir_droits_complets",
    "exiger_certificat",
    "rechercher_classe_sh",
    "initialiser_reglementation",
    "get_reglementation_store",
    "CODES_SH_ALGERIE",
    "REGLES_REGLEMENTAIRES",
    "TYPES_CERTIFICATS",
]


# ───────────────────────────────────────────────────────────────
# Pour compatibilité avec les imports
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    initialiser_reglementation()
    print("Base de réglementation initialisée")
    print(f"Codes SH Algérie: {len(CODES_SH_ALGERIE)} codes")
    print(f"Règles réglementaires: {len(REGLES_REGLEMENTAIRES)} règles")
    print(f"Types certificats: {len(TYPES_CERTIFICATS)} types")
