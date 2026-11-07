"""Positions des termes dans les libellés reçus ; pas preuve PDF ni attribut."""
from .search_excerpt import extrait_original, localiser_termes

MAX_EXTRAITS_TARIF = 16
CHAMPS_TARIF = ("designation_officielle_fr", "designation_officielle_ar")


def localiser_criteres(ligne, preuves, match_mode="sous_chaine"):
    textes = {champ: getattr(ligne, champ) for champ in CHAMPS_TARIF}
    termes_par_champ = {champ: list(dict.fromkeys(t for mots in preuves.values() for t, champs in mots.items()
                                                if champ in champs)) for champ in CHAMPS_TARIF}
    spans = {champ: localiser_termes(textes[champ], termes, match_mode) if termes else {}
             for champ, termes in termes_par_champ.items()}
    positions, extraits, total = {}, [], 0
    for critere, mots in preuves.items():
        positions[critere] = {}
        for terme, champs in mots.items():
            positions[critere][terme] = []
            for champ in champs:
                debut, fin = spans[champ][terme]
                positions[critere][terme].append({"champ_texte": champ,
                    "unite_decalage": "points_de_code_unicode_python",
                    "correspondance_debut": debut, "correspondance_fin": fin})
                if len(extraits) < MAX_EXTRAITS_TARIF:
                    extraits.append({"critere": critere, **extrait_original(textes[champ], champ, terme, debut, fin)})
                total += 1
    return {"positions_par_critere": positions, "extraits_correspondants": extraits,
            "total_extraits_disponibles": total, "extraits_tronques": total > len(extraits)}
