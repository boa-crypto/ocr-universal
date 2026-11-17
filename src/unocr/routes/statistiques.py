"""Comparaison de périodes : « est-ce que ça bouge ? »

**Pourquoi.** L'écran Statistiques donne un état : 715 dossiers, 185 à valider.
Il ne répond pas à la question qu'on se pose vraiment — *est-ce plus ou moins
qu'avant ?* — et c'est précisément ce que l'exploitant doit savoir pour
arbitrer une charge de travail.

Deux fenêtres de même durée sont comparées : `[maintenant - jours, maintenant)`
contre `[maintenant - 2·jours, maintenant - jours)`. Les indicateurs sont
calculés sur les dates de création et de dernière modification disponibles.
Les états sont ceux du poste au moment de la lecture : ce n’est pas un
historique des transitions ni une mesure de la date exacte d’archivage.

Deux précautions de lecture :

* quand la période précédente est vide, la variation n'est pas « +∞ % » : elle
  est dite non calculable, avec le nombre brut ;
* les dates absentes ne sont pas comptées comme « anciennes » : elles sont
  signalées à part, pour que le total de l'écran s'explique.
"""

from __future__ import annotations

import math
import time
from typing import Any, Iterable

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api/stats", tags=["statistiques"])

#: États considérés comme « clos » côté métier, pour la lecture des sorties.
ETATS_ARCHIVES = {"archive"}
ETATS_A_REVOIR = {"revision_requise", "incomplet", "erreur_traitement"}


def _horodatage(valeur: Any) -> float | None:
    """Accepte un timestamp numérique (le format réel des dossiers)."""
    if valeur is None or valeur == "":
        return None
    try:
        nombre = float(valeur)
        return nombre if math.isfinite(nombre) else None
    except (TypeError, ValueError):
        return None


def _etat(dossier: dict[str, Any]) -> str:
    """État lisible : les modèles portent parfois une énumération."""
    valeur = dossier.get("state")
    return str(getattr(valeur, "value", valeur) or "")


def _compte(valeurs: Iterable[float | None], debut: float, fin: float) -> int:
    return sum(1 for v in valeurs if v is not None and debut <= v < fin)


def _variation(courant: int, precedent: int) -> tuple[int | None, str, str]:
    """(variation, tendance, lecture) — sans division par zéro déguisée."""
    if precedent == 0 and courant == 0:
        return 0, "stable", "aucune activité sur les deux périodes"
    if precedent == 0:
        return None, "hausse", f"{courant} sur la période, aucun équivalent avant"
    delta = courant - precedent
    pourcentage = round(100.0 * delta / precedent)
    if delta == 0:
        return 0, "stable", f"identique à la période précédente ({precedent})"
    tendance = "hausse" if delta > 0 else "baisse"
    signe = "+" if delta > 0 else ""
    return delta, tendance, f"{signe}{delta} ({signe}{pourcentage} %) vs {precedent}"


