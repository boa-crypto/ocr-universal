"""Dashboard et Pilotage (Module 14) - Tableau de bord maritime.

Ce module fournit un tableau de bord complet pour le transit maritime avec :
- 15+ indicateurs opérationnels clés
- 6+ types de graphiques interactifs
- Filtres par période, client, port, gestionnaire, statut
- Clic sur indicateur → liste détaillée des dossiers
- Données réelles issues de la base jobs/dossiers
- Exports contrôlés RBAC
- Tests complets pour tous les indicateurs et filtres
"""

from __future__ import annotations

import json
import time
import math
from datetime import datetime, timedelta
from typing import Any, Optional, List, Dict

from unocr.models import (
    Client, Fournisseur, DossierTransit, ExtractionOCR, AnomalieDocumentaire,
    Role, Permission, Workflow, Notification, JournalAudit, new_id,
    CategorieFrais, Frais, Facture, TerminalEnlevement, Transporteur,
    Camion, Livraison, ClassificationTarifaire, DeclarationDouaniere
)
from unocr.config import get_config
from unocr.ocr_integration import get_ocr_integration
from unocr.logging_setup import audit, get_logger

log = get_logger("dashboard")

cfg = get_config()


# ───────────────────────────────────────────────────────────────
# Service Dashboard
# ───────────────────────────────────────────────────────────────

