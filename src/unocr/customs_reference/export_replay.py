"""Rejeu local d'un export de critères ; aucune identité officielle ou signature."""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

from .review_export import ExportRefuse, _lire_export, analyser_export
from .tariff_criteria import CRITERES, rechercher_tarif_criteres


def _parametres_export(requete, lot_id):
    url = urlsplit(requete)
    if url.scheme or url.netloc or url.fragment or url.path != f"/api/v1/customs-review/lots/{lot_id}/tariff-criteria":
        raise ExportRefuse("Route de critères et identité de lot explicites requises")
    if re.search(r"%(?![0-9a-fA-F]{2})", url.query):
        raise ExportRefuse("Encodage de requête incompatible")
    try:
        paires = parse_qsl(url.query,keep_blank_values=True,strict_parsing=True,
                           max_num_fields=9,encoding="utf-8",errors="strict")
    except ValueError:
        raise ExportRefuse("Requête de critères incompatible") from None
    params = {}
    autorises = {*CRITERES,"code_prefix","match_mode","limit","offset"}
    for cle,valeur in paires:
        if cle not in autorises or cle in params:
            raise ExportRefuse("Paramètre inconnu ou dupliqué")
        params[cle] = valeur
    for cle in ("limit","offset"):
        if cle in params:
            if re.fullmatch(r"[0-9]{1,7}",params[cle]) is None:
                raise ExportRefuse("Pagination décimale ASCII explicite requise")
            params["limite" if cle == "limit" else "decalage"] = int(params.pop(cle))
    return params


def _canonique(objet):
    # Contrairement à l'égalité Python, distingue 0 de false et 1 de 1.0.
    return json.dumps(objet,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")


def verifier_rejeu_criteres(chemin_export: Path, repertoire: Path, lot_id: str) -> dict:
    if not isinstance(lot_id,str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}",lot_id) is None:
        raise ExportRefuse("Identité locale de lot explicite requise")
    contenu = _lire_export(chemin_export)
    controle = analyser_export(contenu)
    # Un seul fichier lu ; le contenu déjà contrôlé (doublons, bornes et Unicode)
    # est reparsé sans rouvrir le chemin. Aucun paramètre n'est un chemin local.
    objet = json.loads(contenu)
    params = _parametres_export(objet["requete_relative"],lot_id)
    try:
        reproduit = rechercher_tarif_criteres(repertoire,**params)
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        raise ExportRefuse("Archive fournie ou paramètres de recherche incompatibles") from None
    manifeste = reproduit["archive"]["manifest_sha256"]
    manifeste_identique = controle["manifestes_declares"] == [manifeste]
    original = _canonique(objet["resultat"])
    rejeu = _canonique(reproduit)
    identique = original == rejeu
    return {
        "type_controle":"rejeu_local_export_criteres_tarifaires",
        "statut":"rejeu_identique" if identique else "rejeu_different",
        "lecture_seule":True,"publication_active":False,"validation_juridique":"non_validee",
        "sha256_fichier_export":controle["sha256_fichier"],
        "manifest_sha256_archive_fournie":manifeste,"manifest_export_correspond":manifeste_identique,
        "archive_fournie_coherente_au_rejeu":True,"rapport_identique":identique,
        "sha256_resultat_export_canonique":hashlib.sha256(original).hexdigest(),
        "sha256_resultat_rejoue_canonique":hashlib.sha256(rejeu).hexdigest(),
        "authenticite_verifiee":False,"identite_registre_verifiee":False,"audit_serveur_verifie":False,
        "avertissements":[
            "Comparaison avec un dossier fourni explicitement, pas avec le registre serveur ni une archive officielle authentifiée.",
            "Le chemin et l'identité sont fournis par l'opérateur ; aucun chemin déduit de la requête, aucun accès réseau.",
            "Le résultat entier est comparé avec la version actuelle du logiciel, ordre des clés JSON ignoré ; listes et types conservés.",
            "Différence peut provenir d'une autre archive, d'une modification ou d'une version logicielle différente, pas preuve de fraude.",
            "Horodatage client et enveloppe ne sont pas rejoués ; aucune signature, identité humaine ou validation juridique attestée.",
            "Contrôle en lecture seule, pas transaction filesystem ni garantie contre mutation concurrente après lecture."]}
