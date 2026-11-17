"""XML tabulaire explicite et fermé : ni XPath, DTD, namespace ou réseau."""
import re
from xml.parsers import expat

MAX_XML = 64 * 1024 * 1024
MAX_LIGNES = 200_000
MAX_COLONNES = 256
MAX_CELLULES = 2_000_000
MAX_TEXTE_CHAMP = 1024 * 1024
NOM = r"[A-Za-z_][A-Za-z0-9_.-]{0,63}"


class XMLRefuse(ValueError):
    """Structure hors contrat : aucun import partiel."""


def lire_xml(original: bytes, configuration: dict) -> tuple[list, dict]:
    racine, ligne = configuration.get("racine_xml"), configuration.get("ligne_xml")
    if not all(isinstance(nom, str) and re.fullmatch(NOM, nom) for nom in (racine, ligne)):
        raise XMLRefuse("Noms XML simples explicites requis : racine_xml et ligne_xml")
    if {"delimiteur", "feuille", "ligne_entete"} & set(configuration):
        raise XMLRefuse("Options CSV/XLSX interdites pour XML")
    if type(original) is not bytes or not 0 < len(original) <= MAX_XML:
        raise XMLRefuse("XML vide ou dépassant 64 Mio")
    try:
        original.decode("utf-8-sig")
    except UnicodeError:
        raise XMLRefuse("XML UTF-8 requis") from None
    parseur = expat.ParserCreate(encoding="UTF-8")
    parseur.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
    pile, rows, headers = [], [], None
    row, morceaux, taille, cellules, debut = {}, [], 0, 0, 0

    def interdit(*args):
        raise XMLRefuse("DTD, entités déclarées, commentaires et instructions de traitement refusés")

    def declaration(version, encodage, autonome):
        if version != "1.0" or (encodage is not None and encodage.upper() != "UTF-8"):
            raise XMLRefuse("XML 1.0 UTF-8 requis")

    def ouvrir(nom, attributs):
        nonlocal row, morceaux, taille, cellules, debut
        if attributs or re.fullmatch(NOM, nom) is None:
            raise XMLRefuse("Attributs, espaces de noms ou noms complexes refusés")
        profondeur = len(pile)
        if profondeur == 0:
            if nom != racine:
                raise XMLRefuse("Racine XML différente de celle déclarée")
        elif profondeur == 1:
            if nom != ligne or len(rows) >= MAX_LIGNES:
                raise XMLRefuse("Élément de ligne inattendu ou limite de lignes dépassée")
            row, debut = {}, parseur.CurrentLineNumber
        elif profondeur == 2:
            if nom in row or len(row) >= MAX_COLONNES or cellules >= MAX_CELLULES:
                raise XMLRefuse("Champ dupliqué ou limite colonnes/cellules dépassée")
            morceaux, taille = [], 0
            cellules += 1
        else:
            raise XMLRefuse("Champ XML imbriqué refusé")
        pile.append(nom)

    def texte(valeur):
        nonlocal taille
        if len(pile) == 3:
            taille += len(valeur)
            if taille > MAX_TEXTE_CHAMP:
                raise XMLRefuse("Champ XML dépassant 1 Mio de caractères")
            morceaux.append(valeur)
        elif valeur.strip(" \t\r\n"):
            raise XMLRefuse("Texte hors champ XML refusé")

    def fermer(nom):
        nonlocal headers
        if len(pile) == 3:
            row[nom] = "".join(morceaux)
        elif len(pile) == 2:
            if not row:
                raise XMLRefuse("Ligne XML vide refusée")
            if headers is None:
                headers = list(row)
            elif set(row) != set(headers):
                raise XMLRefuse("Jeu de champs différent entre lignes XML")
            rows.append((debut, row))
        pile.pop()

    parseur.XmlDeclHandler = declaration
    parseur.StartDoctypeDeclHandler = interdit
    parseur.EntityDeclHandler = interdit
    parseur.ExternalEntityRefHandler = interdit
    parseur.CommentHandler = interdit
    parseur.ProcessingInstructionHandler = interdit
    parseur.StartElementHandler = ouvrir
    parseur.CharacterDataHandler = texte
    parseur.EndElementHandler = fermer
    try:
        # Un seul appel évite le reparsing répété d'un très long jeton incomplet.
        # Les octets sources sont déjà bornés par le lecteur commun.
        parseur.Parse(original, True)
    except expat.ExpatError:
        raise XMLRefuse("XML mal formé ou caractères interdits") from None
    if headers is None:
        raise XMLRefuse("Aucune ligne XML tabulaire")
    return rows, {"headers": headers, "racine_xml": racine, "ligne_xml": ligne,
                  "localisation": "ligne_physique_debut_element_ligne", "encodage": "UTF-8",
                  "normalisation": "regles_XML_1_0_pas_normalisation_metier"}
