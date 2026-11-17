"""Historique d'un document : ce qui lui est arrivé, dans l'ordre.

**Pourquoi.** Le journal d'audit (`logs/audit.log`) enregistre chaque étape —
création du job, fin de traitement, corrections de champs, rattachement à un
dossier — mais rien ne l'exposait par document. L'écran de révision affichait
l'état courant sans dire d'où il venait : impossible de savoir qui avait
corrigé un champ, ni quand.

La route lit le journal, ne garde que les entrées du job demandé et les
présente dans un vocabulaire lisible. Les événements inconnus ne sont pas
masqués : ils apparaissent avec leur nom brut, ce qui vaut mieux qu'un
historique troué.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request

from ..logging_setup import get_logger

log = get_logger("historique")

router = APIRouter(prefix="/api/jobs", tags=["historique"])

#: Traduction des événements d'audit en phrases. Le détail reste factuel :
#: on reprend les valeurs du journal, on n'en invente aucune.
LIBELLES: dict[str, tuple[str, str]] = {
    "job_created": ("Document reçu", "{filename} — {size} octets, profil {profile}"),
    "job_done": ("Analyse terminée", "{pages} page(s), confiance moyenne {mean_confidence:.0%}"),
    "job_error": ("Analyse en échec", "{erreur}"),
    "job_deduped": ("Doublon détecté", "{filename} : déjà traité (job {job_id})"),

    "field_correction_annulee": ("Correction annulée", "{field}"),
    "field_decisions_restored": ("Décisions restaurées", "{nombre} champ(s)"),
    "dossier_piece_added": ("Rattaché à un dossier", "{dossier_id} — {filename}"),
    "dossier_state_changed": ("Dossier changé d'état", "{dossier_id} : {etat}"),
    "dossier_created": ("Dossier créé", "{dossier_id}"),
    "document_classified": ("Document classé", "{category} (confiance : {confidence:.0%})"),
    "data_package_generated": ("Paquet de données généré", "{dossier_id}"),
}


def _detail(modele: str, entree: dict[str, Any]) -> str:
    """Remplit un gabarit avec les champs présents, sans lever d'exception."""
    try:
        return modele.format(**entree)
    except (KeyError, IndexError, ValueError):
        # Un champ manquant ne doit pas casser l'historique : on rend le nom
        # de l'événement, le lecteur saura qu'il manque un détail.
        return ""


def _phrase(entree: dict[str, Any]) -> tuple[str, str]:
    evenement = str(entree.get("event") or "")
    if evenement == "field_validated":
        # Le journal porte la valeur confirmée ou corrigée selon le geste ;
        # on affiche celle qui existe, sinon on dit simplement le champ.
        champ = entree.get("field") or "champ"
        valeur = entree.get("corrected") or entree.get("confirmed")
        return ("Champ corrigé", f"{champ} : {valeur}") if entree.get("corrected") \
            else ("Champ validé", f"{champ} : {valeur}" if valeur else f"{champ} confirmé")
    modele = LIBELLES.get(evenement)
    if modele is None:
        return evenement.replace("_", " ") or "événement", ""
    libelle, gabarit = modele
    return libelle, _detail(gabarit, entree)


def _horodatage(valeur: Any) -> str:
    try:
        return datetime.fromtimestamp(float(valeur)).strftime("%d/%m/%Y %H:%M:%S")
    except (TypeError, ValueError, OSError):
        return ""


@router.get("/{job_id}/historique")
def historique(job_id: str, request: Request) -> dict:
    """Événements du journal concernant ce document, du plus ancien au plus récent."""
    cfg = request.app.state.cfg
    chemin = cfg.log_dir / "audit.log"
    evenements: list[dict[str, Any]] = []
    ignores = 0
    if chemin.is_file():
        with chemin.open(encoding="utf-8") as journal:
            for ligne in journal:
                ligne = ligne.strip()
                if not ligne:
                    continue
                try:
                    entree = json.loads(ligne)
                except json.JSONDecodeError:
                    ignores += 1
                    continue
                if not isinstance(entree, dict) or entree.get("job_id") != job_id:
                    continue
                libelle, detail = _phrase(entree)
                evenements.append({
                    "horodatage": _horodatage(entree.get("ts")),
                    "ts": entree.get("ts"),
                    "evenement": entree.get("event"),
                    "libelle": libelle,
                    "detail": detail,
                    "acteur": entree.get("acteur") or "",
                })
    evenements.sort(key=lambda e: e.get("ts") or 0)

    store = getattr(request.app.state, "store", None)
    job_existe = bool(store and store.get(job_id))
    if evenements:
        vide = ""
    elif job_existe:
        vide = ("Ce document existe mais n'a aucun événement : il a été créé "
                "avant la mise en place du journal d'audit.")
    else:
        vide = (f"Document inconnu du journal et du magasin : rien à raconter "
                f"pour {job_id}.")
    return {
        "job_id": job_id,
        "total": len(evenements),
        "job_existe": job_existe,
        "lignes_illisibles": ignores,
        "vide": vide,
        "evenements": evenements,
    }
