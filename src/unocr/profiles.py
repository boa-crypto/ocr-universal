"""Profils métier configurables (JSON) + validateurs de format.

Un profil définit : champs recherchés, formats, règles de validation, champs
obligatoires, relations, contrôles de cohérence, règles d'exportation.
Ajouter un profil n'exige aucune modification du noyau.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field

from .logging_setup import get_logger
from .models import FieldStatus, FieldValue, ValueOrigin

log = get_logger("profiles")


# ---------------------------------------------------------------- validateurs
# Table ISO 6346 : A-Z -> 10..38 en sautant les multiples de 11 (11, 22, 33),
# chiffres -> leur valeur numérique.
_ISO6346_VALUES: dict[str, int] = {str(d): d for d in range(10)}
_letter_values = [v for v in range(10, 39) if v % 11 != 0]
for _c, _v in zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", _letter_values):
    _ISO6346_VALUES[_c] = _v


def iso6346_check_digit_ok(container: str) -> Optional[bool]:
    """Vérifie le chiffre de contrôle ISO 6346 d'un numéro de conteneur.

    Retourne True/False, ou None si le format n'est pas vérifiable.
    Ne transforme jamais une hypothèse en certitude : un numéro qui « ressemble »
    à un conteneur n'est pas déclaré valide sans passer ce contrôle.
    """
    m = re.match(r"^([A-Z]{3})([UJZ])(\d{6})(\d)$", re.sub(r"[\s-]", "", container.upper()))
    if not m:
        return None
    owner, cat, serial, check = m.groups()
    chars = owner + cat + serial
    total = 0
    for i, ch in enumerate(chars):
        val = _ISO6346_VALUES.get(ch)
        if val is None:
            return None
        total += val * (2 ** i)
    computed = total % 11
    if computed == 10:
        computed = 0
    return computed == int(check)


def luhn_ok(digits: str) -> Optional[bool]:
    s = re.sub(r"\D", "", digits or "")
    if len(s) < 12:
        return None
    total, alt = 0, False
    for ch in reversed(s):
        d = int(ch)
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0


def iban_ok(iban: str) -> Optional[bool]:
    s = re.sub(r"\s", "", (iban or "").upper())
    if not re.match(r"^[A-Z]{2}\d{2}[A-Z0-9]{10,30}$", s):
        return None
    rearranged = s[4:] + s[:4]
    digits = "".join(str(int(c, 36)) for c in rearranged)
    return int(digits) % 97 == 1


def date_iso_ok(value: str) -> Optional[bool]:
    from datetime import date
    try:
        date.fromisoformat((value or "").strip()[:10])
        return True
    except ValueError:
        return False if value else None


def container_type_ok(value: str) -> Optional[bool]:
    """Format ISO 6346 type code : 4 chars (2 lettres + 2 chiffres), ex. 22G1, 45R1."""
    return bool(re.match(r"^\d{2}[A-Z]\d$", (value or "").strip().upper())) or None


def not_empty(value: str) -> Optional[bool]:
    return bool((value or "").strip()) or None


def plate_number_ok(value: str) -> Optional[bool]:
    """Valide une plaque d'immatriculation : voir plate_format() (ci-dessous)."""
    return plate_format(value)[1]


def _plate_clean(value: str) -> str:
    return re.sub(r"[\s.\-_/·•|]+", "", (value or "").upper())


def _es_check(m: re.Match) -> bool:
    # espagnole récente : 4 chiffres + 3 consonnes (pas de voyelles)
    return not re.search(r"[AEIOU]", m.group(2))


def _dz_check(m: re.Match) -> bool:
    # algérienne : wilaya 01–58
    return 1 <= int(m.group(3)) <= 58


def _tr_check(m: re.Match) -> bool:
    # turque : province 01–81
    return 1 <= int(m.group(1)) <= 81


def _fr_siv_check(m: re.Match) -> bool:
    # SIV français : I, O, U exclus des lettres de série
    return not re.search(r"[IOU]", m.group(1) + m.group(3))


