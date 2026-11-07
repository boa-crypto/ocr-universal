"""Rejeu local typé d’exports documentaires ; aucune identité officielle ou signature."""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

from .review_export import ExportRefuse, _lire_export, analyser_export
from .tariff_criteria import CRITERES, rechercher_tarif_criteres


def _parametres_export(requete, lot_id, *, route="tariff-criteria", autorises=None, numeriques=None, chemin_attendu=None):
    url = urlsplit(requete)
    attendu = chemin_attendu or f"/api/v1/customs-review/lots/{lot_id}/{route}"
    if url.scheme or url.netloc or url.fragment or url.path != attendu:
        raise ExportRefuse("Route et identité de lot explicites requises")
    if re.search(r"%(?![0-9a-fA-F]{2})", url.query):
        raise ExportRefuse("Encodage de requête incompatible")
    try:
        paires = parse_qsl(url.query,keep_blank_values=True,strict_parsing=True,
                           max_num_fields=9,encoding="utf-8",errors="strict")
    except ValueError:
        raise ExportRefuse("Requête de critères incompatible") from None
    params = {}
    if autorises is None:
        autorises = {*CRITERES,"code_prefix","match_mode","limit","offset"}
    if numeriques is None:
        numeriques = {"limit":("limite",7),"offset":("decalage",7)}
    for cle,valeur in paires:
        if cle not in autorises or cle in params:
            raise ExportRefuse("Paramètre inconnu ou dupliqué")
        params[cle] = valeur
    for cle,(destination,chiffres) in numeriques.items():
        if cle in params:
            if re.fullmatch(r"[0-9]{1,"+str(chiffres)+"}",params[cle]) is None:
                raise ExportRefuse("Pagination décimale ASCII explicite requise")
            params[destination] = int(params.pop(cle))
    return params


def _canonique(objet):
    # Contrairement à l'égalité Python, distingue 0 de false et 1 de 1.0.
    return json.dumps(objet,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")


def _verifier_rejeu(chemin_export: Path, repertoire: Path, lot_id: str, preparer=None) -> dict:
    if not isinstance(lot_id,str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}",lot_id) is None:
        raise ExportRefuse("Identité locale de lot explicite requise")
    contenu = _lire_export(chemin_export)
    controle = analyser_export(contenu)
    # Un seul fichier lu ; le contenu déjà contrôlé (doublons, bornes et Unicode)
    # est reparsé sans rouvrir le chemin. Aucun paramètre n'est un chemin local.
    objet = json.loads(contenu)
    if preparer is None:
        params = _parametres_export(objet["requete_relative"],lot_id)
        def operation(p):
            return rechercher_tarif_criteres(p,**params)
    else:
        operation = preparer(objet["requete_relative"],lot_id)
    try:
        reproduit = operation(repertoire)
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        raise ExportRefuse("Archive fournie ou paramètres de recherche incompatibles") from None
    return _constat_rejeu(controle,objet["resultat"],reproduit)


def _constat_rejeu(controle,exporte,reproduit):
    if "archive" in reproduit:
        manifeste = reproduit["archive"]["manifest_sha256"]
        manifestes = [manifeste]
        provenance = {"manifest_sha256_archive_fournie":manifeste,"archive_fournie_coherente_au_rejeu":True}
    else:
        par_role = {c:reproduit["archives"][c]["manifest_sha256"] for c in ("avant","apres")}
        manifestes = list(par_role.values())
        provenance = {"manifestes_archives_fournies":par_role,"archives_fournies_coherentes_au_rejeu":True}
    manifeste_identique = controle["manifestes_declares"] == manifestes
    original = _canonique(exporte)
    rejeu = _canonique(reproduit)
    identique = original == rejeu
    return {
        "type_controle":"rejeu_local_export_criteres_tarifaires",
        "statut":"rejeu_identique" if identique else "rejeu_different",
        "lecture_seule":True,"publication_active":False,"validation_juridique":"non_validee",
        "sha256_fichier_export":controle["sha256_fichier"],
        **provenance,"manifest_export_correspond":manifeste_identique,"rapport_identique":identique,
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


def verifier_rejeu_criteres(chemin_export: Path, repertoire: Path, lot_id: str) -> dict:
    """Contrat lot 50 conservé : critères tarifaires uniquement."""
    return _verifier_rejeu(chemin_export,repertoire,lot_id)


def verifier_rejeu_export(chemin_export: Path, repertoire: Path, lot_id: str, type_lot: str, *, autoriser_pdf: bool = False) -> dict:
    """Rejeu typé des seules lectures explicitement prises en charge."""
    if not isinstance(type_lot,str) or type_lot not in {"code","tarif","mesures"}:
        raise ExportRefuse("Type explicite code, tarif ou mesures requis")
    if type(autoriser_pdf) is not bool:
        raise ExportRefuse("Autorisation PDF booléenne explicite requise")
    from .export_replay_routes import preparer_rejeu

    resultat = _verifier_rejeu(chemin_export,repertoire,lot_id,
                              lambda requete,identite: preparer_rejeu(requete,identite,type_lot,autoriser_pdf=autoriser_pdf))
    resultat.update(type_controle="rejeu_local_export_documentaire",type_lot_explicite=type_lot,rejeu_pdf_autorise=autoriser_pdf)
    return resultat
