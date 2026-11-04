"""Moteur universel de correspondance des champs (Phase 4).

Indépendant des connecteurs : il transforme les données OCR normalisées
(`FieldValue`) vers le schéma propre au système cible.

**Règle de sécurité fondamentale.** Une correspondance n'est appliquée que si
elle est **explicite** (configurée par un humain) ou **exacte** (égalité de nom
normalisé). Une simple similarité sémantique ne remplit JAMAIS silencieusement
un champ : elle est proposée comme *suggestion* à valider. C'est la différence
entre « deviner » et « préparer » — et c'est ce qui évite de transmettre une
valeur fausse à une administration.

Trois niveaux de confiance, exposés à l'interface :
- `explicit`  : règle configurée par un humain → applicable directement
- `exact`     : égalité stricte après normalisation → applicable
- `suggested` : similarité → **à valider**, jamais appliqué sans confirmation
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Optional

from ..logging_setup import get_logger

log = get_logger("connectors.mapping")

CONFIDENCE_LEVELS = ("explicit", "exact", "suggested")


def normalize_key(name: str) -> str:
    """Normalise un nom de champ pour comparaison (minuscules, sans accents,
    sans séparateurs). « N° de connaissement » → « nodeconnaissement »."""
    if not name:
        return ""
    s = unicodedata.normalize("NFKD", str(name))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s


# ─────────────────────────── conversions ───────────────────────────

def _to_iso_date(value: str, dayfirst: bool = True) -> tuple[Optional[str], str]:
    """Convertit une date en ISO AAAA-MM-JJ.

    Renvoie (valeur, avertissement). `dayfirst` explicitе la convention
    (True = jj/mm/aaaa, convention francophone du projet) : elle n'est jamais
    sous-entendue. Quand les deux lectures sont possibles (les deux nombres
    ≤ 12), la conversion est faite **selon la convention déclarée** mais un
    avertissement le signale — l'utilisateur voit que la date est incertaine.
    """
    if not value:
        return None, ""
    v = str(value).strip()
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", v)
    if m:
        y, a, b = (int(x) for x in m.groups())
        iso = _valid_date(y, a, b)
        return iso, "" if iso else f"date invalide : {v}"

    m = re.fullmatch(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})", v)
    if m:
        a, b, y = (int(x) for x in m.groups())
        ambiguous = a <= 12 and b <= 12 and a != b
        # lecture selon la convention déclarée ; si elle est impossible
        # (mois > 12), on tente l'autre lecture en le signalant.
        iso = _valid_date(y, b, a) if dayfirst else _valid_date(y, a, b)
        if iso is None:
            iso = _valid_date(y, a, b) if dayfirst else _valid_date(y, b, a)
            if iso is None:
                return None, f"date invalide : {v}"
            return iso, (f"« {v} » ne suit pas la convention "
                         f"{'jj/mm' if dayfirst else 'mm/jj'}/aaaa : "
                         "lu dans l'autre ordre — à confirmer")
        if ambiguous:
            return iso, (f"date ambiguë « {v} » lue en "
                         f"{'jj/mm' if dayfirst else 'mm/jj'}/aaaa — à confirmer")
        return iso, ""

    # formes textuelles courantes : 12 mars 2019
    months = {"janvier": 1, "février": 2, "mars": 3, "avril": 4, "mai": 5,
              "juin": 6, "juillet": 7, "août": 8, "septembre": 9,
              "octobre": 10, "novembre": 11, "décembre": 12}
    m = re.fullmatch(r"(\d{1,2})\s+([\wéûôàç]+)\.?\s+(\d{4})", v.lower())
    if m and m.group(2) in months:
        iso = _valid_date(int(m.group(3)), months[m.group(2)], int(m.group(1)))
        return iso, "" if iso else f"date invalide : {v}"

    return None, f"format de date non reconnu : {v}"


def _valid_date(y: int, m: int, d: int) -> Optional[str]:
    if not (1 <= m <= 12 and 1 <= d <= 31 and 1000 <= y <= 2200):
        return None
    return f"{y:04d}-{m:02d}-{d:02d}"


_NUM_CLEAN = re.compile(r"[^\d,.\-]")


def to_decimal(value: str, decimal_sep: str = ",") -> tuple[Optional[str], str]:
    """Normalise un nombre (« 1 234,56 » → « 1234.56 »).

    `decimal_sep` déclare le séparateur décimal (« . » ou « , ») : il n'est
    jamais deviné. Renvoie (valeur, avertissement) ; une valeur ambiguë est
    convertie puis signalée plutôt que choisie en silence.
    """
    if value is None:
        return None, ""
    v = str(value).strip()
    if not v:
        return None, ""
    neg = v.startswith("-")
    v = _NUM_CLEAN.sub("", v)
    v = v.lstrip("-")                     # le signe est réappliqué à la fin
    if not v or v in (".", ","):
        return None, ""

    other = "." if decimal_sep == "," else ","
    warn = ""
    if decimal_sep in v and other in v:
        # les deux séparateurs présents : le DERNIER est le séparateur décimal,
        # l'autre est un séparateur de milliers.
        if v.rfind(other) > v.rfind(decimal_sep):
            v = v.replace(decimal_sep, "")            # « 1,234.56 » → 1234.56
        else:
            v = v.replace(other, "").replace(decimal_sep, ".")  # « 1.234,56 »
        warn = "séparateurs mixtes normalisés — à vérifier"
    elif decimal_sep in v:
        parts = v.split(decimal_sep)
        if len(parts) == 2 and len(parts[1]) <= 2:
            v = parts[0] + "." + parts[1]        # « 1234,56 »
        else:
            v = "".join(parts)                   # « 1,234,567 » → milliers
            warn = f"« {decimal_sep} » interprété comme séparateur de milliers"
    elif other in v:
        parts = v.split(other)
        if len(parts) > 1 and all(len(x) == 3 for x in parts[1:]):
            v = "".join(parts)                   # « 1.234 » / « 1.234.567 » → milliers
            warn = f"« {other} » interprété comme séparateur de milliers"
        else:
            v = v.replace(other, ".")
    if v in ("", "-", "."):
        return None, "valeur numérique vide"
    return ("-" if neg else "") + v, warn


def clean_text(value: str) -> str:
    """Normalise les espaces et caractères invisibles, sans altérer le sens."""
    if value is None:
        return ""
    s = str(value)
    s = s.replace("\u00a0", " ").replace("\u200b", "")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


# ─────────────────────────── règles de correspondance ───────────────────────────

@dataclass
class MappingRule:
    """Règle explicite : champ OCR → champ cible, avec transformation optionnelle."""
    source_field: str                     # nom du champ OCR (clé de `fields`)
    target_field: str                     # nom réel chez le système cible
    transform: str = ""                   # iso_date | decimal | clean | upper | none
    note: str = ""

    def as_dict(self) -> dict:
        return {"source_field": self.source_field, "target_field": self.target_field,
                "transform": self.transform, "note": self.note}


@dataclass
class MappingVersion:
    """Une version de mapping est immuable et traçable."""
    version: str
    rules: list[MappingRule] = field(default_factory=list)
    created_at: float = 0.0
    author: str = ""
    note: str = ""

    def as_dict(self) -> dict:
        return {"version": self.version,
                "rules": [r.as_dict() for r in self.rules],
                "created_at": self.created_at, "author": self.author,
                "note": self.note}


@dataclass
class MappedValue:
    """Valeur prête pour le formulaire cible + sa traçabilité complète."""
    target_field: str
    value: Optional[str]
    confidence: str                 # explicit | exact | suggested
    source_field: Optional[str] = None
    transform: str = ""
    source_page: Optional[int] = None
    ocr_raw: Optional[str] = None   # valeur OCR originale
    normalized: Optional[str] = None
    warning: str = ""

    def as_dict(self) -> dict:
        return {"target_field": self.target_field, "value": self.value,
                "confidence": self.confidence, "source_field": self.source_field,
                "transform": self.transform, "source_page": self.source_page,
                "ocr_raw": self.ocr_raw, "normalized": self.normalized,
                "warning": self.warning}


TRANSFORMS = {
    "iso_date": _to_iso_date,
    "decimal": to_decimal,
    "clean": clean_text,
    "upper": lambda v: clean_text(v).upper(),
    "none": lambda v: clean_text(v),
}


def apply_transform(value: Optional[str], transform: str,
                     dayfirst: bool = True) -> tuple[Optional[str], str]:
    """Applique une transformation. Renvoie (valeur, avertissement).

    Une transformation qui échoue renvoie la valeur d'origine + un
    avertissement : on ne perd jamais l'information, on la signale.
    """
    if value is None:
        return None, ""
    try:
        if transform == "iso_date":
            out, warn = _to_iso_date(value, dayfirst=dayfirst)
        elif transform == "decimal":
            out, warn = to_decimal(value)
        else:
            fn = TRANSFORMS.get(transform or "none", TRANSFORMS["none"])
            out, warn = fn(value), ""
    except Exception:
        return value, f"transformation « {transform} » impossible"
    if out is None and transform in ("iso_date", "decimal"):
        return value, (warn or (f"« {transform} » impossible sur « {value} » : "
                                "valeur conservée telle quelle, à vérifier"))
    return out, warn


# ─────────────────────────── le moteur ───────────────────────────

class MappingEngine:
    """Associe les champs OCR aux champs cibles, avec traçabilité totale."""

    def __init__(self, rules: Optional[list[MappingRule]] = None):
        self.rules = list(rules or [])

    # ─── configuration ───

    def add_rule(self, rule: MappingRule) -> None:
        self.rules = [r for r in self.rules
                      if r.target_field != rule.target_field]
        self.rules.append(rule)

    def remove_rule(self, target_field: str) -> bool:
        before = len(self.rules)
        self.rules = [r for r in self.rules if r.target_field != target_field]
        return len(self.rules) != before

    @classmethod
    def from_dict(cls, data: dict) -> "MappingEngine":
        allowed = {"source_field", "target_field", "transform", "note"}
        rules = []
        for r in (data.get("rules") or []):
            if not isinstance(r, dict):
                continue
            # les clés inconnues sont ignorées, la règle est conservée
            clean = {k: v for k, v in r.items() if k in allowed}
            if clean.get("source_field") and clean.get("target_field"):
                rules.append(MappingRule(**clean))
            else:
                log.warning("règle de mapping ignorée (incomplète) : %s",
                            sorted(clean))
        return cls(rules)

    def as_dict(self) -> dict:
        return {"rules": [r.as_dict() for r in self.rules]}

    # ─── suggestions (jamais appliquées seules) ───

    def suggest(self, target_fields: Any,
                ocr_fields: dict[str, Any]) -> list[dict]:
        """Propose des correspondances par similarité de nom.

        Retourne des **suggestions** marquées `suggested` : l'interface doit
        les faire valider. Une similarité seule ne remplit rien.
        """
        ocr_keys = list(ocr_fields.keys())
        suggestions = []
        for tf in _as_field_list(target_fields):
            name = getattr(tf, "external_name", None) or (
                tf.get("external_name") if isinstance(tf, dict) else None)
            label = getattr(tf, "label", None) or (
                tf.get("label") if isinstance(tf, dict) else "") or ""
            if not name:
                continue
            best, score = None, 0.0
            for key in ocr_keys:
                s = _similarity(normalize_key(key), normalize_key(name),
                                normalize_key(label))
                if s > score:
                    best, score = key, s
            if best is not None and score >= 0.55:
                suggestions.append({
                    "target_field": name, "source_field": best,
                    "confidence": "suggested", "score": round(score, 2),
                    "reason": "similarité de nom — À VALIDER"})
        return suggestions

    # ─── application ───

    def apply(self, target_fields: Any,
              ocr_fields: dict[str, Any]) -> dict[str, MappedValue]:
        """Produit les valeurs pour chaque champ cible.

        - règle explicite → `explicit`
        - égalité exacte de nom normalisé → `exact`
        - sinon → suggestion non appliquée (valeur None)
        """
        out: dict[str, MappedValue] = {}
        by_target = {r.target_field: r for r in self.rules}
        norm_index = {normalize_key(k): k for k in ocr_fields}

        for tf in _as_field_list(target_fields):
            name = getattr(tf, "external_name", None) or (
                tf.get("external_name") if isinstance(tf, dict) else None)
            if not name:
                continue
            required = bool(getattr(tf, "required", None) if not isinstance(tf, dict)
                            else tf.get("required"))

            rule = by_target.get(name)
            if rule is not None:
                fv = ocr_fields.get(rule.source_field)
                if fv is None:
                    out[name] = MappedValue(
                        name, None, "explicit", rule.source_field, rule.transform,
                        warning="champ source absent du document")
                    continue
                raw = _field_value(fv)
                val, warn = apply_transform(raw, rule.transform)
                out[name] = MappedValue(
                    name, val, "explicit", rule.source_field, rule.transform,
                    source_page=getattr(fv, "page_num", None),
                    ocr_raw=raw, normalized=getattr(fv, "normalized_value", None),
                    warning=warn)
                continue

            key = norm_index.get(normalize_key(name))
            if key is not None:
                fv = ocr_fields[key]
                raw = _field_value(fv)
                out[name] = MappedValue(
                    name, clean_text(raw), "exact", key, "clean",
                    source_page=getattr(fv, "page_num", None), ocr_raw=raw,
                    normalized=getattr(fv, "normalized_value", None))
                continue

            out[name] = MappedValue(
                name, None, "suggested",
                warning=("champ obligatoire sans correspondance"
                         if required else "aucune correspondance"))

        return out


def _as_field_list(target_fields: Any) -> list[Any]:
    """Accepte un `FormSchema` ou une liste de champs — évite les erreurs
    d'appel silencieuses."""
    if target_fields is None:
        return []
    if hasattr(target_fields, "fields"):        # FormSchema
        return list(target_fields.fields)
    if isinstance(target_fields, dict) and "fields" in target_fields:
        return list(target_fields["fields"])
    return list(target_fields)


