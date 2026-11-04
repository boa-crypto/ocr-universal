"""Contrôle Documentaire Intelligent (Module 04) - Moteur de comparaison croisée.

Ce module compare les documents d'un même dossier pour détecter :
- Incohérences (valeurs divergentes)
- Informations manquantes
- Documents expirés
- Doublons
- Contradictions entre pièces
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, List, Set

from .models import AnomalieDocumentaire, new_id
from .ocr_integration import get_ocr_integration
from .config import get_config
from .logging_setup import audit, get_logger

log = get_logger("controle_documentaire")

cfg = get_config()


# ───────────────────────────────────────────────────────────────
# Types d'anomalies
# ───────────────────────────────────────────────────────────────

class TypeAnomalie(str):
    INCOHERENCE = "incoherence"
    MANQUANT = "manquant"
    EXPIRE = "expire"
    DOUBLON = "doublon"
    CONTRADICTION = "contradiction"
    ILLISIBLE = "illisible"
    CHAMP_VIDE = "champ_vide"


class Gravite(str):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    BLOCKING = "blocking"


# ───────────────────────────────────────────────────────────────
# Règles de comparaison par type de document
# ───────────────────────────────────────────────────────────────

REGLES_COMPARAISON = {
    # Champs à comparer entre FACTURE ↔ PACKING LIST ↔ BL
    "identite_importateur": {
        "champs": ["buyer", "consignee", "importer", "importateur"],
        "types_docs": ["invoice", "bill_of_lading", "packing_list", "customs_declaration"],
        "gravite": Gravite.ERROR,
        "message": "Identité de l'importateur divergente entre documents"
    },
    "identite_fournisseur": {
        "champs": ["seller", "shipper", "exporter", "fournisseur"],
        "types_docs": ["invoice", "bill_of_lading", "packing_list", "certificate_of_origin"],
        "gravite": Gravite.ERROR,
        "message": "Identité du fournisseur divergente entre documents"
    },
    "designation_marchandise": {
        "champs": ["goods_description", "description", "items", "marchandise"],
        "types_docs": ["invoice", "bill_of_lading", "packing_list", "certificate_of_origin"],
        "gravite": Gravite.WARNING,
        "message": "Désignation de la marchandise divergente"
    },
    "quantite": {
        "champs": ["quantity", "packages_count", "nombre_colis", "quantite"],
        "types_docs": ["invoice", "bill_of_lading", "packing_list"],
        "gravite": Gravite.WARNING,
        "message": "Quantité divergente entre documents",
        "tolerance": 0.05  # 5% de tolérance
    },
    "nombre_colis": {
        "champs": ["packages_count", "nombre_colis", "colis"],
        "types_docs": ["invoice", "bill_of_lading", "packing_list"],
        "gravite": Gravite.WARNING,
        "message": "Nombre de colis divergent",
        "tolerance": 0.05
    },
    "poids_brut": {
        "champs": ["gross_weight", "poids_brut"],
        "types_docs": ["invoice", "bill_of_lading", "packing_list"],
        "gravite": Gravite.WARNING,
        "message": "Poids brut divergent",
        "tolerance": 0.02  # 2% de tolérance
    },
    "poids_net": {
        "champs": ["net_weight", "poids_net"],
        "types_docs": ["invoice", "bill_of_lading", "packing_list"],
        "gravite": Gravite.WARNING,
        "message": "Poids net divergent",
        "tolerance": 0.02
    },
    "devise": {
        "champs": ["currency", "devise"],
        "types_docs": ["invoice", "bill_of_lading", "customs_declaration"],
        "gravite": Gravite.ERROR,
        "message": "Devise divergente"
    },
    "valeur": {
        "champs": ["total_amount", "valeur", "valeur_commerciale", "amount"],
        "types_docs": ["invoice", "bill_of_lading", "customs_declaration"],
        "gravite": Gravite.WARNING,
        "message": "Valeur divergente",
        "tolerance": 0.01
    },
    "numero_bl": {
        "champs": ["bl_number", "numero_bl", "bill_of_lading_number"],
        "types_docs": ["bill_of_lading", "delivery_order", "customs_declaration"],
        "gravite": Gravite.ERROR,
        "message": "Numéro de BL divergent"
    },
    "conteneurs": {
        "champs": ["container_numbers", "conteneurs", "conteneur"],
        "types_docs": ["bill_of_lading", "packing_list", "delivery_order", "customs_declaration"],
        "gravite": Gravite.ERROR,
        "message": "Références conteneurs divergentes"
    },
    "pays_origine": {
        "champs": ["country_origin", "pays_origine", "origin"],
        "types_docs": ["certificate_of_origin", "customs_declaration", "invoice"],
        "gravite": Gravite.WARNING,
        "message": "Pays d'origine divergent"
    },
    "ports": {
        "champs": ["port_load", "port_discharge", "port_chargement", "port_dechargement"],
        "types_docs": ["bill_of_lading", "customs_declaration"],
        "gravite": Gravite.WARNING,
        "message": "Ports divergents"
    },
}


# ───────────────────────────────────────────────────────────────
# Moteur de contrôle
# ───────────────────────────────────────────────────────────────

@dataclass
class AnomalieDetectee:
    """Anomalie détectée lors du contrôle croisé."""
    type_anomalie: str
    regle: str
    documents_concernes: List[str]
    champ: str
    valeurs: Dict[str, str]  # doc_id -> valeur
    gravite: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


class ControleDocumentaireEngine:
    """Moteur de contrôle documentaire inter-documentaire."""

    def __init__(self) -> None:
        self.ocr_integration = get_ocr_integration()

    def _normalize_value(self, value: str) -> str:
        """Normalise une valeur pour comparaison."""
        if not value:
            return ""
        return " ".join(value.upper().split()).replace("-", "").replace("/", "").replace(".", "")

    def _extract_number(self, value: str) -> Optional[float]:
        """Extrait un nombre d'une chaîne."""
        if not value:
            return None
        import re
        txt = value.replace(" ", " ").replace("\xa0", " ").strip()
        txt = txt.replace(" ", "")
        if "," in txt and "." in txt:
            if txt.rfind(",") > txt.rfind("."):
                txt = txt.replace(".", "").replace(",", ".")
            else:
                txt = txt.replace(",", "")
        elif "," in txt:
            parts = txt.split(",")
            if len(parts) == 2 and len(parts[1]) in (1, 2):
                txt = txt.replace(",", ".")
            else:
                txt = txt.replace(",", "")
        m = re.search(r"-?\d+(?:\.\d+)?", txt)
        return float(m.group(0)) if m else None

    def _compare_values(self, val1: str, val2: str, tolerance: float = 0) -> bool:
        """Compare deux valeurs avec tolérance."""
        n1 = self._extract_number(val1)
        n2 = self._extract_number(val2)

        if n1 is not None and n2 is not None:
            if n1 == 0 and n2 == 0:
                return True
            if n1 == 0 or n2 == 0:
                return False
            diff = abs(n1 - n2)
            moy = (n1 + n2) / 2
            return (diff / moy) <= tolerance

        # Comparaison textuelle normalisée
        return self._normalize_value(val1) == self._normalize_value(val2)

    def _get_field_value(self, extraction, champ_candidates: List[str]) -> Optional[str]:
        """Récupère la valeur d'un champ depuis l'extraction."""
        for champ in extraction.champs_extraits:
            for candidate in champ_candidates:
                if candidate.lower() in champ.nom.lower():
                    # Priorité : confirmée > corrigée > normalisée > brute
                    return (champ.valeur_confirmee or champ.valeur_correctee
                            or champ.valeur_normale or champ.valeur_raw)
        return None

    def analyser_dossier(self, dossier_id: str) -> List[AnomalieDetectee]:
        """Analyse complète d'un dossier - retourne toutes les anomalies."""
        extractions = self.ocr_integration.extraction_store.par_dossier(dossier_id)

        if len(extractions) < 2:
            return []  # Pas assez de documents pour comparer

        anomalies: List[AnomalieDetectee] = []

        # 1. Vérifier documents expirés
        anomalies.extend(self._verifier_documents_expires(extractions))

        # 2. Vérifier documents illisibles
        anomalies.extend(self._verifier_documents_illisibles(extractions))

        # 3. Vérifier doublons
        anomalies.extend(self._verifier_doublons(extractions))

        # 4. Comparaisons croisées selon règles
        anomalies.extend(self._comparer_croise(extractions))

        # 5. Vérifier champs vides obligatoires
        anomalies.extend(self._verifier_champs_obligatoires(extractions))

        # Sauvegarder les anomalies
        self._sauvegarder_anomalies(dossier_id, anomalies)

        return anomalies

    def _verifier_documents_expires(self, extractions) -> List[AnomalieDetectee]:
        """Vérifie les documents expirés (certificats, etc.)."""
        anomalies = []
        maintenant = datetime.now()

        for ext in extractions:
            # Chercher date de validité/expiration dans les champs
            date_exp = None
            for champ in ext.champs_extraits:
                if any(kw in champ.nom.lower() for kw in ["expir", "valid_to", "expire", "validite"]):
                    try:
                        # Essayer plusieurs formats
                        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"]:
                            try:
                                date_exp = datetime.strptime(champ.valeur_raw, fmt)
                                break
                            except ValueError:
                                continue
                    except Exception:
                        pass

            if date_exp and date_exp < maintenant:
                anomalies.append(AnomalieDetectee(
                    type_anomalie=TypeAnomalie.EXPIRE,
                    regle="document_expire",
                    documents_concernes=[ext.id],
                    champ="date_expiration",
                    valeurs={ext.id: date_exp.strftime("%Y-%m-%d")},
                    gravite=Gravite.BLOCKING,
                    message=f"Document {ext.type_document} expiré le {date_exp.strftime('%d/%m/%Y')}",
                    details={"date_expiration": date_exp.isoformat()}
                ))

        return anomalies

    def _verifier_documents_illisibles(self, extractions) -> List[AnomalieDetectee]:
        """Vérifie les documents illisibles (confiance trop faible)."""
        anomalies = []
        for ext in extractions:
            if ext.confiance_globale < 0.3:
                anomalies.append(AnomalieDetectee(
                    type_anomalie=TypeAnomalie.ILLISIBLE,
                    regle="document_illisible",
                    documents_concernes=[ext.id],
                    champ="confiance_globale",
                    valeurs={ext.id: str(ext.confiance_globale)},
                    gravite=Gravite.ERROR,
                    message=f"Document {ext.type_document} illisible (confiance: {ext.confiance_globale:.0%})",
                    details={"confiance": ext.confiance_globale}
                ))
        return anomalies

    def _verifier_doublons(self, extractions) -> List[AnomalieDetectee]:
        """Détecte les documents en double (même type + même référence)."""
        anomalies = []
        vus: Dict[str, List] = {}

        for ext in extractions:
            # Clé de déduplication : type + référence principale
            ref = None
            for champ in ext.champs_extraits:
                if any(kw in champ.nom.lower() for kw in ["number", "numero", "reference", "ref"]):
                    ref = self._normalize_value(champ.valeur_raw or champ.valeur_normale or "")
                    if ref:
                        break

            if ref:
                cle = f"{ext.type_document}:{ref}"
                vus.setdefault(cle, []).append(ext)

        for cle, docs in vus.items():
            if len(docs) > 1:
                anomalies.append(AnomalieDetectee(
                    type_anomalie=TypeAnomalie.DOUBLON,
                    regle="document_double",
                    documents_concernes=[d.id for d in docs],
                    champ="reference",
                    valeurs={d.id: cle for d in docs},
                    gravite=Gravite.WARNING,
                    message=f"Doublon détecté : {len(docs)} documents de type {docs[0].type_document} avec même référence",
                    details={"cle_dedup": cle}
                ))

        return anomalies

    def _comparer_croise(self, extractions) -> List[AnomalieDetectee]:
        """Comparaisons croisées selon les règles définies."""
        anomalies = []

        # Grouper les extractions par type
        par_type: Dict[str, List] = {}
        for ext in extractions:
            par_type.setdefault(ext.type_document, []).append(ext)

        # Pour chaque règle de comparaison
        for regle_nom, regle in REGLES_COMPARAISON.items():
            types_concernes = [t for t in regle["types_docs"] if t in par_type]
            if len(types_concernes) < 2:
                continue  # Pas assez de types pour comparer

            # Collecter tous les documents concernés
            docs_concernes = []
            for t in types_concernes:
                docs_concernes.extend(par_type[t])

            if len(docs_concernes) < 2:
                continue

            # Pour chaque champ candidat de la règle
            for champ_candidate in regle["champs"]:
                valeurs: Dict[str, str] = {}
                docs_avec_valeur = []

                for doc in docs_concernes:
                    val = self._get_field_value(doc, [champ_candidate])
                    if val:
                        valeurs[doc.id] = val
                        docs_avec_valeur.append(doc)

                if len(valeurs) < 2:
                    continue  # Pas assez de valeurs pour comparer

                # Comparer toutes les paires
                valeurs_norm = {k: self._normalize_value(v) for k, v in valeurs.items()}
                uniques = set(valeurs_norm.values())

                if len(uniques) > 1:
                    # Divergence détectée
                    tolerance = regle.get("tolerance", 0)
                    # Vérifier si c'est une vraie divergence (au-delà tolérance)
                    vals_num = {k: self._extract_number(v) for k, v in valeurs.items()}
                    if all(v is not None for v in vals_num.values()):
                        # Comparaison numérique
                        max_v = max(vals_num.values())
                        min_v = min(vals_num.values())
                        if max_v > 0 and min_v > 0:
                            diff_pct = (max_v - min_v) / ((max_v + min_v) / 2)
                            if diff_pct <= tolerance:
                                continue  # Dans la tolérance

                    anomalies.append(AnomalieDetectee(
                        type_anomalie=TypeAnomalie.INCOHERENCE,
                        regle=regle_nom,
                        documents_concernes=list(valeurs.keys()),
                        champ=champ_candidate,
                        valeurs=valeurs,
                        gravite=regle["gravite"],
                        message=regle["message"],
                        details={
                            "tolerance": tolerance,
                            "types_docs": types_concernes
                        }
                    ))

        return anomalies

    def _verifier_champs_obligatoires(self, extractions) -> List[AnomalieDetectee]:
        """Vérifie la présence des champs obligatoires selon le type de document."""
        anomalies = []

        CHAMPS_OBLIGATOIRES = {
            "invoice": ["invoice_number", "invoice_date", "seller", "buyer", "total_amount"],
            "bill_of_lading": ["bl_number", "vessel", "shipper", "consignee"],
            "packing_list": ["gross_weight", "packages_count"],
            "certificate_of_origin": ["certificate_number", "country_origin"],
            "customs_declaration": ["declaration_number", "importer", "hs_code"],
            "delivery_order": ["do_number", "bl_number"],
            "release_note": ["release_number", "declaration_number"],
        }

        for ext in extractions:
            obligatoires = CHAMPS_OBLIGATOIRES.get(ext.type_document, [])
            for champ_req in obligatoires:
                trouve = False
                for champ in ext.champs_extraits:
                    if champ_req.lower() in champ.nom.lower():
                        if champ.valeur_raw or champ.valeur_normale or champ.valeur_confirmee:
                            trouve = True
                            break
                if not trouve:
                    anomalies.append(AnomalieDetectee(
                        type_anomalie=TypeAnomalie.MANQUANT,
                        regle=f"champ_obligatoire_{champ_req}",
                        documents_concernes=[ext.id],
                        champ=champ_req,
                        valeurs={ext.id: ""},
                        gravite=Gravite.ERROR,
                        message=f"Champ obligatoire '{champ_req}' manquant dans {ext.type_document}",
                        details={"type_document": ext.type_document}
                    ))

        return anomalies

    def _sauvegarder_anomalies(self, dossier_id: str, anomalies: List[AnomalieDetectee]) -> None:
        """Sauvegarde les anomalies dans le store."""
        for anom in anomalies:
            anom_obj = AnomalieDocumentaire(
                id=new_id("anom_"),
                dossier_id=dossier_id,
                regle_violée=anom.regle,
                type_anomalie=anom.type_anomalie,
                document_source=anom.documents_concernes[0] if anom.documents_concernes else "",
                document_reference=",".join(anom.documents_concernes[1:]) if len(anom.documents_concernes) > 1 else "",
                valeur_detectée=str(anom.valeurs),
                valeur_reference="",
                gravite=anom.gravite,
                responsable="",
                date_detection=datetime.now().strftime("%Y-%m-%d"),
                action_corrective=anom.message,
                statut_resolution="ouvert",
            )
            # Ici on pourrait sauvegarder dans un store dédié
            # Pour l'instant, log seulement
            log.info("Anomalie détectée: %s - %s", anom.regle, anom.message)


# ───────────────────────────────────────────────────────────────
# Fonction principale
# ───────────────────────────────────────────────────────────────

def analyser_dossier_complet(dossier_id: str) -> Dict[str, Any]:
    """Point d'entrée principal pour analyser un dossier."""
    engine = ControleDocumentaireEngine()
    anomalies = engine.analyser_dossier(dossier_id)

    # Compter par gravité
    par_gravite = {}
    for a in anomalies:
        par_gravite[a.gravite] = par_gravite.get(a.gravite, 0) + 1

    # Bloquant = ne peut pas passer à l'étape suivante
    bloquantes = [a for a in anomalies if a.gravite == Gravite.BLOCKING]

    return {
        "dossier_id": dossier_id,
        "total_anomalies": len(anomalies),
        "par_gravite": par_gravite,
        "anomalies_bloquantes": len(bloquantes),
        "peut_continuer": len(bloquantes) == 0,
        "anomalies": [
            {
                "type": a.type_anomalie,
                "regle": a.regle,
                "gravite": a.gravite,
                "message": a.message,
                "documents": a.documents_concernes,
                "champ": a.champ,
                "valeurs": a.valeurs,
            }
            for a in anomalies
        ]
    }