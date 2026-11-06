"""Contrôle/rejeu et diff de lots Code, sans effet juridique ni écriture."""
import hashlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

from .comparison import LotRefuse, _diff_collection, _provenances
from .importer import _json, _lire
from .legal_importer import _analyser_code_contenu
from .legal_models import CodeDocumentaireBatch

MAX_ARCHIVE = 256 * 1024 * 1024


def _canonique(valeur):
    # Comparaison des types JSON imbriqués : true != 1, 1.0 != 1.
    return json.dumps(valeur, sort_keys=True, ensure_ascii=False, allow_nan=False)


def charger_lot_code(repertoire: Path) -> tuple[CodeDocumentaireBatch, dict]:
    if repertoire.is_symlink() or not repertoire.is_dir():
        raise LotRefuse("Répertoire de lot Code absent ou symbolique")
    original = _lire(repertoire / "manifest.json")
    manifest = _json(original)
    champs = {"type_lot", "statut", "date_importation", "publication_active", "validation_juridique",
              "transcription_nom_recu", "documents", "fichiers_sha256"}
    if (not isinstance(manifest, dict) or set(manifest) != champs
            or manifest.get("type_lot") != "code_douanier_documentaire"
            or manifest.get("statut") != "quarantaine"
            or manifest.get("publication_active") is not False
            or manifest.get("validation_juridique") != "non_validee"):
        raise LotRefuse("Manifeste Code en quarantaine attendu, sans publication")
    try:
        date_import = datetime.fromisoformat(manifest["date_importation"])
        if date_import.utcoffset() != timedelta(0):
            raise ValueError("Horodatage UTC requis")
    except (TypeError, ValueError) as exc:
        raise LotRefuse("Date d'import UTC invalide") from exc
    if not isinstance(manifest["transcription_nom_recu"], str) or not manifest["transcription_nom_recu"]:
        raise LotRefuse("Nom de transcription reçu absent")
    empreintes = manifest["fichiers_sha256"]
    if not isinstance(empreintes, dict) or not 5 <= len(empreintes) <= 68:
        raise LotRefuse("Table d'empreintes Code invalide")
    attendus = {"transcription_recue.json", "metadata_original.json", "lot_code.json", "rapport.json"}
    attendus.update(f"document_{i:04d}.pdf" for i in range(1, len(empreintes) - 3))
    if set(empreintes) != attendus:
        raise LotRefuse("Noms d'archives Code non autorisés ou indices discontinus")
    presents = set()
    for nombre, fichier in enumerate(repertoire.iterdir(), 1):
        if nombre > len(attendus) + 1:
            raise LotRefuse("Fichiers inattendus dans le lot Code")
        presents.add(fichier.name)
    if presents != attendus | {"manifest.json"}:
        raise LotRefuse("Lot Code incomplet ou contenant des fichiers inattendus")
    fichiers, taille = {}, len(original)
    for nom in sorted(attendus):
        sha = empreintes[nom]
        if not isinstance(sha, str) or re.fullmatch(r"[a-f0-9]{64}", sha) is None:
            raise LotRefuse("Empreinte Code invalide")
        contenu = _lire(repertoire / nom)
        taille += len(contenu)
        if taille > MAX_ARCHIVE:
            raise LotRefuse("Archive Code trop volumineuse (256 Mio maximum)")
        if hashlib.sha256(contenu).hexdigest() != sha:
            raise LotRefuse("Empreinte Code différente : " + nom)
        fichiers[nom] = contenu
    lot = CodeDocumentaireBatch.model_validate_json(_canonique(_json(fichiers["lot_code.json"])))

    def lire_document(numero, nom_recu):
        # Ne jamais résoudre fichier_recu contre le système de fichiers ici.
        nom = f"document_{numero:04d}.pdf"
        if nom not in fichiers:
            raise LotRefuse("Document archivé absent pour le rejeu")
        return fichiers[nom]

    reproduit, rapport, fichiers_rejoues, archives = _analyser_code_contenu(
        fichiers["transcription_recue.json"], fichiers["metadata_original.json"], lire_document)
    if set(fichiers_rejoues) | {"lot_code.json", "rapport.json"} != attendus:
        raise LotRefuse("Archives documentaires et métadonnées incohérentes")
    if _canonique(reproduit.model_dump(mode="json")) != _canonique(lot.model_dump(mode="json")):
        raise LotRefuse("Lot Code non reproductible depuis les octets archivés")
    if _canonique(manifest["documents"]) != _canonique(archives):
        raise LotRefuse("Correspondances documentaires du manifeste incohérentes")
    if _canonique(_json(fichiers["rapport.json"])) != _canonique({**rapport, "ecrit": True}):
        raise LotRefuse("Rapport Code incohérent avec le rejeu")
    rapport["lecture_seule"] = True
    rapport["integrite_locale"] = "coherente_au_rejeu"
    rapport["validation_humaine_requise"] = True
    rapport["archive"] = {"date_importation": manifest["date_importation"],
                          "transcription_nom_recu": manifest["transcription_nom_recu"],
                          "manifest_sha256": hashlib.sha256(original).hexdigest(),
                          "fichiers_sha256": empreintes}
    return lot, rapport


