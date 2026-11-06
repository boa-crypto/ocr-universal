"""Navigation des seuls chemins hiérarchiques transcrits, cloisonnés par source."""
import json
import unicodedata
from pathlib import Path

from .legal_comparison import charger_lot_code
from .models import NIVEAUX


class ParamArbreCodeInvalide(ValueError):
    """Sélecteur ou pagination invalide avant lecture du lot."""


def parcourir_code(repertoire: Path, source_id: str | None = None, chemin: str = "[]",
                   limite: int = 20, decalage: int = 0) -> dict:
    if source_id is not None and (not isinstance(source_id, str) or not source_id.strip() or len(source_id) > 256
                                 or any(unicodedata.category(c) == "Cc" for c in source_id)):
        raise ParamArbreCodeInvalide("ID source exact non blanc sans contrôle de 256 caractères maximum requis")
    if type(limite) is not int or not 1 <= limite <= 100 or type(decalage) is not int or not 0 <= decalage <= 1_000_000:
        raise ParamArbreCodeInvalide("Limite entière 1–100 et décalage entier 0–1000000 requis")
    try:
        if not isinstance(chemin, str) or len(chemin) > 8192:
            raise ValueError()
        def objet(paires):
            if len(dict(paires)) != len(paires):
                raise ValueError()
            return dict(paires)
        selection = json.loads(chemin, object_pairs_hook=objet)
        if not isinstance(selection, list) or len(selection) > len(NIVEAUX):
            raise ValueError()
        for n in selection:
            if (not isinstance(n, dict) or set(n) != {"niveau", "identifiant"}
                    or not isinstance(n["niveau"], str) or n["niveau"] not in NIVEAUX
                    or not isinstance(n["identifiant"], str) or len(n["identifiant"]) > 256
                    or any(unicodedata.category(c) == "Cs" for c in n["identifiant"])):
                raise ValueError()
        niveaux = [NIVEAUX.index(n["niveau"]) for n in selection]
        if niveaux != sorted(set(niveaux)) or (source_id is None and selection):
            raise ValueError()
    except (ValueError, TypeError, RecursionError) as exc:
        raise ParamArbreCodeInvalide("Chemin JSON ordonné de couples niveau/identifiant, source requise hors racine") from exc
    lot, rapport = charger_lot_code(repertoire)
    documents = {d.id: d for d in lot.documents}
    source = documents.get(source_id)
    correspondances, noeuds, versions = [], {}, []
    if source_id is None:
        compteurs = {}
        for a in lot.articles:
            compteurs[a.reference.source_id] = compteurs.get(a.reference.source_id, 0) + 1
        enfants = [{"type_noeud": "document", "source_id": d.id, "document_declare": d.model_dump(mode="json"),
                    "nombre_versions_transcrites": compteurs.get(d.id, 0)} for d in sorted(lot.documents, key=lambda d: d.id)]
        trouve = None
    else:
        for a in lot.articles:
            if a.reference.source_id != source_id:
                continue
            parcours = [{"niveau": n.niveau, "identifiant": n.identifiant} for n in a.hierarchie]
            if parcours[:len(selection)] != selection:
                continue
            correspondances.append(a)
            if len(parcours) == len(selection):
                versions.append({"type_noeud": "version_article", "version_declaree": a.model_dump(mode="json", include={
                    "id", "numero_article", "nature_version", "version_juridique", "reference", "validation_juridique"})})
            else:
                suivant = a.hierarchie[len(selection)]
                cle = (suivant.niveau, suivant.identifiant)
                if cle not in noeuds:
                    noeuds[cle] = {"titres": set(), "nombre": 0}
                noeuds[cle]["titres"].add(suivant.intitule)
                noeuds[cle]["nombre"] += 1
        enfants = [{"type_noeud": "niveau_declare", "chemin": [*selection, {"niveau": cle[0], "identifiant": cle[1]}],
                    "intitules_declares": sorted(v["titres"], key=lambda t: (t is not None, t or "")),
                    "nombre_versions_transcrites": v["nombre"]}
                   for cle, v in sorted(noeuds.items(), key=lambda kv: (NIVEAUX.index(kv[0][0]), kv[0][1]))]
        enfants += sorted(versions, key=lambda v: v["version_declaree"]["id"])
        trouve = source is not None and (not selection or bool(correspondances))
    page = enfants[decalage:decalage + limite]
    suivant = decalage + len(page)
    return {"type_rapport": "navigation_code_documentaire", "lecture_seule": True,
            "publication_active": False, "validation_juridique": "non_validee", "validation_humaine_requise": True,
            "completude_reglementaire": "non_etablie", "restitution_juridique_a_date": False,
            "transcription_verification": "non_verifiee", "archive": rapport["archive"],
            "source_id_exact": source_id, "document_declare": source.model_dump(mode="json") if source else None,
            "chemin_exact": selection, "parent_trouve": trouve,
            "identite_noeud": "source_id_et_chemin_complet_niveau_identifiant_sans_intitule",
            "ordre": "documents_id_ou_niveaux_declares_puis_identifiant_puis_versions_id",
            "total_enfants_declares": len(enfants), "limite": limite, "decalage": decalage,
            "decalage_suivant": suivant if suivant < len(enfants) else None, "enfants_declares": page,
            "avertissements": [
                "Chemins transcrits uniquement, pas reconstitution des niveaux absents ni hiérarchie nationale exhaustive.",
                "Sources séparées : numéros et titres communs ne fusionnent pas des documents ou des versions.",
                "Intitulés divergents conservés comme variantes déclarées, pas correction ou arbitrage.",
                "Une version se lit au terme de son chemin déclaré ; aucun niveau ajouté.",
                "Parent ou enfant absent ne prouve ni absence de droit, ni abrogation.",
                "Navigation technique sans filiation juridique, consolidation ou droit applicable à date.",
                "Empreintes/rejeu ne prouvent ni authenticité ni fidélité des transcriptions au PDF.",
            ]}
