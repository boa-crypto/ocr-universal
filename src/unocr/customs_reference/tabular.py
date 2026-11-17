"""Lecture XLSX littérale et bornée ; jamais d'évaluation de formule ni zfill."""
from __future__ import annotations

import io
import stat
import zipfile
from pathlib import PurePosixPath

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

MAX_MEMBRES = 4096
MAX_DECOMPRESSE = 128 * 1024 * 1024
MAX_RATIO = 200
MAX_LIGNES = 200_000
MAX_COLONNES = 256
MAX_CELLULES = 2_000_000


class TableurRefuse(ValueError):
    """Structure XLSX ambiguë, active ou hors des bornes de lecture."""


def _verifier_archive(original: bytes):
    try:
        with zipfile.ZipFile(io.BytesIO(original)) as archive:
            membres = archive.infolist()
            if len(membres) > MAX_MEMBRES:
                raise TableurRefuse("Trop de membres ZIP")
            noms = [m.filename for m in membres]
            if len(noms) != len(set(noms)):
                raise TableurRefuse("Membre ZIP dupliqué")
            if not {"[Content_Types].xml", "xl/workbook.xml"} <= set(noms):
                raise TableurRefuse("Paquet XLSX incomplet")
            total = 0
            for m in membres:
                chemin = PurePosixPath(m.filename)
                if (chemin.is_absolute() or ".." in chemin.parts or "\\" in m.filename
                        or ":" in m.filename or stat.S_ISLNK(m.external_attr >> 16)):
                    raise TableurRefuse("Chemin ZIP non sûr")
                if m.flag_bits & 1:
                    raise TableurRefuse("Classeur chiffré refusé")
                if (m.filename.lower().endswith("vbaproject.bin")
                        or m.filename.lower().startswith(("xl/externallinks/", "xl/macrosheets/",
                                                              "xl/dialogsheets/", "xl/activex/", "xl/embeddings/"))):
                    raise TableurRefuse("Macros ou liens de classeur externes refusés")
                total += m.file_size
                if total > MAX_DECOMPRESSE or m.file_size > max(1, m.compress_size) * MAX_RATIO:
                    raise TableurRefuse("Limite de décompression ou ratio ZIP dépassé")
                if m.filename.lower().endswith((".xml", ".rels")):
                    # Aucun DTD/ENTITY : garde indépendant des options du parseur.
                    with archive.open(m) as fichier:
                        precedent = b""
                        while bloc := fichier.read(65536):
                            examine = (precedent + bloc).replace(b"\x00", b"").upper()
                            if b"<!DOCTYPE" in examine or b"<!ENTITY" in examine:
                                raise TableurRefuse("DTD ou entité XML refusée")
                            precedent = bloc[-64:]
    except (zipfile.BadZipFile, NotImplementedError, RuntimeError) as exc:
        raise TableurRefuse("Archive XLSX invalide ou non prise en charge") from exc


def lire_xlsx(original: bytes, configuration: dict) -> tuple[list, dict]:
    feuille = configuration.get("feuille")
    entete = configuration.get("ligne_entete", 1)
    if not isinstance(feuille, str) or not feuille.strip():
        raise TableurRefuse("Nom de feuille explicite requis")
    if type(entete) is not int or not 1 <= entete <= 50:
        raise TableurRefuse("Ligne d'en-tête entière requise (1 à 50)")
    if "delimiteur" in configuration:
        raise TableurRefuse("Délimiteur CSV interdit pour XLSX")
    _verifier_archive(original)
    classeur = None
    try:
        classeur = load_workbook(io.BytesIO(original), read_only=True, data_only=False, keep_links=False)
        if feuille not in classeur.sheetnames:
            raise TableurRefuse("Feuille déclarée introuvable")
        table = classeur[feuille]
        if table.sheet_state != "visible":
            raise TableurRefuse("Feuille cachée refusée")
        # Les dimensions déclarées d'un classeur peuvent être inexactes : ne pas
        # ignorer silencieusement des cellules situées hors du rectangle annoncé.
        table.reset_dimensions()
        headers = None
        donnees = []
        vides = 0
        cellules = 0
        for numero, row in enumerate(table.iter_rows(), 1):
            cellules += len(row)
            if numero > MAX_LIGNES or len(row) > MAX_COLONNES or cellules > MAX_CELLULES:
                raise TableurRefuse("Bornes lignes/colonnes/cellules dépassées")
            if numero < entete:
                continue
            if any(cell.data_type == "f" for cell in row):
                raise TableurRefuse(f"Formule refusée dans {feuille}, ligne {numero}")
            valeurs = [cell.value for cell in row]
            if numero == entete:
                if not valeurs or not all(isinstance(v, str) and v.strip() for v in valeurs):
                    raise TableurRefuse("En-têtes textuels non vides requis")
                if len(valeurs) != len(set(valeurs)):
                    raise TableurRefuse("En-tête XLSX dupliqué")
                headers = valeurs
            elif not any(v is not None for v in valeurs):
                vides += 1
            else:
                if headers is None or len(valeurs) > len(headers):
                    raise TableurRefuse("Cellules au-delà des en-têtes déclarés")
                valeurs.extend([None] * (len(headers) - len(valeurs)))
                donnees.append((numero, dict(zip(headers, valeurs))))
        if headers is None:
            raise TableurRefuse("Ligne d'en-tête absente")
        return donnees, {"headers": headers, "feuille": feuille, "ligne_entete": entete,
                         "feuilles_non_importees": [n for n in classeur.sheetnames if n != feuille],
                         "lignes_vides_ignorees": vides}
    except (zipfile.BadZipFile, InvalidFileException, SyntaxError, KeyError, TypeError, IndexError) as exc:
        raise TableurRefuse("Structure de classeur inexploitable") from exc
    finally:
        if classeur is not None:
            classeur.close()