def _perimetre(lot, rapport):
    return {"documents": sorted(d.id for d in lot.documents), "articles": sorted(a.id for a in lot.articles),
            "relations": sorted(r.id for r in lot.relations),
            "documents_sans_article_transcrit": rapport["documents_sans_article_transcrit"]}


def _details_ajouts_retraits(avant, apres):
    a, b = {o.id: o for o in avant}, {o.id: o for o in apres}
    return {"ajoutes": [b[cle].model_dump(mode="json") for cle in sorted(b.keys() - a.keys())],
            "retires": [a[cle].model_dump(mode="json") for cle in sorted(a.keys() - b.keys())]}


def comparer_lots_code(avant: Path, apres: Path) -> dict:
    a, rapport_a = charger_lot_code(avant)
    b, rapport_b = charger_lot_code(apres)
    perimetre_a, perimetre_b = _perimetre(a, rapport_a), _perimetre(b, rapport_b)
    docs_a, docs_b = {d.id: d for d in a.documents}, {d.id: d for d in b.documents}
    versions_ambigues = sorted(cle for cle in docs_a.keys() & docs_b.keys()
                              if docs_a[cle].version_source == docs_b[cle].version_source
                              and docs_a[cle].sha256 != docs_b[cle].sha256)
    articles_a, articles_b = {v.id: v for v in a.articles}, {v.id: v for v in b.articles}
    identites_a_revoir = sorted(cle for cle in articles_a.keys() & articles_b.keys()
                               if (articles_a[cle].numero_article, articles_a[cle].nature_version, articles_a[cle].version_juridique)
                               != (articles_b[cle].numero_article, articles_b[cle].nature_version, articles_b[cle].version_juridique))
    avertissements = [
        "Écarts entre déclarations archivées : aucune abrogation ni date d'effet déduite.",
        "Authenticité, correspondance transcription/PDF, exhaustivité et validité juridique non établies.",
        "Appariement par ID exact déclaré, jamais par numéro, ressemblance ou traduction.",
        "Changement d'ID : ajout/retrait technique, pas preuve d'une modification législative.",
        "Empreintes et rejeu ne constituent pas une immutabilité WORM ou un horodatage certifié.",
    ]
    if perimetre_a != perimetre_b:
        avertissements.append("Périmètres documentaires différents : revue requise avant interprétation.")
    if versions_ambigues:
        avertissements.append("Même version documentaire déclarée mais PDF différents : revue requise.")
    if identites_a_revoir:
        avertissements.append("ID d'article conservé avec numéro, nature ou version différents : revoir l'identité déclarée.")
    return {
        "type_comparaison": "code_douanier_documentaire", "lecture_seule": True, "publication_active": False,
        "validation_juridique": "non_validee", "validation_humaine_requise": True,
        "completude_reglementaire": "non_etablie", "restitution_juridique_a_date": False,
        "transcription_verification": "non_verifiee",
        "archives": {"avant": rapport_a["archive"], "apres": rapport_b["archive"]},
        "perimetres": {"avant": perimetre_a, "apres": perimetre_b},
        "sources_declarees": {"avant": [d.model_dump(mode="json") for d in a.documents],
                              "apres": [d.model_dump(mode="json") for d in b.documents]},
        "documents": _diff_collection(a.documents, b.documents, "id"),
        "articles": _diff_collection(a.articles, b.articles, "id"),
        "relations": _diff_collection(a.relations, b.relations, "id"),
        "details_ajouts_retraits": {"articles": _details_ajouts_retraits(a.articles, b.articles),
                                   "relations": _details_ajouts_retraits(a.relations, b.relations)},
        "provenances_modifiees": {"articles": _provenances(a.articles, b.articles, "id"),
                                  "relations": _provenances(a.relations, b.relations, "id")},
        "versions_documentaires_ambigues": versions_ambigues,
        "identites_articles_a_revoir": identites_a_revoir, "avertissements": avertissements,
    }