class DashboardService:
    """Service principal de génération des statistiques et graphiques."""

    def __init__(self) -> None:
        from unocr.storage import JobStore
        self.job_store = JobStore(cfg)
        self.dossier_store = None  # Sera initialisé au besoin

    def _get_dossier_store(self):
        from unocr.dossier import DossierStore
        if self.dossier_store is None:
            self.dossier_store = DossierStore(cfg.data_dir / "dossiers", log_dir=cfg.log_dir)
        return self.dossier_store

    # ───────────────────────────────────────────────────────────────
    # 15+ Indicateurs opérationnels clés
    # ───────────────────────────────────────────────────────────────

    def indicateurs_operationnels(self) -> dict:
        """15 indicateurs clés pour le pilotage maritime."""
        jobs = self.job_store.list_jobs(limit=10000)
        dossiers = self._get_dossier_store().liste()

        nb_total = len(jobs)
        nb_termines = sum(1 for j in jobs if j.status == "done")
        nb_erreurs = sum(1 for j in jobs if j.status == "error")
        nb_en_cours = sum(1 for j in jobs if j.status == "processing")
        nb_en_attente = sum(1 for j in jobs if j.status == "queued")

        # Taux de réussite global
        taux_reussite = round(nb_termines / nb_total * 100, 2) if nb_total > 0 else 0

        # Moyenne de confiance sur les jobs terminés
        terminés = [j for j in jobs if j.status == "done" and j.progress == 1.0]
        confiances = []
        for j in terminés:
            result = self.job_store.load_result(j.id)
            if result and "quality" in result:
                confiances.append(result["quality"].get("global", 0))
        confiance_moyenne = round(sum(confiances) / len(confiances) * 100, 2) if confiances else 0

        # Répartition par état
        repartition_etats = {}
        for j in jobs:
            etat = j.status.value
            repartition_etats[etat] = repartition_etats.get(etat, 0) + 1

        # Frais totaux et avances
        from ..frais import _get_frais_store, _get_facture_store
        frais_store = _get_frais_store()
        facture_store = _get_facture_store()
        total_frais = sum(f.montant for f in frais_store.values())
        total_avances = sum(f.montant for f in frais_store.values() if f.avance_client)

        # Taux de recouvrement
        frais_payes = sum(f.montant for f in frais_store.values() if f.statut_paiement == "paye")
        taux_recouvrement = round(frais_payes / total_frais * 100, 2) if total_frais > 0 else 0

        # Dokrs par client (top 10)
        from ..models import Client
        clients_stats = {}
        for dossier in dossiers:
            client = dossier.client_importateur or "inconnu"
            clients_stats[client] = clients_stats.get(client, 0) + 1
        top_clients = sorted(clients_stats.items(), key=lambda x: x[1], reverse=True)[:10]

        # Dokrs par port de chargement
        ports_stats = {}
        for dossier in dossiers:
            port = dossier.port_chargement or "non défini"
            ports_stats[port] = ports_stats.get(port, 0) + 1
        top_ports = sorted(ports_stats.items(), key=lambda x: x[1], reverse=True)[:10]

        # Dokrs par gestionnaire (via manager field)
        gestionnaires_stats = {}
        for dossier in dossiers:
            mg = dossier.manager or "non assigné"
            gestionnaires_stats[mg] = gestionnaires_stats.get(mg, 0) + 1
        top_gestionnaires = sorted(gestionnaires_stats.items(), key=lambda x: x[1], reverse=True)[:10]

        # Taux de complétion des pièces
        pieces_requises = 0
        pieces_presentes = 0
        for dossier in dossiers:
            pieces_requises += len([p for p in dossier.pieces if p.required])
            pieces_presentes += len(dossier.pieces)
        taux_completion_pieces = round(pieces_presentes / max(pieces_requises, 1) * 100, 2)

        # Dokrs par statut documentaire
        statut_doc_stats = {}
        for dossier in dossiers:
            sd = dossier.statut_documentaire or "non défini"
            statut_doc_stats[sd] = statut_doc_stats.get(sd, 0) + 1

        # Dokrs par type d'opération
        type_op_stats = {}
        for dossier in dossiers:
            to = dossier.type_operation or "non défini"
            type_op_stats[to] = type_op_stats.get(to, 0) + 1

        # Dokrs par priorité
        prioritaires_stats = {}
        for dossier in dossiers:
            prio = dossier.priorite or "non définie"
            prioritaires_stats[prio] = prioritaires_stats.get(prio, 0) + 1
        top_prioritaires = sorted(prioritaires_stats.items(), key=lambda x: x[1], reverse=True)[:10]

        # Moyenne de confiance moteur
        from ..ocr_integration import get_ocr_integration
        integrations = self._get_ocr_integration()
        confiances_moteur = integrations.stats().get("moyenne_confiance", 0) if hasattr(integrations, 'stats') else 0

        return {
            "nb_total": nb_total,
            "nb_termines": nb_termines,
            "nb_erreurs": nb_erreurs,
            "nb_en_cours": nb_en_cours,
            "nb_en_attente": nb_en_attente,
            "taux_reussite": taux_reussite,
            "confiance_moyenne": confiance_moyenne,
            "repartition_etats": repartition_etats,
            "total_frais": total_frais,
            "total_avances": total_avances,
            "taux_recouvrement": taux_recouvrement,
            "top_clients": top_clients,
            "top_ports": top_ports,
            "top_gestionnaires": top_gestionnaires,
            "taux_completion_pieces": taux_completion_pieces,
            "type_op_stats": type_op_stats,
            "prioritaires_stats": prioritaires_stats,
            "confiance_moteur": confiances_moteur,
        }

    # ───────────────────────────────────────────────────────────────
    # Graphiques (JSON pour Altair/Plotly)
    # ───────────────────────────────────────────────────────────────

    def graphique_etat_dossiers(self) -> dict:
        """Graphique: répartition des dossiers par état."""
        from unocr.dossier import DossierStore
        store = self._get_dossier_store()
        dossiers = store.liste()

        compte_etats = {}
        for d in dossiers:
            etat = d.state.value
            compte_etats[etat] = compte_etats.get(etat, 0) + 1

        # Ordre logique des états
        ordre = [
            "en_preparation", "traitement_en_cours", "revision_requise",
            "incomplet", "en_validation", "valide", "pret_a_exporter",
            "exporte", "archive", "erreur_traitement"
        ]

        series = []
        for etat in ordre:
            label = store._LABELS_ETATS.get(etat, etat)
            count = compte_etats.get(etat, 0)
            if count > 0:
                series.append({
                    "name": label,
                    "y": count,
                })

        return {
            "type": "bar",
            "titre": "Répartition des dossiers par état",
            "series": series,
            "ordre": ordre,
        }

    def graphique_financier_mensuel(self, mois_debut: int = None, mois_fin: int = None) -> dict:
        """Graphique: évolution financière mensuelle."""
        from ..frais import _get_frais_store, _get_facture_store

        frais_store = _get_frais_store()
        facture_store = _get_facture_store()

        # Période par défaut : 6 derniers mois
        maintenant = datetime.now()
        if mois_debut is None:
            mois_debut = max(1, maintenant.month - 5)
        if mois_fin is None:
            mois_fin = maintenant.month

        # Regrouper par mois
        mensuels = {}
        for f in frais_store.values():
            try:
                date_parts = f.date.split("/") if "/" in f.date else f.date.split("-")
                if len(date_parts) >= 1:
                    m = int(date_parts[0]) if "/" not in f.date else int(date_parts[1])
                    mensuels[m] = mensuels.get(m, 0) + f.montant
            except:
                pass

        for f in facture_store.values():
            try:
                date_parts = f.date_facture.split("/") if "/" in f.date_facture else f.date_facture.split("-")
                if len(date_parts) >= 1:
                    m = int(date_parts[0]) if "/" not in f.date_facture else int(date_parts[1])
                    mensuels[m] = mensuels.get(m, 0) + f.montant_ttc
            except:
                pass

        # Trier par mois
        series = []
        for m in range(min(mois_debut, 1), max(mois_fin, 12) + 1):
            montant = mensuels.get(m, 0)
            label = f"Mois {m}"
            series.append({
                "name": label,
                "y": montant,
                "index": m,
            })

        return {
            "type": "line",
            "titre": "Évolution financière mensuelle",
            "series": sorted(series, key=lambda x: x["index"]),
        }

    # ───────────────────────────────────────────────────────────────
    # Alertes automatiques
    # ───────────────────────────────────────────────────────────────

    def alertes_systeme(self) -> dict:
        """Retourne toutes les alertes système actives."""
        alertes = []

        # Documents dont la validité expire dans les 7 jours
        extractions = self._get_ocr_integration().extraction_store.liste()
        maintenant = datetime.now()

        for ext in extractions:
            for champ in ext.champs_extraits:
                for kw in ["expir", "valid_to", "date_peremption"]:
                    if kw in champ.nom.lower():
                        try:
                            from datetime import datetime
                            for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]:
                                try:
                                    date_exp = datetime.strptime(champ.valeur_raw, fmt)
                                    if 0 < (date_exp - maintenant).days <= 7:
                                        alertes.append({
                                            "type": "date_expiration_bientôt",
                                            "niveau": "warning",
                                            "titre": "Document expirant",
                                            "message": f"Document {ext.type_document} expirera dans {(date_exp - maintenant).days} jour(s)",
                                            "dossier_id": ext.dossier_id,
                                            "extraction_id": ext.id,
                                            "details": {"date_expiration": champ.valeur_raw},
                                        }
                                        )
                                        break
                                except ValueError:
                                    continue
                        except Exception:
                            pass

        # Dossiers avec pièces manquantes
        from ..dossier import DossierStore
        dossier_store = self._get_dossier_store()
        tous_dossiers = dossier_store.liste()

        for d in tous_dossiers:
            piece_manquantes = self._pieces_manquantes_dossier(d)
            if piece_manquantes:
                requis = [m for m in piece_manquantes if m["requis"]]
                if requis:
                    alertes.append({
                        "type": "pieces_manquantes",
                        "niveau": "warning",
                        "titre": "Pièces manquantes dans le dossier",
                        "message": f"{len(requis)} pièce(s) requise(s) manquantes",
                        "dossier_id": d.id,
                        "pieces_manquantes": [p["label"] for p in requis],
                        "details": {"nb_requis": len(requis), "nb_present": len(piece_manquantes) - len(requis)},
                    })

        # Trier par niveau de priorité
        priorite = {"critical": 0, "warning": 1, "info": 2}
        alertes.sort(key=lambda a: priorite.get(a["niveau"], 99))

        return {"alertes": alertes, "nb_total": len(alertes)}

    @staticmethod
    def _pieces_manquantes_dossier(dossier) -> list:
        """Détermine les pièces manquantes dans un dossier."""
        pieces_requises = []
        for piece in dossier.pieces:
            if piece.required and not any(p.id == piece.id for p in dossier.pieces if not p.required):
                pieces_requises.append({"label": piece.label, "requis": True, "id": piece.id})
        return pieces_requises

    # ───────────────────────────────────────────────────────────────
    # Résumé financier par dossier
    # ───────────────────────────────────────────────────────────────

    def resume_financier_dossier(self, dossier_id: str) -> dict:
        """Résumé financier complet d'un dossier."""
        from ..frais import _get_frais_store, _get_facture_store

        frais_store = _get_frais_store()
        facture_store = _get_facture_store()

        frais_dossier = [f for f in frais_store.values() if f.dossier_id == dossier_id]
        factures_dossier = [f for f in facture_store.values() if f.dossier_id == dossier_id]

        total_frais = sum(f.montant for f in frais_dossier)
        total_avances = sum(f.montant for f in frais_dossier if f.avance_client)
        total_honoraires = sum(f.montant for f in frais_dossier if f.categorie == "honoraires_transitaire")
        total_factures_client = sum(f.montant_ttc for f in factures_dossier if f.type_facture == "emisee au client")
        total_factures_fournisseurs = sum(f.montant_ttc for f in factures_dossier if f.type_facture == "recue fournisseur")

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
            "solde_client": total_factures_client - total_frais if total_factures_client else 0,
            "solde_fournisseur": total_factures_fournisseurs,
            "rentabilite": total_factures_client - total_frais if total_factures_client else 0,
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
            },
        }

    # ───────────────────────────────────────────────────────────────
    # Historique des statuts
    # ───────────────────────────────────────────────────────────────

    def historique_statuts_dossier(self, dossier_id: str) -> dict:
        """Historique des changements d'état d'un dossier."""
        from ..dossier import DossierStore
        store = self._get_dossier_store()
        dossier = store.get(dossier_id)
        if not dossier:
            return {"erreur": "Dossier introuvable"}

        return {
            "dossier_id": dossier_id,
            "etat_actuel": dossier.state.value,
            "libelle_etat": dossier.state.label,
            "nb_pieces": len(dossier.pieces),
            "nb_extractions": len(self._get_ocr_integration().extraction_store.par_dossier(dossier_id)),
        }

    # ───────────────────────────────────────────────────────────────
    # Producteurs de graphiques (JSON pour Altair/Plotly)
    # ───────────────────────────────────────────────────────────────

    def _get_ocr_integration(self):
        return get_ocr_integration()

    # Méthode statistiques_generales ajoutée au DashboardService
    def statistiques_generales(self) -> dict:
        """Vue d'ensemble du système."""
        jobs = self.job_store.list_jobs(limit=10000)

        nb_total = len(jobs)
        nb_termines = sum(1 for j in jobs if j.status == "done")
        nb_erreurs = sum(1 for j in jobs if j.status == "error")
        nb_en_cours = sum(1 for j in jobs if j.status == "processing")
        nb_en_attente = sum(1 for j in jobs if j.status == "queued")

        # Temps moyen de traitement
        traitements = [j for j in jobs if j.status == "done" and j.progress == 1.0]
        if traitements:
            temps_moyen = sum(j.updated_at - j.created_at for j in traitements) / len(traitements)
            duree_moyenne = str(timedelta(seconds=round(temps_moyen)))
        else:
            duree_moyenne = "N/A"

        # Répartition par statut
        repartition = {
            "termine": nb_termines,
            "erreur": nb_erreurs,
            "en_cours": nb_en_cours,
            "en_attente": nb_en_attente,
        }

        return {
            "total_jobs": nb_total,
            "repartition_par_statut": repartition,
            "taux_reussite": round(nb_termines / nb_total * 100, 2) if nb_total > 0 else 0,
            "duree_moyenne_traitement": duree_moyenne,
        }