def _field_value(fv: Any) -> Optional[str]:
    """Valeur d'un `FieldValue` : confirmée > corrigée > normalisée > brute.

    Reprend exactement la règle de priorité du modèle existant — la valeur
    validée par un humain reste prioritaire sur la valeur OCR.
    """
    if fv is None:
        return None
    for attr in ("confirmed_value", "corrected_value",
                 "normalized_value", "raw_value"):
        v = getattr(fv, attr, None)
        if v:
            return str(v)
    if isinstance(fv, str):
        return fv
    if isinstance(fv, dict):
        for k in ("confirmed_value", "corrected_value",
                  "normalized_value", "raw_value", "value"):
            if fv.get(k):
                return str(fv[k])
    return None


def _similarity(a: str, b: str, label_norm: str = "") -> float:
    """Similarité de nom entre 0 et 1 (préfixe, suffixe, inclusion)."""
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    score = 0.0
    if a.startswith(b) or b.startswith(a):
        score = max(score, 0.8)
    if a.endswith(b) or b.endswith(a):
        score = max(score, 0.8)
    if b in a or a in b:
        score = max(score, 0.7)
    if label_norm and (label_norm == a or label_norm == b):
        score = max(score, 0.9)
    # recouvrement de caractères (Jaccard sur bigrammes)
    ba, bb = _bigrams(a), _bigrams(b)
    if ba and bb:
        j = len(ba & bb) / len(ba | bb)
        score = max(score, round(j, 2))
    return score


def _bigrams(s: str) -> set:
    if len(s) < 2:
        return {s} if s else set()
    return {s[i:i + 2] for i in range(len(s) - 1)}
