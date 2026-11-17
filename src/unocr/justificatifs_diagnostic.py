"""Diagnostic en lecture seule des pièces, jamais une commande de purge.

Pour un résultat stable, arrêter les écritures du serveur : le cliché SQLite
ne rend pas les fichiers transactionnels. Aucun fichier/objet n'est réparé ici.
"""
from __future__ import annotations

import hashlib
import re
import sqlite3
from pathlib import Path

from pydantic import ValidationError

from .models import Frais, Justificatif


def _diagnostiquer_pieces(racine: Path) -> dict:
    anomalies: list[dict] = []
    indisponible = False
    references_connues = True
    pieces: dict[str, Justificatif] = {}
    frais: dict[str, Frais] = {}
    frais_invalides: set[str] = set()

    def noter(categorie, cible, detail):
        anomalies.append({"categorie": categorie, "cible": cible, "detail": detail})

    if not racine.is_dir():
        noter("magasin_absent", str(racine), "Répertoire introuvable ou inaccessible")
        indisponible = True

    base = racine / "metier.sqlite3"
    base_presente = base.exists() or base.is_symlink()
    if not base_presente:
        references_connues = False
    if base.is_symlink():
        noter("base_refusee", "metier.sqlite3", "Lien symbolique : lecture refusée")
        indisponible = True
        references_connues = False
    elif base.exists():
        connexion = None
        try:
            # SQLite peut créer des sidecars en lisant une base WAL. Ce format
            # externe n'est pas celui de BusinessStore : ne pas l'ouvrir ici.
            with base.open("rb") as entete:
                mode = entete.read(20)[18:20]
            if mode == b"\x02\x02":
                noter("base_wal", "metier.sqlite3", "Mode WAL : diagnostic refusé pour ne créer aucun sidecar")
                raise sqlite3.DatabaseError("mode WAL non pris en charge")
            connexion = sqlite3.connect(base.resolve().as_uri() + "?mode=ro", uri=True, timeout=5)
            connexion.execute("PRAGMA query_only=ON")
            lignes = connexion.execute(
                "SELECT collection,id,payload FROM objects WHERE collection IN ('frais','justificatif') "
                "ORDER BY collection,id").fetchall()
            for collection, cle, payload in lignes:
                modele = Frais if collection == "frais" else Justificatif
                try:
                    objet = modele.model_validate_json(payload)
                    if objet.id != cle:
                        raise ValueError("identifiant incohérent")
                    if collection == "justificatif" and (
                        not 0 < objet.taille_octets <= 20 * 1024 * 1024
                        or not re.fullmatch(r"[a-f0-9]{64}", objet.hash_sha256)
                    ):
                        raise ValueError("taille/empreinte invalide")
                except (ValidationError, ValueError):
                    noter("metadonnee_invalide", f"{collection}/{cle}", "Objet ou identifiant invalide")
                    if collection == "justificatif":
                        references_connues = False
                    else:
                        frais_invalides.add(cle)
                    continue
                if collection == "frais":
                    frais[cle] = objet
                else:
                    pieces[cle] = objet
        except (sqlite3.Error, OSError):
            noter("base_illisible", "metier.sqlite3", "Impossible de lire les références ; aucun blob ne sera déclaré orphelin")
            references_connues = False
            indisponible = True
        finally:
            if connexion is not None:
                connexion.close()

    chemins: dict[str, list[str]] = {}
    repertoire = racine / "justificatifs"
    repertoire_sur = not repertoire.is_symlink()
    if not repertoire_sur:
        noter("repertoire_refuse", "justificatifs", "Lien symbolique : aucun fichier suivi")
        indisponible = True
    for cle, piece in pieces.items():
        parent = frais.get(piece.frais_id)
        if parent is None and piece.frais_id not in frais_invalides:
            noter("frais_absent", cle, "La pièce référence un frais absent")
        elif parent is not None and cle not in parent.justificatifs:
            noter("lien_absent", cle, "Le frais ne contient pas l'identifiant de la pièce")
        chemin = piece.chemin_fichier
        if not re.fullmatch(r"justificatifs/[a-f0-9]{32}\.bin", chemin):
            noter("chemin_refuse", cle, "Chemin non canonique : aucun fichier suivi")
            # Un ancien chemin peut désigner un blob local : pas de classement
            # automatique en orphelin quand les références sont incomplètes.
            references_connues = False
            continue
        chemins.setdefault(chemin, []).append(cle)
        if not repertoire_sur:
            continue
        fichier = racine / chemin
        if fichier.is_symlink():
            noter("symlink_refuse", chemin, "Lien symbolique : aucun contenu lu")
            continue
        try:
            if not fichier.is_file():
                noter("fichier_absent", cle, chemin)
                continue
            if fichier.stat().st_size != piece.taille_octets:
                noter("taille_incoherente", cle, chemin)
                continue
            empreinte = hashlib.sha256()
            lus = 0
            with fichier.open("rb") as contenu:
                for bloc in iter(lambda: contenu.read(65536), b""):
                    lus += len(bloc)
                    if lus > piece.taille_octets:
                        break
                    empreinte.update(bloc)
            if lus != piece.taille_octets:
                noter("taille_incoherente", cle, chemin)
                continue
            if empreinte.hexdigest() != piece.hash_sha256:
                noter("empreinte_incoherente", cle, chemin)
        except OSError:
            noter("fichier_illisible", cle, chemin)
            indisponible = True
    for chemin, identifiants in chemins.items():
        if len(identifiants) > 1:
            noter("chemin_partage", chemin, "Plusieurs métadonnées utilisent ce fichier")
    for cle, parent in frais.items():
        for identifiant in sorted(set(parent.justificatifs)):
            if identifiant not in pieces:
                if references_connues:
                    noter("lien_sans_metadonnee", cle, identifiant)
            elif pieces[identifiant].frais_id != cle:
                noter("mauvais_frais", cle, identifiant)
        if len(parent.justificatifs) != len(set(parent.justificatifs)):
            noter("liens_dupliques", cle, "Identifiants de pièces dupliqués")
    if repertoire_sur and repertoire.exists():
        try:
            for fichier in sorted(repertoire.iterdir()):
                relatif = "justificatifs/" + fichier.name
                if fichier.is_symlink():
                    if relatif not in chemins:
                        noter("symlink_refuse", relatif, "Lien symbolique non suivi")
                elif not fichier.is_file():
                    noter("entree_inattendue", relatif, "Aucun parcours récursif")
                elif re.fullmatch(r"\.[a-f0-9]{32}\.bin\.deleted\.tmp", fichier.name):
                    original = "justificatifs/" + fichier.name[1:-len(".deleted.tmp")]
                    noter("quarantaine", relatif, "Référence(s) : " + ", ".join(chemins.get(original, []))
                          if original in chemins else "Aucune référence connue ; ne pas supprimer sans examen")
                elif fichier.name.endswith(".tmp"):
                    noter("temporaire", relatif, "Écriture possiblement interrompue ou en cours")
                elif re.fullmatch(r"[a-f0-9]{32}\.bin", fichier.name):
                    if relatif not in chemins:
                        noter("blob_sans_reference" if references_connues else "blob_non_classe",
                              relatif, "Aucune suppression automatique")
                else:
                    noter("entree_inattendue", relatif, "Ancien fichier ou nom inconnu : examen manuel")
        except OSError:
            noter("repertoire_illisible", "justificatifs", "Inventaire incomplet")
            indisponible = True
    return {"lecture_seule": True, "base_presente": base_presente,
            "pieces_referencees": len(pieces), "references_completes": references_connues,
            "etat": "indisponible" if indisponible else ("anomalies" if anomalies else "conforme"),
            "anomalies": anomalies,
            "limite": "Diagnostic sans réparation. Suspendre les écritures pour une mesure stable."}


def diagnostiquer_pieces(racine: Path) -> dict:
    try:
        return _diagnostiquer_pieces(racine)
    except OSError:
        return {"lecture_seule": True, "base_presente": None, "pieces_referencees": 0,
                "references_completes": False, "etat": "indisponible",
                "anomalies": [{"categorie": "magasin_illisible", "cible": str(racine),
                               "detail": "Inventaire interrompu : accès disque impossible"}],
                "limite": "Diagnostic incomplet, aucune réparation ni suppression effectuée."}