# formats codifiés : (nom, regex pleine chaîne sans séparateurs, contrôle interne).
# L'ordre compte : du plus spécifique au plus générique.
PLATE_FORMATS: list[tuple[str, "re.Pattern[str]", Any]] = [
    ("fr_siv", re.compile(r"([A-Z]{2})(\d{3})([A-Z]{2})"), _fr_siv_check),
    ("es", re.compile(r"(\d{4})([A-Z]{3})"), _es_check),
    ("uk", re.compile(r"(?:[A-Z]{2}\d{2}[A-Z]{3}|[A-Z]\d{3}[A-Z]{3})"), None),
    ("be", re.compile(r"[1-7][A-Z]{3}\d{2,3}"), None),
    ("pt_nl", re.compile(r"(?:[A-Z]{2}\d{2}[A-Z]{2}|\d{2}[A-Z]{2}\d{2})"), None),
    ("fr_fni", re.compile(r"[A-Z]{1,2}\d{2,3}[A-Z]{2}"), None),
    ("it", re.compile(r"[A-Z]{2}\d{3}[A-Z]{2}"), None),
    ("de", re.compile(r"[A-Z]{1,3}[A-Z]{1,2}\d{1,4}"), None),
    ("tr", re.compile(r"(\d{2})[A-Z]{1,3}(\d{2,4})"), _tr_check),
    ("dz", re.compile(r"(\d{3,6})([A-Z\u0621-\u064A]{1,2})(\d{2})"), _dz_check),
    ("ma", re.compile(r"\d{1,5}[A-Z]\d{1,2}"), None),
    ("tn", re.compile(r"\d{1,4}[A-Z\u0621-\u064A]{2,10}\d{1,2}"), None),
]


def plate_format(value: str) -> tuple[Optional[str], Optional[bool]]:
    """Identifie le format d'une plaque et juge sa validité interne.

    Retourne (format, verdict) :
    True  = format reconnu et règles internes respectées ;
    False = format reconnu mais règle universelle violée (ex. wilaya algérienne
            hors 01–58, voyelle dans une série espagnole récente, province
            turque hors 01–81) ;
    None  = format inconnu — jamais déclaré valide ni invalide (→ AMBIGUOUS).

    Un format dont la règle interne échoue ne conclut pas s'il reste un autre
    format candidat : on ne déclare « invalide » que lorsqu'aucune alternative
    ne tient.
    """
    v = _plate_clean(value)
    if not v:
        return None, False
    first_fail: Optional[tuple[str, bool]] = None
    for name, pat, check in PLATE_FORMATS:
        m = pat.fullmatch(v)
        if not m:
            continue
        verdict = check(m) if check else True
        if verdict:
            return name, True
        if first_fail is None:
            first_fail = (name, False)
    if first_fail:
        return first_fail
    return None, None


def vin_ok(value: str) -> Optional[bool]:
    """Valide un n° de châssis VIN (ISO 3779 : 17 caractères, sans I, O, Q).

    True  = longueur et alphabet conformes ;
    False = 17 caractères mais alphabet violé (I/O/Q ou symbole) ;
    None  = longueur ≠ 17 : lecture probablement partielle — non vérifiable.
    """
    s = re.sub(r"\s", "", (value or "").upper())
    if not s:
        return False
    if len(s) != 17:
        return None
    if re.fullmatch(r"[A-HJ-NPR-Z0-9]{17}", s):
        return True
    return False


_VIN_TRANSLIT = {**{str(d): d for d in range(10)},
                 "A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7, "H": 8,
                 "J": 1, "K": 2, "L": 3, "M": 4, "N": 5, "P": 7, "R": 9, "S": 2,
                 "T": 3, "U": 4, "V": 5, "W": 6, "X": 7, "Y": 8, "Z": 9}
_VIN_WEIGHTS = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]


def vin_check_ok(value: str) -> Optional[bool]:
    """Check digit du VIN (position 9, obligation nord-américaine).

    True  = check digit conforme (VIN d'Amérique du Nord : 1er caractère 1–5) ;
    False = check digit faux — lecture OCR probablement erronée à une position ;
    None  = règle non applicable (VIN non nord-américain, longueur ≠ 17) :
            ne tranche rien.
    """
    s = re.sub(r"\s", "", (value or "").upper())
    if len(s) != 17 or not re.fullmatch(r"[A-HJ-NPR-Z0-9]{17}", s):
        return None
    if s[0] not in "12345":
        return None   # hors Amérique du Nord : la position 9 n'est pas un check digit
    try:
        total = sum(_VIN_TRANSLIT[c] * w for c, w in zip(s, _VIN_WEIGHTS))
    except KeyError:
        return None
    r = total % 11
    want = "X" if r == 10 else str(r)
    return want == s[8]


