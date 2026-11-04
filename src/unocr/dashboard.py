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

import time
from datetime import datetime, timedelta

from unocr.config import get_config
from unocr.logging_setup import get_logger
from unocr.ocr_integration import get_ocr_integration

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

    def indicateurs_operationnels(self, frais_store: dict | None = None,
                                  facture_store: dict | None = None) -> dict:
        """15 indicateurs clés pour le pilotage maritime.

        Les stores de frais sont injectés par la couche HTTP (ils vivent dans
        `app.state`) : le service ne peut pas les atteindre seul.
        """
        frais_store = frais_store or {}
        facture_store = facture_store or {}
        jobs = self.job_store.list_jobs(limit=10000)
        dossiers = self._get_dossier_store().liste()

        nb_total = len(jobs)
        nb_termines = sum(1 for j in jobs if j.status == "done")
        nb_erreurs = sum(1 for j in jobs if j.status == "error")
        nb_en_cours = sum(1 for j in jobs if j.status == "processing")
        nb_en_attente = sum(1 for j in jobs if j.status == "queued")

        # Taux de réussite global
        taux_reussite = round(nb_termines / nb_total * 100, 2) if nb_total > 0 else 0

        # Confiance, anomalies et codes-barres : un seul passage sur les
        # résultats des jobs terminés (les relire trois fois coûterait cher).
        terminés = [j for j in jobs if j.status == "done"]
        confiances = []
        jobs_avec_anomalie = 0
        comptes_barcodes: dict[str, int] = {}
        for j in terminés:
            result = self.job_store.load_result(j.id)
            if not result:
                continue
            qualite = (result.get("quality") or {}).get("global")
            if qualite is not None:
                confiances.append(qualite)
            anomalie = bool(result.get("warnings"))
            for champ in (result.get("fields") or {}).values():
                if isinstance(champ, dict) and champ.get("status") in ("invalid", "ambiguous"):
                    anomalie = True
            if anomalie:
                jobs_avec_anomalie += 1
            for code in result.get("barcodes") or []:
                valeur = code.get("text") if isinstance(code, dict) else code
                if valeur:
                    comptes_barcodes[str(valeur)] = comptes_barcodes.get(str(valeur), 0) + 1
        confiance_moyenne = round(sum(confiances) / len(confiances) * 100, 2) if confiances else 0
        taux_anomalies = round(jobs_avec_anomalie / max(1, nb_termines) * 100, 2)
        top_barcodes = sorted(comptes_barcodes.items(), key=lambda x: x[1], reverse=True)[:10]

        # Répartition par état
        repartition_etats = {}
        for j in jobs:
            etat = j.status.value
            repartition_etats[etat] = repartition_etats.get(etat, 0) + 1

        # Frais totaux et avances
        total_frais = sum(f.montant for f in frais_store.values())
        total_avances = sum(f.montant for f in frais_store.values() if f.avance_client)

        # Taux de recouvrement
        frais_payes = sum(f.montant for f in frais_store.values() if f.statut_paiement == "paye")
        taux_recouvrement = round(frais_payes / total_frais * 100, 2) if total_frais > 0 else 0

        # Dokrs par client (top 10)
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

        # Dossiers par gestionnaire
        gestionnaires_stats = {}
        for dossier in dossiers:
            mg = dossier.gestionnaire or "non assigné"
            gestionnaires_stats[mg] = gestionnaires_stats.get(mg, 0) + 1
        top_gestionnaires = sorted(gestionnaires_stats.items(), key=lambda x: x[1], reverse=True)[:10]

        # Taux de complétion des pièces attendues par le profil du dossier
        pieces_requises = 0
        pieces_presentes = 0
        for dossier in dossiers:
            attendues = self._pieces_attendues_dossier(dossier)
            requises = [a for a in attendues if a.required]
            manquantes = {m["id"] for m in self._pieces_manquantes_dossier(dossier)}
            pieces_requises += len(requises)
            pieces_presentes += len([a for a in requises if a.category not in manquantes])
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

        # Dossiers en retard (plus de 7 jours sans mouvement, hors circuit clos)
        from .dossier import DossierState

        maintenant = time.time()
        retardataires = [
            d for d in dossiers
            if d.state not in (DossierState.EXPORTE, DossierState.ARCHIVE)
            and (maintenant - float(d.updated_at or 0)) > 7 * 86400
        ]
        en_retard_7_jours = len(retardataires)
        taux_retard = round(en_retard_7_jours / max(1, len(dossiers)) * 100, 2)
        cout_moyen_fret = round(
            sum(float(d.frais_associes or 0) for d in dossiers) / max(1, len(dossiers)), 2
        )

        # Moyenne de confiance moteur
        integrations = self._get_ocr_integration()
        confiances_moteur = integrations.stats().get("moyenne_confiance", 0) if hasattr(integrations, 'stats') else 0

        return {
            # `total_jobs` est le nom attendu par l'UI (cf. updateKPIs) :
            # `nb_total` reste exposé pour les autres consommateurs.
            "total_jobs": nb_total,
            "nb_total": nb_total,
            "nb_termines": nb_termines,
            "nb_erreurs": nb_erreurs,
            "nb_en_cours": nb_en_cours,
            "nb_en_attente": nb_en_attente,
            "taux_reussite": taux_reussite,
            "confiance_moyenne": confiance_moyenne,
            "repartition_etats": repartition_etats,
            "repartition_par_etat": repartition_etats,
            "taux_anomalies": taux_anomalies,
            "en_retard_7_jours": en_retard_7_jours,
            "taux_retard": taux_retard,
            "cout_moyen_fret": cout_moyen_fret,
            "pieces_requises": pieces_requises,
            "pieces_presentes": pieces_presentes,
            "statut_documentaire": statut_doc_stats,
            "type_operation": type_op_stats,
            "top_barcodes": top_barcodes,
            "total_frais": total_frais,
            "total_avances": total_avances,
            "taux_recouvrement": taux_recouvrement,
            "top_clients": top_clients,
            "top_ports": top_ports,
            "top_gestionnaires": top_gestionnaires,
            "taux_completion_pieces": taux_completion_pieces,
            "type_op_stats": type_op_stats,
            "prioritaires_stats": prioritaires_stats,
            "top_prioritaires": top_prioritaires,
            "confiance_moteur": confiances_moteur,
        }

    # ───────────────────────────────────────────────────────────────
    # Graphiques (JSON pour Altair/Plotly)
    # ───────────────────────────────────────────────────────────────

    def graphique_etat_dossiers(self) -> dict:
        """Graphique: répartition des dossiers par état."""
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

    def graphique_financier_mensuel(self, mois_debut: int = None, mois_fin: int = None,
                                    frais_store: dict | None = None,
                                    facture_store: dict | None = None) -> dict:
        """Graphique: évolution financière mensuelle."""
        frais_store = frais_store or {}
        facture_store = facture_store or {}

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
            except (AttributeError, TypeError, ValueError, IndexError):
                pass

        for f in facture_store.values():
            try:
                date_parts = f.date_facture.split("/") if "/" in f.date_facture else f.date_facture.split("-")
                if len(date_parts) >= 1:
                    m = int(date_parts[0]) if "/" not in f.date_facture else int(date_parts[1])
                    mensuels[m] = mensuels.get(m, 0) + f.montant_ttc
            except (AttributeError, TypeError, ValueError, IndexError):
                pass

        # Trier par mois
        series = []
        for m in range(max(1, mois_debut), min(12, mois_fin) + 1):
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
    # Graphiques complémentaires (ports, clients, fret, anomalies, réussite)
    # ───────────────────────────────────────────────────────────────

    def graphique_repartition_par_port(self) -> dict:
        """Répartition des dossiers par port de chargement (repli destination)."""
        comptes: dict[str, int] = {}
        for dossier in self._get_dossier_store().liste():
            port = (dossier.port_chargement or dossier.port_destination or "").strip()
            port = port or "non défini"
            comptes[port] = comptes.get(port, 0) + 1
        series = [{"name": nom, "y": nb} for nom, nb in
                  sorted(comptes.items(), key=lambda x: x[1], reverse=True)[:10]]
        return {"type": "pie", "titre": "Répartition par port", "series": series}

    def graphique_repartition_par_client(self, limite: int = 10) -> dict:
        """Top clients par nombre de dossiers."""
        comptes: dict[str, int] = {}
        for dossier in self._get_dossier_store().liste():
            client = (dossier.client_importateur or "").strip() or "inconnu"
            comptes[client] = comptes.get(client, 0) + 1
        series = [{"name": nom, "y": nb} for nom, nb in
                  sorted(comptes.items(), key=lambda x: x[1], reverse=True)[:max(1, limite)]]
        return {"type": "doughnut", "titre": "Top clients", "series": series}

    def graphique_fret_par_gestionnaire(self) -> dict:
        """Somme des frais associés par gestionnaire de dossier."""
        totaux: dict[str, float] = {}
        for dossier in self._get_dossier_store().liste():
            gestionnaire = (dossier.gestionnaire or "").strip() or "non assigné"
            totaux[gestionnaire] = totaux.get(gestionnaire, 0.0) + float(
                dossier.frais_associes or 0.0)
        series = [{"name": nom, "y": round(montant, 2)} for nom, montant in
                  sorted(totaux.items(), key=lambda x: x[1], reverse=True)]
        return {"type": "bar", "titre": "Frais associés par gestionnaire",
                "series": series}

    def graphique_anomalies_par_type(self) -> dict:
        """Avertissements d'extraction et champs à réviser, par type.

        Les avertissements sont produits par le pipeline ; les champs
        `invalid` / `ambiguous` sont les anomalies réellement constatées sur les
        documents traités. Rien n'est inventé : sans donnée, la série est vide.
        """
        comptes: dict[str, int] = {}
        for job in self.job_store.list_jobs(limit=200):
            resultat = self.job_store.load_result(job.id)
            if not resultat:
                continue
            for avertissement in resultat.get("warnings") or []:
                libelle = str(avertissement).strip() or "avertissement"
                comptes[libelle] = comptes.get(libelle, 0) + 1
            for champ in (resultat.get("fields") or {}).values():
                statut = champ.get("status") if isinstance(champ, dict) else None
                if statut in ("invalid", "ambiguous"):
                    libelle = "champ invalide" if statut == "invalid" else "champ ambigu"
                    comptes[libelle] = comptes.get(libelle, 0) + 1
        series = [{"name": nom[:70], "y": nb} for nom, nb in
                  sorted(comptes.items(), key=lambda x: x[1], reverse=True)[:10]]
        return {"type": "bar", "titre": "Anomalies par type", "series": series}

    def graphique_taux_reussite_par_mois(self, mois_debut: int = None,
                                         mois_fin: int = None) -> dict:
        """Taux de réussite des traitements, mois par mois."""
        maintenant = datetime.now()
        if mois_fin is None:
            mois_fin = maintenant.month
        if mois_debut is None:
            mois_debut = max(1, mois_fin - 5)

        par_mois: dict[tuple[int, int], list[int]] = {}
        for job in self.job_store.list_jobs(limit=10000):
            cree = datetime.fromtimestamp(getattr(job, "created_at", 0) or 0)
            if not (mois_debut <= cree.month <= mois_fin):
                continue
            cle = (cree.year, cree.month)
            compte = par_mois.setdefault(cle, [0, 0])
            compte[0] += 1
            if job.status == "done":
                compte[1] += 1

        series = []
        for (annee, mois) in sorted(par_mois):
            total, reussis = par_mois[(annee, mois)]
            taux = round(reussis / total * 100, 2) if total else 0.0
            series.append({"name": f"{mois:02d}/{annee}", "y": taux,
                           "total": total, "taux": taux})
        return {"type": "bar", "titre": "Taux de réussite par mois",
                "series": series}

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
                            # `datetime` est importé au niveau du module : un
                            # import local ici le rendait local à la fonction
                            # et cassait `maintenant = datetime.now()` plus haut.
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
    def _pieces_attendues_dossier(dossier) -> list:
        """Pièces attendues par le profil du dossier (liste éventuellement vide)."""
        from .dossier import PROFILS_DOSSIER

        profil = PROFILS_DOSSIER.get(getattr(dossier, "profile", ""))
        return list(profil.pieces) if profil else []

    @classmethod
    def _pieces_manquantes_dossier(cls, dossier) -> list:
        """Pièces attendues absentes : on compare les **catégories** du profil
        aux catégories réellement rattachées au dossier.

        L'ancienne version cherchait `piece.required` sur les pièces jointes,
        attribut qui n'existe pas : chaque appel levait une AttributeError.
        """
        categories_presentes = {
            getattr(p, "category", "") for p in getattr(dossier, "pieces", [])
        }
        manquantes = []
        for attendue in cls._pieces_attendues_dossier(dossier):
            if attendue.category and attendue.category not in categories_presentes:
                manquantes.append({
                    "label": attendue.label,
                    "requis": bool(attendue.required),
                    "id": attendue.category,
                })
        return manquantes

    # ───────────────────────────────────────────────────────────────
    # Résumé financier par dossier
    # ───────────────────────────────────────────────────────────────

    def resume_financier_dossier(self, dossier_id: str,
                                 frais_store: dict | None = None,
                                 facture_store: dict | None = None) -> dict:
        """Résumé financier complet d'un dossier.

        `dossier_id == "__synthese__"` agrège l'ensemble des frais (utilisé par
        l'indicateur de santé financière globale).
        """
        frais_store = frais_store or {}
        facture_store = facture_store or {}

        synthese = dossier_id == "__synthese__"
        frais_dossier = [f for f in frais_store.values()
                         if synthese or f.dossier_id == dossier_id]
        factures_dossier = [f for f in facture_store.values()
                            if synthese or f.dossier_id == dossier_id]

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
        store = self._get_dossier_store()
        dossier = store.get(dossier_id)
        if not dossier:
            return {"erreur": "Dossier introuvable"}

        return {
            "dossier_id": dossier_id,
            "etat_actuel": dossier.state.value,
            "libelle_etat": store._LABELS_ETATS.get(dossier.state, dossier.state.value),
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


__all__ = ["DashboardService", "get_dashboard_service"]