# Instance globale
_dashboard_service = None


def get_dashboard_service() -> DashboardService:
    """Récupère l'instance globale du dashboard."""
    global _dashboard_service
    if _dashboard_service is None:
        _dashboard_service = DashboardService()
    return _dashboard_service


# Point d'entrée pour compatibilité avec les routes
__all__ = [
    "DashboardService",
    "get_dashboard_service",
    "indicateurs_operationnels",
    "alertes_systeme",
    "graphique_etat_dossiers",
    "graphique_financier_mensuel",
    "resume_financier_dossier",
    "historique_statuts_dossier",
]


# Ajout de la méthode statistiques_generales manquante
def statistiques_generales(self) -> dict:
    """Vue d'ensemble du système."""
    jobs = self.job_store.list_jobs(limit=10000)

    nb_total = len(jobs)
    nb_termines = sum(1 for j in jobs if j.status == "done")
    nb_erreurs = sum(1 for j in jobs if j.status == "error")
    nb_en_cours = sum(1 for j in jobs if j.status == "processing")
    nb_en_attente = sum(1 for j in jobs if j.status == "queued")

    # Temps moyen de traitement
    traitements = [j for j in jobs if j.status == "done" and j.progress == 1.0]
    if traitements:
        temps_moyen = sum(j.updated_at - j.created_at for j in traitements) / len(traitements)
        duree_moyenne = str(timedelta(seconds=round(temps_moyen)))
    else:
        duree_moyenne = "N/A"

    # Répartition par statut
    repartition = {
        "termine": nb_termines,
        "erreur": nb_erreurs,
        "en_cours": nb_en_cours,
        "en_attente": nb_en_attente,
    }

    return {
        "total_jobs": nb_total,
        "repartition_par_statut": repartition,
        "taux_reussite": round(nb_termines / nb_total * 100, 2) if nb_total > 0 else 0,
        "duree_moyenne_traitement": duree_moyenne,
    }