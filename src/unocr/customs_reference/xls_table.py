"""Sous-ensemble XLS OLE/BIFF8 textuel, contrôle binaire avant valeurs xlrd."""
import io
import struct

import xlrd
from xlrd.compdoc import CompDoc, CompDocError

from .tabular import MAX_CELLULES, MAX_COLONNES, MAX_LIGNES, TableurRefuse

MAX_XLS = 64 * 1024 * 1024
MAX_RECORDS = 500_000
INTERDITS = {0x0006, 0x04BC, 0x0221, 0x0236, 0x0037,  # formules, tableaux et variantes
             0x002F, 0x01AE, 0x0023, 0x0017, 0x0018,  # chiffrement, liens et noms
             0x00E5, 0x00D3, 0x005D, 0x00EB, 0x00EC, 0x01B6, 0x01B8}  # VBA, objets, dessins, liens


def _verifier_biff(contenu):
    position, nombre, section, globales, feuilles = 0, 0, None, 0, 0
    while position < len(contenu):
        # Les writers OLE peuvent compléter le flux Workbook par des octets nuls.
        if contenu[position:position + 4] == b"\0\0\0\0" and not any(contenu[position:]):
            break
        if position + 4 > len(contenu):
            raise TableurRefuse("En-tête BIFF tronqué")
        code, taille = struct.unpack_from("<HH", contenu, position)
        fin = position + 4 + taille
        if fin > len(contenu) or nombre >= MAX_RECORDS:
            raise TableurRefuse("BIFF tronqué ou nombre de records dépassé")
        payload = contenu[position + 4:fin]
        if code in INTERDITS:
            raise TableurRefuse("Formule, lien, objet, nom ou chiffrement BIFF refusé")
        if code == 0x0809:
            if section is not None or taille < 4:
                raise TableurRefuse("Début BIFF ambigu")
            version, section = struct.unpack_from("<HH", payload)
            if version != 0x0600 or section not in {0x0005, 0x0010}:
                raise TableurRefuse("BIFF8 avec feuilles tabulaires uniquement requis")
            if section == 0x0005:
                if nombre != 0 or globales:
                    raise TableurRefuse("Globales BIFF ambiguës")
                globales += 1
            else:
                feuilles += 1
        elif code == 0x000A:
            if section is None or taille:
                raise TableurRefuse("Fin BIFF incohérente")
            section = None
        elif section is None:
            raise TableurRefuse("Record hors section BIFF")
        elif code == 0x0200 and section == 0x0010:
            if taille != 14:
                raise TableurRefuse("Dimensions BIFF8 requises")
            _, fin_ligne, _, fin_colonne = struct.unpack_from("<IIHH", payload)
            if fin_ligne > MAX_LIGNES or fin_colonne > MAX_COLONNES or fin_ligne * fin_colonne > MAX_CELLULES:
                raise TableurRefuse("Dimensions XLS dépassées")
        nombre += 1
        position = fin
    if section is not None or globales != 1 or not feuilles:
        raise TableurRefuse("Sections BIFF incomplètes")


def lire_xls(original: bytes, configuration: dict) -> tuple[list, dict]:
    feuille, entete = configuration.get("feuille"), configuration.get("ligne_entete", 1)
    if not isinstance(feuille, str) or not feuille.strip() or type(entete) is not int or not 1 <= entete <= 50:
        raise TableurRefuse("Feuille explicite et en-tête entier de 1 à 50 requis")
    if "delimiteur" in configuration:
        raise TableurRefuse("Option CSV interdite pour XLS")
    if type(original) is not bytes or not 0 < len(original) <= MAX_XLS or not original.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        raise TableurRefuse("XLS OLE BIFF8 de 64 Mio maximum requis")
    classeur = None
    try:
        journal = io.StringIO()  # Ne pas émettre des diagnostics contenant les données du classeur.
        ole = CompDoc(original, logfile=journal, ignore_workbook_corruption=False)
        if len(ole.dirlist) > 128:
            raise TableurRefuse("Trop d'entrées OLE")
        noms = set()
        for entree in ole.dirlist:
            if entree.etype == 0:
                continue
            if entree.DID == 0 and entree.etype == 5:
                continue
            if (entree.etype != 2 or entree.parent != 0
                    or entree.name not in {"Workbook", "\x05SummaryInformation", "\x05DocumentSummaryInformation"}
                    or entree.name in noms):
                raise TableurRefuse("Stockage ou flux OLE hors contrat, projet VBA/objet non admis")
            noms.add(entree.name)
        contenu = ole.get_named_stream("Workbook")
        if not contenu or len(contenu) > MAX_XLS:
            raise TableurRefuse("Flux Workbook BIFF8 requis")
        _verifier_biff(contenu)
        classeur = xlrd.open_workbook(file_contents=original, logfile=journal, on_demand=True,
                                     ragged_rows=True, ignore_workbook_corruption=False)
        if classeur.biff_version != 80 or feuille not in classeur.sheet_names():
            raise TableurRefuse("Feuille BIFF8 déclarée introuvable")
        table = classeur.sheet_by_name(feuille)
        if table.visibility != 0 or table.merged_cells:
            raise TableurRefuse("Feuille cachée ou fusionnée refusée")
        if table.nrows > MAX_LIGNES or table.ncols > MAX_COLONNES or table.nrows * table.ncols > MAX_CELLULES:
            raise TableurRefuse("Bornes XLS dépassées")
        headers, rows, vides = None, [], 0
        for numero in range(entete - 1, table.nrows):
            cellules = table.row(numero)
            if any(c.ctype not in {xlrd.XL_CELL_TEXT, xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK} for c in cellules):
                raise TableurRefuse("Cellules XLS textuelles uniquement : nombres, dates, booléens et erreurs refusés")
            valeurs = [c.value if c.ctype == xlrd.XL_CELL_TEXT else None for c in cellules]
            if numero == entete - 1:
                if not valeurs or not all(isinstance(v, str) and v.strip() for v in valeurs) or len(valeurs) != len(set(valeurs)):
                    raise TableurRefuse("En-têtes XLS textuels uniques non vides requis")
                headers = valeurs
            elif not any(v is not None for v in valeurs):
                vides += 1
            else:
                if headers is None or len(valeurs) > len(headers):
                    raise TableurRefuse("Cellules XLS au-delà des en-têtes")
                valeurs.extend([None] * (len(headers) - len(valeurs)))
                rows.append((numero + 1, dict(zip(headers, valeurs))))
        if headers is None:
            raise TableurRefuse("En-tête XLS absent")
        return rows, {"headers": headers, "feuille": feuille, "ligne_entete": entete,
                      "feuilles_non_importees": [n for n in classeur.sheet_names() if n != feuille],
                      "lignes_vides_ignorees": vides, "contrat_xls": "ole_biff8_textuel_records_actifs_refuses"}
    except TableurRefuse:
        raise
    except (xlrd.XLRDError, CompDocError, ValueError, TypeError, IndexError, KeyError, struct.error, AssertionError, NotImplementedError, RecursionError, OverflowError):
        raise TableurRefuse("Structure XLS hors contrat ou corrompue") from None
    finally:
        if classeur is not None:
            classeur.release_resources()
