"""Inventaire des seules sources déclarées d'un lot ; aucune acquisition réseau."""
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from .comparison import charger_lot
from .legal_comparison import charger_lot_code
from .search import ParamRechercheInvalide, _correspondances, _parametres, _rapport

NATURES_DOCUMENTS = ("code_original", "acte_modificatif", "compilation")


def inventorier_sources(repertoire: Path, type_lot: str, requete: str = "", source_id: str | None = None,
                        nature_document: str | None = None, limite: int = 20, decalage: int = 0) -> dict:
    if not isinstance(type_lot, str) or type_lot not in {"code", "tarif"}:
        raise ParamRechercheInvalide("Type explicite code ou tarif requis")
    if source_id is not None and (not isinstance(source_id, str) or not source_id.strip() or len(source_id) > 256
            or any(unicodedata.category(c) in {"Cc", "Cs"} for c in source_id)):
        raise ParamRechercheInvalide("ID de source exact non blanc, sans contrôle, de 256 caractères maximum requis")
    if nature_document is not None and (type_lot != "code" or not isinstance(nature_document, str)
                                        or nature_document not in NATURES_DOCUMENTS):
        raise ParamRechercheInvalide("Nature documentaire Code uniquement, valeur déclarée exacte requise")
    termes = _parametres(requete, limite, decalage, True)
    if any(unicodedata.category(c) == "Cs" for c in requete):
        raise ParamRechercheInvalide("Substitut Unicode isolé interdit")
    lot, rapport = (charger_lot_code if type_lot == "code" else charger_lot)(repertoire)
    sources = lot.documents if type_lot == "code" else [lot.source]
    compteurs = {s.id: Counter() for s in sources}
    if type_lot == "code":
        for article in lot.articles:
            compteurs[article.reference.source_id]["articles_reference_principale"] += 1
            for sid in {ref.source_id for ref in article.historique_modifications}:
                compteurs[sid]["articles_historique_declare"] += 1
        for relation in lot.relations:
            compteurs[relation.reference.source_id]["relations_reference_preuve"] += 1
        cles = ("articles_reference_principale", "articles_historique_declare", "relations_reference_preuve")
    else:
        cles = ("sections", "chapitres", "positions", "sous_positions", "subdivisions_nationales", "lignes", "mesures")
        for cle in cles:
            compteurs[lot.source.id][cle] = len(getattr(lot, cle))
    empreintes = defaultdict(list)
    for s in sorted(sources, key=lambda s: s.id):
        empreintes[s.sha256].append(s.id)
    resultats, total = [], 0
    for s in sorted(sources, key=lambda s: s.id):
        if ((source_id is not None and s.id != source_id)
                or (nature_document is not None and s.nature_document != nature_document)):
            continue
        preuves = _correspondances({c: getattr(s, c) for c in ("titre", "organisme", "version_source")}, termes)
        if preuves is None:
            continue
        if decalage <= total < decalage + limite:
            resultats.append({"source_declaree": s.model_dump(mode="json"), "champs_correspondants": preuves,
                              "compteurs_lot": {cle: compteurs[s.id][cle] for cle in cles},
                              "autres_sources_meme_sha256_dans_lot": [sid for sid in empreintes[s.sha256] if sid != s.id]})
        total += 1
    rep = _rapport("sources_documentaires", requete, termes, "metadonnees_normalisees_et_filtres_exacts",
                   {"source_id_exact": source_id, "nature_document": nature_document}, rapport,
                   total, resultats, limite, decalage)
    rep.update(type_lot=type_lot, total_sources_lot=len(sources), ordre="id_source_unicode_croissant",
               champs_recherches=["titre", "organisme", "version_source"], authenticite_etablie=False,
               utilisable_pour_calcul_douanier=False)
    rep["avertissements"].extend([
        "Inventaire des sources reçues dans un seul lot, sans découverte réseau ou corpus national exhaustif.",
        "URL officielle, nature, dates et empreinte sont déclarées : aucune authenticité ou applicabilité attestée.",
        "Empreintes identiques dans ce lot : constat binaire, pas identité juridique, traduction ou dédoublonnage automatique.",
        "Compteurs de rattachements déclarés seulement ; zéro article transcrit ne prouve pas un document vide.",
        "Recherche dans titre/organisme/version seulement, pas texte des articles, URL, empreinte ou localisateurs.",
    ])
    return rep
