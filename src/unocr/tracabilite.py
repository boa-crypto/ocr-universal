"""Archivage et traçabilité du dossier (étape 15).

**Archivage.** Marquer un dossier comme archivé. Ce n'est **pas** une
suppression : les documents, les pièces, le formulaire et le journal restent
en place. Archiver verrouille un dossier dans un état final lisible — il ne
disparaît pas.

**Traçabilité.** Rassembler, pour un dossier, la suite des événements qui le
concernent : création, traitement de chaque document, classification,
validations humaines, reprises après panne, générations de paquet.

**Ce que ce module ne prétend pas.** Le journal applicatif n'est pas une
preuve inviolable. Il est écrit par l'application, dans un fichier texte, sur
la même machine : un administrateur peut le modifier, et rien ici ne le rend
résistant à l'altération. La fonction `avertissement_tracabilite()` le dit
explicitement, et l'interface l'affiche à côté de la trace. Présenter ce
journal comme une preuve juridiquement opposable serait un mensonge.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .storage import audit

# ─────────────────────────── archivage ───────────────────────────

#: ce que l'archivage garantit — et ce qu'il ne garantit pas
GARANTIES_ARCHIVAGE = (
    "Les documents originaux ne sont ni modifiés ni supprimés.",
    "Les valeurs extraites et les corrections humaines sont conservées.",
    "Le journal d'audit reste lisible et n'est pas purgé.",
    "Le dossier reste consultable : l'archivage est un état, pas une mise "
    "au placard.",
)

LIMITES_ARCHIVAGE = (
    "L'archivage ne rend rien inaltérable : le journal reste un fichier "
    "modifiable par quiconque a accès à la machine.",
    "L'archivage ne constitue pas une preuve juridique opposable.",
    "L'archivage ne déclenche aucune conservation légale automatique.",
)


def archiver_dossier(store, dossier_id: str, motif: str = "",
                     acteur: str = "utilisateur") -> dict:
    """Archive un dossier : état final explicite, aucune donnée supprimée.

    Renvoie la synthèse du dossier. Lève `KeyError` si le dossier n'existe
    pas, `ValueError` si l'archivage est refusé.
    """
    dossier = store.get(dossier_id)
    if dossier is None:
        raise KeyError(f"dossier introuvable : {dossier_id}")

    if dossier.state.value == "archive":
        raise ValueError("ce dossier est déjà archivé")

    # un dossier en erreur de traitement peut être archivé, mais on le dit :
    # l'archivage d'un dossier incomplet ne le rend pas complet
    avertissements = []
    manquantes = store.pieces_manquantes(dossier)
    if manquantes:
        avertissements.append(
            f"{len(manquantes)} pièce(s) attendue(s) par le profil sont "
            "absentes : l'archivage ne les crée pas.")

    from .dossier import DossierState

    dossier = store.forcer_etat(
        dossier_id, DossierState.ARCHIVE, acteur=acteur,
        motif=motif or "archivage depuis l'interface")
    audit(store.log_dir, "dossier_archived", dossier_id=dossier_id,
          motif=motif, acteur=acteur, avertissements=len(avertissements))

    synthese = store.synthese(dossier)
    synthese["avertissements_archivage"] = avertissements
    return synthese


# ─────────────────────────── traçabilité ───────────────────────────

#: événements du journal qui concernent le parcours d'un document
EVENEMENTS_DOCUMENT = (
    "job_created", "job_done", "job_error", "job_deduped",
    "document_classified", "field_validated", "field_decisions_restored",
)

#: événements qui concernent le dossier ou ses sorties
EVENEMENTS_DOSSIER = (
    "dossier_created", "dossier_piece_added", "dossier_piece_removed",
    "dossier_piece_recategorized", "dossier_deleted",
    # « state_changed » = état déduit par le système ;
    # « state_forced »  = état posé explicitement par un humain
    "dossier_state_changed", "dossier_state_forced", "dossier_archived",
    "dossier_form_saved", "dossier_form_deleted",
    "data_package_generated", "dossier_transmitted",
)

#: libellés lisibles, pour qu'une trace se lise sans connaître le code
LIBELLES_EVENEMENT = {
    "job_created": "Document reçu",
    "job_done": "Document traité",
    "job_error": "Traitement en échec",
    "job_deduped": "Doublon détecté à l'import",
    "document_classified": "Document classé",
    "field_validated": "Champ validé par un humain",
    "field_decisions_restored": "Décisions humaines restaurées après reprise",
    "dossier_created": "Dossier créé",
    "dossier_piece_added": "Pièce ajoutée au dossier",
    "dossier_piece_removed": "Pièce retirée du dossier",
    "dossier_deleted": "Dossier supprimé",
    "dossier_state_changed": "État du dossier recalculé",
    "dossier_state_forced": "État du dossier forcé par un humain",
    "dossier_piece_recategorized": "Pièce reclassée",
    "dossier_archived": "Dossier archivé",
    "dossier_form_saved": "Formulaire enregistré",
    "dossier_form_deleted": "Formulaire supprimé",
    "data_package_generated": "Paquet de données généré",
    "dossier_transmitted": "Dossier transmis à un connecteur",
}


@dataclass
class Entree:
    """Une ligne de trace, rendue lisible."""
    ts: float
    event: str
    job_id: str = ""
    dossier_id: str = ""
    detail: dict[str, Any] = field(default_factory=dict)

    @property
    def libelle(self) -> str:
        return LIBELLES_EVENEMENT.get(self.event, self.event)

    def resume(self) -> str:
        """Une phrase courte décrivant l'événement, sans rien inventer."""
        d = self.detail
        if self.event == "document_classified":
            conf = d.get("confidence")
            return (f"classé « {d.get('category', '?')} »"
                    + (f" (confiance {conf:.2f})" if isinstance(conf, (int, float)) else "")
                    + (" — à confirmer" if d.get("needs_review") else ""))
        if self.event == "field_validated":
            return f"champ « {d.get('field', '?')} » validé"
        if self.event == "field_decisions_restored":
            champs = d.get("fields") or []
            return (f"{len(champs)} décision(s) humaine(s) restaurée(s) "
                    f"à la reprise n°{d.get('attempt', '?')}")
        if self.event == "data_package_generated":
            return (f"{d.get('fichier', '?')} — {d.get('documents', '?')} "
                    "document(s)")
        if self.event == "dossier_piece_added":
            return f"pièce « {d.get('filename', d.get('job_id', '?'))} » ajoutée"
        if self.event == "dossier_piece_removed":
            return f"pièce « {d.get('job_id', '?')} » retirée"
        if self.event in ("dossier_state_changed", "dossier_state_forced"):
            fleche = f"{d.get('from', '?')} → {d.get('to', '?')}"
            if self.event == "dossier_state_forced":
                fleche += " (posé par un humain)"
            if d.get("motif"):
                fleche += f" — {d['motif']}"
            return fleche
        if self.event == "dossier_archived":
            return "dossier archivé" + (f" — {d['motif']}" if d.get("motif") else "")
        if self.event == "job_error":
            return f"échec : {d.get('error', '?')}"
        if self.event == "job_deduped":
            return "déjà traité : réutilisation du résultat existant"
        if self.event == "job_done":
            pages = d.get("pages")
            return (f"{pages} page(s) traitée(s)" if pages is not None
                    else "traitement terminé")
        if self.event == "dossier_created":
            return f"profil « {d.get('profile', '?')} »"
        return ""

    def as_dict(self) -> dict[str, Any]:
        return {"ts": self.ts, "event": self.event, "libelle": self.libelle,
                "job_id": self.job_id, "dossier_id": self.dossier_id,
                "resume": self.resume(), "detail": self.detail}


