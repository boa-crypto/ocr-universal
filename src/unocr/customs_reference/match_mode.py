"""Modes littéraux explicites sur texte déjà normalisé, sans sémantique."""
import re

MODES_CORRESPONDANCE = ("sous_chaine", "mots_entiers")


def indice_terme(normalise, terme, mode="sous_chaine"):
    if mode == "sous_chaine":
        return normalise.find(terme)
    if mode == "mots_entiers":
        # Frontières dans le texte normalisé, sans recopier tout le libellé
        # pour chaque terme. Aucun motif fourni par l’utilisateur n’est exécuté.
        trouve = re.search(r"(?<!\S)" + re.escape(terme) + r"(?!\S)", normalise)
        return -1 if trouve is None else trouve.start()
    raise ValueError("Mode de correspondance inconnu")