def comparer(dossiers: list[dict[str, Any]], jobs: list[Any],
             jours: int, maintenant: float | None = None) -> dict[str, Any]:
    """Compare deux fenêtres consécutives ; fonction pure, testable seule."""
    maintenant = time.time() if maintenant is None else maintenant
    seconde = 86400
    debut_courant = maintenant - jours * seconde
    debut_precedent = maintenant - 2 * jours * seconde

    creation = [_horodatage(d.get("created_at") or d.get("date_ouverture"))
                for d in dossiers]
    maj = [_horodatage(d.get("updated_at")) for d in dossiers]

    archives = [_horodatage(d.get("updated_at")) if _etat(d) in ETATS_ARCHIVES
                else None for d in dossiers]
    a_revoir = [_horodatage(d.get("created_at") or d.get("date_ouverture"))
                if _etat(d) in ETATS_A_REVOIR else None for d in dossiers]

    def champ(job: Any, nom: str) -> Any:
        valeur = job.get(nom) if isinstance(job, dict) else getattr(job, nom, None)
        return getattr(valeur, "value", valeur)       # énumérations → valeur

    fin_job = [_horodatage(champ(j, "updated_at"))
               if champ(j, "status") == "done" else None for j in jobs]
    erreurs_job = [_horodatage(champ(j, "updated_at"))
                   if champ(j, "status") == "error" else None for j in jobs]

    indicateurs_def = [
        ("Dossiers ouverts", creation, "date de création du dossier"),
        ("Dossiers archivés", archives, "dernière modification des dossiers actuellement archivés"),
        ("Documents traités", fin_job, "dernière modification des jobs actuellement réussis (done)"),
        ("Documents en erreur", erreurs_job, "dernier état du job"),
        ("Dossiers à revoir", a_revoir, "création des dossiers actuellement à revoir"),
        ("Dossiers mis à jour", maj, "dernière modification de chaque dossier"),
    ]

    lignes = []
    for libelle, valeurs, base in indicateurs_def:
        courant = _compte(valeurs, debut_courant, maintenant)
        precedent = _compte(valeurs, debut_precedent, debut_courant)
        delta, tendance, lecture = _variation(courant, precedent)
        lignes.append({
            "id": libelle.lower().replace(" ", "-"),
            "indicateur": libelle,
            "courant": courant,
            "precedent": precedent,
            "variation": delta,
            "tendance": tendance,
            "lecture": lecture,
            "base": base,
        })

    sans_date = sum(1 for v in creation if v is None)
    precedent_vide = all(ligne["precedent"] == 0 for ligne in lignes)
    return {
        "jours": jours,
        "fenetres": {
            "courant": [debut_courant, maintenant],
            "precedent": [debut_precedent, debut_courant],
        },
        "indicateurs": lignes,
        "total_dossiers": len(dossiers),
        "sans_date": sans_date,
        "avertissement": (
            "La période précédente ne contient aucune donnée sur ce poste : la "
            "comparaison n'a pas encore de point de repère. Les colonnes "
            "affichent donc le volume de la période courante, sans variation."
        ) if precedent_vide else "",
        "vide": (
            "Aucune activité datée sur les deux périodes : rien à comparer."
            if all(ligne["courant"] == 0 and ligne["precedent"] == 0 for ligne in lignes)
            else ""
        ),
    }


@router.get("/comparaison")
def comparaison(request: Request, jours: int = 30) -> dict:
    """Deux fenêtres consécutives de `jours` jours, sur les données réelles."""
    jours = max(1, min(365, int(jours)))
    dossiers: list[dict[str, Any]] = []
    try:
        from ..api import _dossiers as magasin_dossiers
        dossiers = [
            d.model_dump() if hasattr(d, "model_dump") else dict(d.__dict__)
            for d in magasin_dossiers.liste()
        ]
    except Exception as exc:
        raise HTTPException(503, "Statistiques indisponibles : lecture des dossiers impossible") from exc
    store = getattr(request.app.state, "store", None)
    if store is None:
        raise HTTPException(503, "Statistiques indisponibles : magasin des documents absent")
    try:
        # Une ligne sentinelle permet de signaler la limite, jamais de la cacher.
        jobs = list(store.list_jobs(limit=2001))
    except Exception as exc:
        raise HTTPException(503, "Statistiques indisponibles : lecture des documents impossible") from exc
    tronque = len(jobs) > 2000
    resultat = comparer(dossiers, jobs[:2000], jours)
    resultat["jobs_tronques"] = tronque
    resultat["jobs_analyses"] = min(len(jobs), 2000)
    resultat["limites"] = (
        "Photographie des états actuels, pas un historique des transitions : "
        "les dates utilisées sont précisées pour chaque ligne. "
        "Documents traités : uniquement les jobs actuellement réussis (done)."
    )
    if tronque:
        resultat["limites"] += " Attention : seuls les 2000 documents les plus récents sont analysés."
    return resultat