def lit_journal(log_dir: Path) -> list[dict]:
    """Lit le journal d'audit. Renvoie les lignes lisibles, dans l'ordre."""
    path = Path(log_dir) / "audit.log"
    if not path.is_file():
        return []
    entrees = []
    for ligne in path.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if not ligne:
            continue
        try:
            entrees.append(json.loads(ligne))
        except ValueError:
            continue        # une ligne illisible ne fait pas échouer la trace
    return entrees


def trace_dossier(store, dossier_id: str, limite: int = 200) -> list[Entree]:
    """Trace complète d'un dossier, des événements les plus anciens aux récents.

    Remonte les événements du dossier lui-même **et** ceux de chaque document
    qu'il contient. Un document retiré du dossier n'apparaît plus : sa trace
    reste dans le journal global, mais elle ne concerne plus ce dossier.
    """
    dossier = store.get(dossier_id)
    if dossier is None:
        raise KeyError(f"dossier introuvable : {dossier_id}")
    job_ids = {p.job_id for p in dossier.pieces}

    sortie: list[Entree] = []
    for brute in lit_journal(store.log_dir):
        event = brute.get("event", "")
        job_id = brute.get("job_id", "")
        did = brute.get("dossier_id", "")
        # Un dossier_id explicite l'emporte sur le job_id : un même document
        # peut être joint à plusieurs dossiers, mais l'action « ajouté au
        # dossier X » appartient à X seul. Sans cette garde, la trace d'un
        # dossier se remplirait des rattachements du même document ailleurs.
        if did:
            if did != dossier_id:
                continue
        elif job_id not in job_ids:
            continue
        if event not in EVENEMENTS_DOCUMENT and event not in EVENEMENTS_DOSSIER:
            continue
        sortie.append(Entree(
            ts=float(brute.get("ts") or 0.0), event=event, job_id=job_id,
            dossier_id=did,
            detail={k: v for k, v in brute.items()
                    if k not in ("ts", "event", "job_id", "dossier_id")},
        ))
    sortie.sort(key=lambda e: e.ts)
    return sortie[-limite:] if limite else sortie


def synthese_tracabilite(store, dossier_id: str) -> dict:
    """Trace d'un dossier + compteurs + l'avertissement obligatoire."""
    entrees = trace_dossier(store, dossier_id)
    dossier = store.get(dossier_id)
    compteurs: dict[str, int] = {}
    for e in entrees:
        compteurs[e.event] = compteurs.get(e.event, 0) + 1
    return {
        "dossier_id": dossier_id,
        "etat": dossier.state.value if dossier else None,
        "entrees": [e.as_dict() for e in entrees],
        "compteurs": compteurs,
        "total": len(entrees),
        # ce que la trace garantit, et ce qu'elle ne garantit pas
        "avertissement": AVERTISSEMENT_TRACABILITE,
        "garanties": list(GARANTIES_ARCHIVAGE),
        "limites": list(LIMITES_ARCHIVAGE),
    }


#: affiché à côté de toute trace, sans exception
AVERTISSEMENT_TRACABILITE = (
    "Journal applicatif, pas preuve inviolable : il est écrit par "
    "l'application dans un fichier texte sur cette machine. Quiconque a un "
    "accès administrateur peut le modifier, et rien ici ne le rend résistant "
    "à l'altération."
)
