"""Rejeu de deux archives explicitement ordonnées, jamais fusion ou droit à date."""
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from .article_diff import comparer_versions_article
from .comparison import comparer_lots
from .export_replay import _constat_rejeu, _parametres_export
from .legal_comparison import comparer_lots_code
from .replay_pins import (
    constat_empreintes,
    valider_empreinte,
    verifier_manifeste,
    verifier_manifeste_rejoue,
    verifier_octets,
)
from .review_export import ExportRefuse, _lire_export, analyser_export
from .tariff_measures import juxtaposer_tarif_mesures
from .tariff_pair import juxtaposer_fiches_tarifaires


def verifier_rejeu_paire(fichier: Path, avant: Path, apres: Path, avant_id: str, apres_id: str,
                         type_avant: str, type_apres: str, *, sha256_export_attendu=None,
                         manifest_avant_attendu=None, manifest_apres_attendu=None) -> dict:
    for identite in (avant_id,apres_id):
        if not isinstance(identite,str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}",identite) is None:
            raise ExportRefuse("Deux identités explicites de lots requises")
    for t in (type_avant,type_apres):
        if not isinstance(t,str) or t not in {"code","tarif","mesures"}:
            raise ExportRefuse("Deux types explicites de lots requis")
    if avant_id == apres_id and (avant != apres or type_avant != type_apres):
        raise ExportRefuse("Même identité associée à des dossiers ou types différents")
    for reference in (sha256_export_attendu,manifest_avant_attendu,manifest_apres_attendu):
        valider_empreinte(reference)
    contenu = _lire_export(fichier)
    verifier_octets(contenu,sha256_export_attendu)
    controle = analyser_export(contenu)
    objet = json.loads(contenu)
    route = urlsplit(objet["requete_relative"]).path
    prefixe = "/api/v1/customs-review/"
    nom = route[len(prefixe):] if route.startswith(prefixe) else ""
    types = (type_avant,type_apres)
    autorises = {
        "diff":{"avant","apres"},
        "article-diff":{"avant","apres","avant_id","apres_id","field","limit","offset_avant","offset_apres"},
        "tariff-compare":{"avant","apres","code10","before_limit","before_offset","after_limit","after_offset"},
        "tariff-measures":{"tarif","mesures","code10","tariff_limit","tariff_offset","measures_limit","measures_offset"}}
    compatibles = ((nom == "diff" and types in {("code","code"),("tarif","tarif")}) or
                   (nom == "article-diff" and types == ("code","code")) or
                   (nom == "tariff-compare" and types == ("tarif","tarif")) or
                   (nom == "tariff-measures" and types == ("tarif","mesures")))
    if not compatibles:
        raise ExportRefuse("Route de comparaison incompatible avec les types explicites")
    nombres = {"limit":("limite",5),"offset_avant":("decalage_avant",8),"offset_apres":("decalage_apres",8)} if nom == "article-diff" else {
        "before_limit":("limite_avant",3),"before_offset":("decalage_avant",7),
        "after_limit":("limite_apres",3),"after_offset":("decalage_apres",7),
        "tariff_limit":("limite_tarif",3),"tariff_offset":("decalage_tarif",7),
        "measures_limit":("limite_mesures",3),"measures_offset":("decalage_mesures",7)}
    params = _parametres_export(objet["requete_relative"],avant_id,autorises=autorises[nom],numeriques=nombres,chemin_attendu=prefixe+nom)
    roles = ("tarif","mesures") if nom == "tariff-measures" else ("avant","apres")
    if params.pop(roles[0],None) != avant_id or params.pop(roles[1],None) != apres_id:
        raise ExportRefuse("Identités et ordre de comparaison incompatibles")
    if nom in {"tariff-compare","tariff-measures"} and "code10" not in params:
        raise ExportRefuse("Code10 exact explicite requis")
    if nom == "article-diff":
        if not {"avant_id","apres_id"} <= params.keys():
            raise ExportRefuse("Deux IDs article explicites requis")
        if "field" in params:
            params["champ"] = params.pop("field")
    verifier_manifeste(avant,manifest_avant_attendu)
    verifier_manifeste(apres,manifest_apres_attendu)
    try:
        if nom == "diff":
            reproduit = (comparer_lots_code if type_avant == "code" else comparer_lots)(avant,apres)
        elif nom == "article-diff":
            reproduit = comparer_versions_article(avant,repertoire_apres=apres,**params)
        elif nom == "tariff-compare":
            reproduit = juxtaposer_fiches_tarifaires(avant,apres,**params)
        else:
            reproduit = juxtaposer_tarif_mesures(avant,apres,**params)
    except (OSError,ValueError,KeyError,TypeError,RecursionError):
        raise ExportRefuse("Archives ou paramètres de comparaison incompatibles") from None
    if nom != "diff":
        reproduit["lots_exacts"] = dict(zip(roles,(avant_id,apres_id)))
    verifier_manifeste_rejoue(reproduit["archives"]["avant"]["manifest_sha256"],manifest_avant_attendu)
    verifier_manifeste_rejoue(reproduit["archives"]["apres"]["manifest_sha256"],manifest_apres_attendu)
    r = _constat_rejeu(controle,objet["resultat"],reproduit)
    r["empreintes_attendues"] = constat_empreintes(sha256_export_attendu,{"avant":manifest_avant_attendu,"apres":manifest_apres_attendu})
    r.update(type_controle="rejeu_local_export_deux_archives",types_lots_explicites={"avant":type_avant,"apres":type_apres})
    return r