def _strip_accents(s: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


_ENERGY_TERMS = (
    "ESSENCE", "SANS PLOMB", "SUPER", "SP95", "SP98", "DIESEL", "GAZOLE",
    "ELECTRI", "HYBRID", "GPL", "ETHANOL", "E85", "HYDROGEN", "GAZ NATUREL",
    "CNG", "LPG", "PETROLE",
)


def energy_ok(value: str) -> Optional[bool]:
    """Valide une valeur d'énergie / carburant (carte grise).

    True  = terme ou code d'énergie connu ;
    None  = terme inconnu — jamais déclaré valide ni invalide (→ AMBIGUOUS).
    """
    v = re.sub(r"\s+", " ", _strip_accents(value or "").upper()).strip(" .:")
    if not v:
        return False
    if v in {"ES", "GO", "GPL", "EE", "EH", "EL", "EP", "GN", "FE", "NE", "H2"}:
        return True
    for term in ("ESSENCE", "SANS PLOMB", "SUPER", "DIESEL", "GAZOLE",
                 "ELECTRI", "HYBRID", "GPL", "ETHANOL", "E85", "HYDROGEN",
                 "GAZ NATUREL", "CNG", "LPG", "PETROLE"):
        if term in v:
            return True
    return None


VALIDATORS: dict[str, Callable[[str], Optional[bool]]] = {
    "iso6346": iso6346_check_digit_ok,
    "luhn": luhn_ok,
    "iban": iban_ok,
    "date_iso": date_iso_ok,
    "container_type": container_type_ok,
    "not_empty": not_empty,
    "plate": plate_number_ok,
    "vin": vin_ok,
    "vin_check": vin_check_ok,
    "energy": energy_ok,
}

# validateurs « auxiliaires » : ne parlent que s'ils ont la preuve.
# False = alerte (INVALID) ; True/None = aucun effet sur le statut
# (None signifie « règle non applicable », ex. check digit VIN hors Amérique
# du Nord) — contrairement aux validateurs principaux où None → AMBIGUOUS.
AUX_VALIDATORS = {"vin_check"}


# ---------------------------------------------------------------- schéma profil
class ProfileField(BaseModel):
    key: str
    label: str = ""
    patterns: list[str] = Field(default_factory=list)   # regex avec groupe 1
    required: bool = False
    validators: list[str] = Field(default_factory=list)
    normalize: Optional[str] = None       # nom de normalisation (generic | upper | digits | date | amount)
    category: str = "general"
    multiline: bool = False


class Profile(BaseModel):
    name: str
    label: str = ""
    description: str = ""
    document_types: list[str] = Field(default_factory=list)
    fields: list[ProfileField] = Field(default_factory=list)
    relations: list[dict[str, Any]] = Field(default_factory=list)
    consistency_checks: list[dict[str, Any]] = Field(default_factory=list)
    export_rules: dict[str, Any] = Field(default_factory=dict)

    def field_map(self) -> dict[str, ProfileField]:
        return {f.key: f for f in self.fields}


NORMALIZERS: dict[str, Callable[[str], str]] = {
    "generic": lambda s: re.sub(r"\s+", " ", s.strip()),
    "upper": lambda s: re.sub(r"\s+", " ", s.strip().upper()),
    "digits": lambda s: re.sub(r"\D", "", s),
    "date": None,    # rempli ci-dessous (conversion ISO)
    "amount": None,  # rempli ci-dessous
}


def _init_normalizers() -> None:
    from .extract_fields import _norm_amount, _norm_date
    NORMALIZERS["date"] = _norm_date
    NORMALIZERS["amount"] = _norm_amount


_init_normalizers()


def load_profile(path: Path) -> Profile:
    data = json.loads(path.read_text(encoding="utf-8"))
    return Profile.model_validate(data)


def load_profiles(profiles_dir: Path) -> dict[str, Profile]:
    out: dict[str, Profile] = {}
    if profiles_dir.is_dir():
        for p in sorted(profiles_dir.glob("*.json")):
            try:
                prof = load_profile(p)
                out[prof.name] = prof
            except Exception:
                log.exception("profil invalide ignoré: %s", p.name)
    return out


# ---------------------------------------------------------------- application
def apply_profile(text: str, profile: Profile, page_num: int | None = None,
                  locate=None) -> dict[str, FieldValue]:
    """Applique un profil au texte. `locate(value)` localise géométriquement si fourni.

    Valeur absente → status=not_detected, valeur None. Jamais d'invention.
    """
    results: dict[str, FieldValue] = {}
    for pf in profile.fields:
        raw: Optional[str] = None
        used_pattern: Optional[str] = None
        for pat in pf.patterns:
            try:
                if pf.multiline:
                    # champ répétable (ex. plusieurs conteneurs) : toutes les
                    # occurrences sont gardées, dédoublonnées et réunies.
                    trouves: list[str] = []
                    for m in re.finditer(pat, text, re.IGNORECASE | re.MULTILINE):
                        valeur = (m.group(1) if m.groups() else m.group(0)).strip()
                        if valeur and valeur not in trouves:
                            trouves.append(valeur)
                    if trouves:
                        raw = " | ".join(trouves)
                        used_pattern = pat
                        break
                    continue
                m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
            except re.error:
                log.warning("regex invalide dans le profil %s: %s", profile.name, pat)
                continue
            if m:
                raw = (m.group(1) if m.groups() else m.group(0)).strip()
                used_pattern = pat
                break

        if raw is None:
            results[pf.key] = FieldValue(
                name=pf.key, label=pf.label or pf.key,
                raw_value=None,
                status=FieldStatus.NOT_DETECTED,
                source="rule", profile=profile.name,
            )
            continue

        norm_fn = NORMALIZERS.get(pf.normalize or "generic")
        normalized = norm_fn(raw) if norm_fn else raw
        corrected: Optional[str] = None
        anomalies: list[str] = []
        status = FieldStatus.DETECTED

        for vname in pf.validators:
            fn = VALIDATORS.get(vname)
            if not fn:
                continue
            ok = fn(normalized)
            if ok is False:
                status = FieldStatus.INVALID
                anomalies.append(f"validator:{vname}:failed")
            elif ok is None and vname not in AUX_VALIDATORS:
                # non vérifiable (iso6346, plaque inconnue, VIN partiel…) :
                # jamais déclaré valide — signalé ambigu
                status = FieldStatus.AMBIGUOUS
                anomalies.append(f"validator:{vname}:unverifiable")

        page, bbox, score = (None, None, 0.0)
        if locate is not None:
            page, bbox, score = locate(raw)
        conf = 0.5 + 0.5 * min(1.0, score or 0.0) if bbox else 0.5

        results[pf.key] = FieldValue(
            name=pf.key,
            label=pf.label or pf.key,
            raw_value=raw,
            normalized_value=normalized,
            corrected_value=corrected,
            value_origin=ValueOrigin.NORMALIZED,
            source="rule",
            confidence=round(conf, 3),
            engine_confidence=round(conf, 3),
            page_num=page,
            bbox=bbox,
            status=status,
            pattern=used_pattern,
            anomalies=anomalies,
            profile=profile.name,
        )
    return results


def check_required(profile: Profile, fields: dict[str, FieldValue]) -> list[dict]:
    """Contrôle des champs obligatoires + relations inter-champs."""
    issues = []
    for pf in profile.fields:
        if pf.required:
            fv = fields.get(pf.key)
            if fv is None or fv.status == FieldStatus.NOT_DETECTED or fv.value is None:
                issues.append({"code": "MISSING_REQUIRED_FIELD",
                               "severity": "error",
                               "field": pf.key,
                               "message": f"champ obligatoire absent : {pf.label or pf.key}"})
    for rel in profile.relations:
        kind = rel.get("type")
        if kind == "date_order":
            a = fields.get(rel.get("before", ""))
            b = fields.get(rel.get("after", ""))
            if a and b and a.normalized_value and b.normalized_value:
                if str(b.normalized_value)[:10] < str(a.normalized_value)[:10]:
                    issues.append({"code": "DATE_INCOHERENT", "severity": "warning",
                                   "fields": [a.name, b.name],
                                   "message": rel.get("message", "dates incohérentes")})
        elif kind == "sum_equals":
            total = fields.get(rel.get("total", ""))
            parts = [fields.get(k) for k in rel.get("parts", [])]
            if total and total.normalized_value and all(p and p.normalized_value for p in parts):
                try:
                    tval = float(re.sub(r"[^\d.\-]", "", total.normalized_value) or "nan")
                    sval = sum(float(re.sub(r"[^\d.\-]", "", p.normalized_value)) for p in parts if p)
                    if tval == tval and abs(tval - sval) > 0.02:
                        issues.append({"code": "SUM_MISMATCH", "severity": "warning",
                                       "message": f"{rel.get('total')} != somme des parties"})
                except ValueError:
                    pass
    return issues


def load_all_profiles(profiles_dir: Path,
                      user_dir: Path | None = None) -> dict[str, Profile]:
    """Profils livrés + profils utilisateur.

    Les profils utilisateur (`data/profiles/`) sont chargés en second et
    **priment** sur les profils livrés de même nom. Un profil utilisateur
    invalide est ignoré (journalisé) plutôt que de faire échouer le chargement.
    """
    out = load_profiles(profiles_dir)
    if user_dir is None:
        return out
    for name, prof in load_profiles(user_dir).items():
        out[name] = prof
    return out
