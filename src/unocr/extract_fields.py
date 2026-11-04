"""Extraction de champs génériques et localisation géométrique par recherche floue.

Règle absolue : une valeur absente n'est jamais inventée → null / « non détecté ».
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Optional

from rapidfuzz import fuzz

from .logging_setup import get_logger
from .models import BBox, FieldStatus, FieldValue, PageResult, ValueOrigin, Word

log = get_logger("fields")


@dataclass
class PatternSpec:
    name: str
    label: str
    category: str
    regex: re.Pattern
    normalize: Optional[Callable[[str], str]] = None
    description: str = ""


# ---------------------------------------------------------------- normalisations
def _norm_date(m: str) -> str:
    from datetime import datetime
    s = m.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d",
                "%d/%m/%y", "%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return s


def _norm_amount(m: str) -> str:
    s = m.strip().replace(" ", "").replace("\u00a0", "")
    s = re.sub(r"[^\d,.\-+]", "", s)
    # format européen : 1.250,50 -> 1250.50
    if re.match(r"^-?\d{1,3}(\.\d{3})+,\d+$", s):
        s = s.replace(".", "").replace(",", ".")
    elif "," in s and "." not in s:
        s = s.replace(",", ".")
    return s


def _norm_phone(m: str) -> str:
    return re.sub(r"[^\d+]", "", m)


def _norm_generic(m: str) -> str:
    return re.sub(r"\s+", " ", m.strip())


DATE_RE = re.compile(
    r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}"
    r"|\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre"
    r"|January|February|March|April|May|June|July|August|September|October|November|December"
    r"|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})\b",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b")
URL_RE = re.compile(r"\b(?:https?://|www\.)[\w\-./?=&%#:~+]+", re.IGNORECASE)
PHONE_RE = re.compile(r"(?<![\w.])(?:\+?\d{1,3}[\s.\-]?)?(?:\(?\d{2,4}\)?[\s.\-]?){2,4}\d{2,4}(?![\w.])")
AMOUNT_RE = re.compile(
    r"(?<![\w.,])(?:\d{1,3}(?:[ .]\d{3})*(?:,\d{1,2})?|\d+(?:[.,]\d{1,2})?)"
    r"\s?(?:EUR|USD|DZD|DA|GBP|€|\$|£)"
    r"|(?:EUR|USD|DZD|GBP|€|\$|£)\s?"
    r"(?:\d{1,3}(?:[ .]\d{3})*(?:,\d{1,2})?|\d+(?:[.,]\d{1,2})?)",
    re.IGNORECASE,
)
PERCENT_RE = re.compile(r"(?<![\w.,])\d+(?:[.,]\d{1,2})?\s?%")
IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b")
INVOICE_NO_RE = re.compile(
    r"(?:\bfacture\b|\binvoice\b|\bbon de commande\b|\bpurchase order\b"
    r"|\br[ée]f[érence]*\b|\bref\b|\bn[°o](?![a-z])|\bno\.?(?![a-z]))"
    r"\s*[:#]?\s*(?!(?:invoice|facture|num[ée]ro|number|n[°o]\b|no\b|ref\b|B/?L\b)[:\s])([A-Z0-9][A-Z0-9\-/_.]{2,30})", re.IGNORECASE)
VAT_RE = re.compile(r"\b(?:TVA|VAT|IVA|MwSt\.?|BTW)\s*[:#]?\s*([A-Z]{0,2}\d{8,12})\b", re.IGNORECASE)
CONTAINER_RE = re.compile(r"\b([A-Z]{4}[\s-]?\d{7})\b")
HS_CODE_RE = re.compile(r"\b(\d{4}(?:[ .-]?\d{2}){0,2})\b(?=\s|$)")
SERIAL_RE = re.compile(r"(?:S[ée]rie|serial|S/N|SN)\s*[:#]?\s*([A-Z0-9\-/]{4,30})", re.IGNORECASE)
# Deux garde-fous sur le nombre :
#   — ne pas commencer au milieu d'un nombre à séparateur de milliers
#     (« 12 000 KG » rendait « 000 » comme quantité) ;
#   — accepter ces séparateurs DANS le nombre, pour rendre « 12 000 »
#     entier plutôt que rien.
QTY_UNIT_RE = re.compile(
    r"(?<![\w.,])(?<!\d[ .,\u00a0])"
    r"(\d{1,3}(?:[ .,\u00a0\u202f]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)"
    r"\s?(kg|g|t|T|L|m3|m²|m2|pcs|u|unit[éé]s?|cartons?|colis|CBM)\b",
    re.IGNORECASE)


GENERIC_PATTERNS: list[PatternSpec] = [
    PatternSpec("date", "Date", "dates", DATE_RE, _norm_date, "date (plusieurs formats)"),
    PatternSpec("email", "E-mail", "contacts", EMAIL_RE, _norm_generic),
    PatternSpec("url", "URL", "contacts", URL_RE, _norm_generic),
    PatternSpec("phone", "Téléphone", "contacts", PHONE_RE, _norm_phone),
    PatternSpec("iban", "IBAN", "identifiants", IBAN_RE, _norm_generic),
    PatternSpec("invoice_number", "Numéro de facture", "identifiants", INVOICE_NO_RE, _norm_generic),
    PatternSpec("vat_number", "N° TVA", "identifiants", VAT_RE, _norm_generic),
    PatternSpec("container_number", "N° conteneur", "identifiants", CONTAINER_RE, _norm_generic),
    PatternSpec("serial_number", "N° de série", "identifiants", SERIAL_RE, _norm_generic),
    PatternSpec("amount", "Montant", "numeriques", AMOUNT_RE, _norm_amount),
    PatternSpec("percent", "Pourcentage", "numeriques", PERCENT_RE, _norm_generic),
    PatternSpec("quantity", "Quantité + unité", "numeriques", QTY_UNIT_RE, _norm_generic),
]

CATEGORY_MAP = {
    "dates": ["date"],
    "contacts": ["email", "url", "phone"],
    "identifiants": ["iban", "invoice_number", "vat_number", "container_number", "serial_number"],
    "numeriques": ["amount", "percent", "quantity"],
}


# ---------------------------------------------------------------- localisation
def locate_value(pages: list[PageResult], value: str) -> tuple[Optional[int], Optional[BBox], float]:
    """Retourne (page, bbox, score) de la meilleure occurrence du champ dans les mots."""
    if not value:
        return None, None, 0.0
    needle = re.sub(r"\s+", " ", value.strip())
    best = (None, None, 0.0)
    for page in pages:
        for w in page.words:
            score = fuzz.partial_ratio(needle.lower(), w.text.lower()) / 100.0
            if score > best[2]:
                best = (page.page_num, w.bbox, score)
        # recherche multi-mots : concatène les glissières de mots
        texts = [w.text for w in page.words]
        joined = " ".join(texts)
        if needle and needle.lower() in joined.lower():
            idx = joined.lower().index(needle.lower())
            # retrouve les mots couvrant l'intervalle
            pos = 0
            sel: list[Word] = []
            for w in page.words:
                wlen = len(w.text) + 1
                if pos + wlen > idx and pos < idx + len(needle):
                    sel.append(w)
                pos += wlen
            if sel:
                bbox = BBox(
                    x0=min(w.bbox.x0 for w in sel), y0=min(w.bbox.y0 for w in sel),
                    x1=max(w.bbox.x1 for w in sel), y1=max(w.bbox.y1 for w in sel),
                )
                return page.page_num, bbox, 1.0
    return best if best[2] >= 0.75 else (None, None, best[2])


def extract_generic_fields(pages: list[PageResult],
                           patterns: list[PatternSpec] | None = None
                           ) -> tuple[dict[str, FieldValue], dict[str, list[str]]]:
    """Extrait les champs génériques. Multi-valeurs : liste jointe par ' | '."""
    patterns = patterns or GENERIC_PATTERNS
    fields: dict[str, FieldValue] = {}
    categories: dict[str, list[str]] = {k: [] for k in CATEGORY_MAP}

    full_by_page = [(p.page_num, p.text, p) for p in pages]
    for spec in patterns:
        found: list[tuple[str, int, float, float]] = []  # raw, page, engine_conf, global_conf
        for page_num, text, page in full_by_page:
            for m in spec.regex.finditer(text):
                raw = m.group(1) if m.groups() else m.group(0)
                raw = raw.strip()
                if not raw:
                    continue
                # confiance : moyenne des mots proches de la zone (approximation : confiance page)
                engine_conf = page.lines[0].confidence if page.lines else 1.0
                if page.words:
                    engine_conf = sum(w.confidence for w in page.words) / len(page.words)
                found.append((raw, page_num, engine_conf, engine_conf))

        if not found:
            fields[spec.name] = FieldValue(
                name=spec.name, label=spec.label, raw_value=None,
                status=FieldStatus.NOT_DETECTED, source="ocr", profile=None,
            )
            continue

        # déduplication en conservant l'ordre
        seen: list[str] = []
        for raw, page_num, econf, gconf in found:
            norm = spec.normalize(raw) if spec.normalize else raw
            if norm in seen:
                continue
            seen.append(norm)
        values = seen[:20]  # borne de sécurité
        page_num, bbox, loc_score = locate_value(pages, values[0])
        status = FieldStatus.DETECTED
        if loc_score < 0.8:
            status = FieldStatus.AMBIGUOUS
        fv = FieldValue(
            name=spec.name,
            label=spec.label,
            raw_value=" | ".join(values) if len(values) > 1 else values[0],
            normalized_value=" | ".join(values) if len(values) > 1 else values[0],
            value_origin=ValueOrigin.NORMALIZED,
            source="ocr",
            confidence=round(min(1.0, (found[0][3] * 0.7 + loc_score * 0.3)), 3),
            engine_confidence=round(found[0][2], 3),
            page_num=page_num,
            bbox=bbox,
            status=status,
            pattern=spec.name,
        )
        fields[spec.name] = fv
        for cat, names in CATEGORY_MAP.items():
            if spec.name in names:
                categories[cat].append(spec.name)
    return fields, categories
