"""Fragments originaux de recherche ; offsets Unicode, aucune attestation PDF."""
import unicodedata

MAX_EXTRAIT = 384
CONTEXTE_AVANT = 40
CHAMPS_EXTRAITS = ("intitule", "texte_integral", "texte_francais", "texte_arabe")


def _indices_normalises(texte):
    """Position d'origine de chaque caractère normalisé, sans table de tout le texte."""
    present, separateur = False, None
    for i, original in enumerate(texte):
        for c in unicodedata.normalize("NFKD", original).casefold().replace("œ", "oe").replace("æ", "ae"):
            if unicodedata.category(c).startswith("M") or c == "ـ":
                continue
            if c.isalnum():
                if separateur is not None:
                    yield separateur
                    separateur = None
                yield i
                present = True
            elif present and separateur is None:
                separateur = i


def extraits_correspondants(champs, termes):
    # Import local : le moteur de recherche appelle ce complément seulement pour
    # les résultats de la page, et reste l'unique définition de la normalisation.
    from .search import _normaliser

    extraits = []
    for champ in CHAMPS_EXTRAITS:
        texte = champs.get(champ)
        if not texte or not termes:
            continue
        normalise = _normaliser(texte)
        trouve = next(((terme, normalise.find(terme)) for terme in termes if terme in normalise), None)
        if trouve is None:
            continue
        terme, index = trouve
        del normalise
        debut_match = fin_match = None
        for n, origine in enumerate(_indices_normalises(texte)):
            if n == index:
                debut_match = origine
            if n == index + len(terme) - 1:
                fin_match = origine + 1
                break
        if debut_match is None or fin_match is None:
            raise ValueError("Impossible de localiser la correspondance normalisée dans le texte original")
        debut = max(0, debut_match - CONTEXTE_AVANT)
        fin = min(len(texte), debut + MAX_EXTRAIT)
        extraits.append({"champ_texte": champ, "terme_normalise": terme,
                         "unite_decalage": "points_de_code_unicode_python", "decalage": debut,
                         "fragment": texte[debut:fin], "total_caracteres": len(texte),
                         "correspondance_debut": debut_match, "correspondance_fin": fin_match,
                         "correspondance_entierement_visible": fin_match <= fin,
                         "tronque_debut": debut > 0, "tronque_fin": fin < len(texte)})
    return extraits
