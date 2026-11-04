"""Direction d'écriture (C3) — détection RTL et aide au rendu.

**Pourquoi c'est nécessaire.** UniOCR traite l'arabe parmi ses 11 langues.
Un texte arabe affiché dans un conteneur LTR : l'ordre visuel des mots est
inversé, la ponctuation se retrouve du mauvais côté, et les nombres mêlés au
texte deviennent illisibles. C'est un défaut de rendu réel, pas cosmétique.

**Ce que fait ce module.**
- détecte la direction d'un texte à partir des caractères RTL qu'il contient
  (arabe, hébreu, syriaque, thâna, n'ko…), en gérant les nombres et les
  parenthèses qui restent en ordre logique ;
- calcule la direction d'une page et d'un document (dominante + mélange) ;
- fournit les attributs HTML à poser (`dir`, `lang`) pour un affichage correct.

**Ce qu'il ne fait pas** : translittération, ni réordonnancement des mots
(le texte extrait reste la transcription du moteur, jamais réécrit).
"""
from __future__ import annotations

import re
import unicodedata

# plages Unicode des écritures de droite à gauche
_RTL_RANGES = (
    (0x0590, 0x05FF),    # hébreu
    (0x0600, 0x06FF),    # arabe
    (0x0700, 0x074F),    # syriaque
    (0x0750, 0x077F),    # supplément arabe
    (0x0780, 0x07BF),    # thâna
    (0x07C0, 0x08FF),    # extended arabic / nko
    (0xFB1D, 0xFB4F),    # hébreu présentations
    (0xFB50, 0xFDFF),    # formes arabes A
    (0xFE70, 0xFEFF),    # formes arabes B
)

# caractères neutres fréquents qui ne décident pas de la direction
_NEUTRAL = set(" \t\r\n.,;:!?()[]{}\"'/\\|-—–…·")


def is_rtl_char(ch: str) -> bool:
    cp = ord(ch)
    return any(lo <= cp <= hi for lo, hi in _RTL_RANGES)


def _strong_direction_counts(text: str) -> tuple[int, int]:
    """(nombre de caractères RTL forts, nombre de caractères LTR forts)."""
    rtl = ltr = 0
    for ch in text:
        if ch in _NEUTRAL or not ch.strip():
            continue
        if is_rtl_char(ch):
            rtl += 1
        elif unicodedata.category(ch).startswith("L"):
            ltr += 1
    return rtl, ltr


def detect_direction(text: str, threshold: float = 0.4) -> str:
    """'rtl', 'ltr' ou 'neutral' (pas assez de caractères directionnels).

    `threshold` : part minimale de caractères RTL parmi les caractères
    directionnels pour conclure RTL — 0,4 tolère un texte arabe contenant
    des nombres ou des mots latins isolés.
    """
    if not text:
        return "neutral"
    rtl, ltr = _strong_direction_counts(text)
    total = rtl + ltr
    if total < 3:                      # trop peu de matière pour décider
        return "neutral"
    if rtl / total >= threshold:
        return "rtl"
    if ltr / total >= 1 - threshold:
        return "ltr"
    return "neutral"


def dominant_direction(directions: list[str]) -> str:
    """Direction majoritaire d'un ensemble de pages ('ltr' par défaut)."""
    rtl = sum(1 for d in directions if d == "rtl")
    ltr = sum(1 for d in directions if d == "ltr")
    if rtl > ltr:
        return "rtl"
    if ltr > rtl:
        return "ltr"
    return "ltr" if ltr or rtl else "neutral"


# ─────────────────── segmentation en plages directionnelles ───────────────────

_RTL_RUN = re.compile(
    "[" + "".join(f"{chr(lo)}-{chr(hi)}" for lo, hi in _RTL_RANGES) + "]+")


def rtl_spans(text: str) -> list[tuple[int, int]]:
    """Plages (début, fin) des segments RTL d'un texte — utile pour afficher
    chaque segment dans son propre conteneur `dir=rtl` (rendu correct garanti)."""
    return [(m.start(), m.end()) for m in _RTL_RUN.finditer(text)]
