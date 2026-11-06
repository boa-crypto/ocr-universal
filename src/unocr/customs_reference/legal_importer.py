"""Archivage opaque de PDF reçus et de transcriptions déclarées, sans OCR."""
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .importer import ImportRefuse, _json, _lire
from .legal_models import CodeDocumentaireBatch, MetadataCode

MAX_TOTAL = 128 * 1024 * 1024


def _analyser_code_contenu(texte_recu: bytes, metadata_recu: bytes, lire_document):
    brut = _json(texte_recu)
    if not isinstance(brut, dict) or set(brut) != {"articles", "relations"}:
        raise ImportRefuse("Transcription JSON attendue : articles et relations, sans source ni activation inline")
    meta = MetadataCode.model_validate_json(json.dumps(_json(metadata_recu), ensure_ascii=False, allow_nan=False))
    lot = CodeDocumentaireBatch.model_validate_json(json.dumps({
        "documents": [entree.document.model_dump(mode="json") for entree in meta.documents], **brut,
    }, ensure_ascii=False, allow_nan=False))
    fichiers = {"transcription_recue.json": texte_recu, "metadata_original.json": metadata_recu}
    archives, noms, taille = [], set(), len(texte_recu) + len(metadata_recu)
    for numero, entree in enumerate(meta.documents, 1):
        nom = entree.fichier_recu
        if nom in {".", ".."} or any(car in nom for car in ("/", "\\", ":", "\x00")):
            raise ImportRefuse("Nom local simple requis, sans chemin ni traversée")
        if nom in noms:
            raise ImportRefuse("Même fichier local déclaré plusieurs fois")
        noms.add(nom)
        contenu = lire_document(numero, nom)
        taille += len(contenu)
        if taille > MAX_TOTAL:
            raise ImportRefuse("Lot reçu trop volumineux (128 Mio maximum)")
        if hashlib.sha256(contenu).hexdigest() != entree.document.sha256:
            raise ImportRefuse("Empreinte PDF différente : " + entree.document.id)
        if not contenu.startswith(b"%PDF-"):
            raise ImportRefuse("Signature PDF absente ; aucun contenu reconstruit automatiquement")
        nom_archive = f"document_{numero:04d}.pdf"
        fichiers[nom_archive] = contenu
        archives.append({"document_id": entree.document.id, "nom_recu": nom, "fichier_archive": nom_archive,
                         "sha256": entree.document.sha256, "nature_document": entree.document.nature_document})
    utilises = {a.reference.source_id for a in lot.articles}
    empreintes = Counter(d.sha256 for d in lot.documents)
    rapport = {
        "type_lot": "code_douanier_documentaire", "statut": "quarantaine", "publication_active": False,
        "validation_juridique": "non_validee", "completude_reglementaire": "non_etablie",
        "transcription_verification": "non_verifiee", "restitution_juridique_a_date": False,
        "documents_recus": len(lot.documents), "octets_recus": taille,
        "articles_declares": len(lot.articles), "relations_declarees": len(lot.relations),
        "articles_par_nature": {nature: sum(a.nature_version == nature for a in lot.articles)
                                for nature in ("originale", "modificative", "consolidee_provisoire")},
        "documents_sans_article_transcrit": sorted(d.id for d in lot.documents if d.id not in utilises),
        "empreintes_documentaires_dupliquees": sorted(sha for sha, nombre in empreintes.items() if nombre > 1),
        "archives": archives,
        "avertissements": ["Transcription/PDF non rapprochés : le texte déclaré n'est pas vérifié par cet import.",
                           "Signature PDF et SHA256 ne prouvent ni authenticité ni validité structurelle du PDF.",
                           "Relations et chronologie déclarées : aucune portée juridique déduite.",
                           "Aucune consolidation, traduction, abrogation ou date d'effet automatique."],
        "ecrit": False,
    }
    return lot, rapport, fichiers, archives


def preparer_code(transcription: Path, metadata: Path, sortie: Path | None = None) -> dict:
    lot, rapport, fichiers, archives = _analyser_code_contenu(
        _lire(transcription), _lire(metadata), lambda numero, nom: _lire(metadata.parent / nom))
    rapport["ecrit"] = sortie is not None
    if sortie is not None:
        fichiers["lot_code.json"] = lot.model_dump_json(indent=2).encode("utf-8")
        fichiers["rapport.json"] = json.dumps(rapport, ensure_ascii=False, indent=2).encode("utf-8")
        sortie.mkdir(mode=0o700, parents=False, exist_ok=False)
        for nom, contenu in fichiers.items():
            with (sortie / nom).open("xb") as fichier:
                fichier.write(contenu)
        manifest = {"type_lot": "code_douanier_documentaire", "statut": "quarantaine",
                    "date_importation": datetime.now(timezone.utc).isoformat(), "publication_active": False,
                    "validation_juridique": "non_validee", "transcription_nom_recu": transcription.name,
                    "documents": archives,
                    "fichiers_sha256": {nom: hashlib.sha256(contenu).hexdigest() for nom, contenu in fichiers.items()}}
        with (sortie / "manifest.json").open("x", encoding="utf-8") as fichier:
            json.dump(manifest, fichier, ensure_ascii=False, indent=2)
    return rapport
