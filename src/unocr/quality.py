"""Contrôle qualité : confiances, anomalies, désaccords moteurs, cohérence.

Distinction stricte :
- `engine_confidence` : celle du moteur OCR (Tesseract, natif…),
- `global_confidence` : calculée par le système (qualité page × confiance moteur).
"""
from __future__ import annotations

import re
from typing import Any

from .models import (
    Anomaly,
    Disagreement,
    DocumentResult,
    FieldStatus,
    PageResult,
    QualityReport,
)
from .security import flag_untrusted_content


# facteur qualité : flou / résolution / éclairage borné [0.5, 1.0]
def page_quality_factor(page: PageResult) -> float:
    q = page.quality
    f = 1.0
    if q.blur_score and q.blur_score < 100:
        f *= max(0.6, q.blur_score / 100.0)
    if q.estimated_dpi and q.estimated_dpi < 150:
        f *= max(0.7, q.estimated_dpi / 200.0)
    if q.contrast and q.contrast < 35:
        f *= 0.85
    if "dark" in q.issues or "overexposed" in q.issues:
        f *= 0.9
    return max(0.5, min(1.0, f))


def global_confidence(engine_conf: float, page: PageResult,
                      disagreement: bool = False) -> float:
    f = page_quality_factor(page)
    if disagreement:
        f *= 0.85
    return max(0.0, min(1.0, engine_conf * f))


def build_quality_report(result: DocumentResult,
                         review_threshold: float = 0.7) -> QualityReport:
    pages = result.pages
    engine_confs, global_confs = [], []
    low_pages = []
    for p in pages:
        if p.words:
            ec = sum(w.confidence for w in p.words) / len(p.words)
            engine_confs.append(ec)
            g = global_confidence(ec, p)
            global_confs.append(g)
            if g < review_threshold:
                low_pages.append(p.page_num)
        elif p.blank:
            continue
        elif p.text.strip():  # texte numérique sans mots OCR (politique historique)
            engine_confs.append(0.95)
            global_confs.append(0.95)
        else:
            # Page non déclarée vide sans sortie exploitable : ne pas masquer
            # cet échec dans la moyenne d'un document mixte. Zéro conservateur,
            # pas score mesuré. Revue requise même si le seuil vaut zéro.
            engine_confs.append(0.0)
            global_confs.append(0.0)
            low_pages.append(p.page_num)

    low_fields = [k for k, v in result.fields.items()
                  if v.confidence < review_threshold
                  and v.status not in (FieldStatus.NOT_DETECTED,)]

    anomalies: list[Anomaly] = []
    # anomalies de page
    for p in pages:
        for issue in p.quality.issues:
            severity = "warning" if issue in {"blurry", "dark", "skewed", "low_resolution"} else "info"
            anomalies.append(Anomaly(
                code=f"PAGE_{issue.upper()}", severity=severity,
                message=f"page {p.page_num} : {issue}",
                page_num=p.page_num,
                context={"blur": p.quality.blur_score, "dpi": p.quality.estimated_dpi},
            ))
        if p.quality.is_blank:
            anomalies.append(Anomaly(code="EMPTY_PAGE", severity="info",
                                     message=f"page {p.page_num} vide ou quasi vide",
                                     page_num=p.page_num))
        if not p.blank and not p.text.strip():
            anomalies.append(Anomaly(code="OCR_FAILED", severity="error",
                                     message=f"aucun texte reconnu page {p.page_num}",
                                     page_num=p.page_num))

    # ambiguïté de caractères dans les identifiants critiques
    AMBIG = re.compile(r"[OoIl1|]{2,}")
    for name, fv in result.fields.items():
        for anc in fv.anomalies:
            if anc.startswith("validator:"):
                anomalies.append(Anomaly(
                    code="INVALID_FORMAT", severity="warning",
                    message=f"champ '{name}' : {anc}", page_num=fv.page_num, bbox=fv.bbox))
        if fv.status == FieldStatus.AMBIGUOUS:
            anomalies.append(Anomaly(
                code="AMBIGUOUS_VALUE", severity="warning",
                message=f"champ '{name}' ambigu : {fv.raw_value}", page_num=fv.page_num))
        if fv.raw_value and AMBIG.search(fv.raw_value) and re.search(r"\d", fv.raw_value or ""):
            anomalies.append(Anomaly(
                code="AMBIGUOUS_CHARS", severity="info",
                message=f"champ '{name}' : caractères ambigus (O/0, I/l/1) dans {fv.raw_value}",
                page_num=fv.page_num, bbox=fv.bbox))
        if fv.status == FieldStatus.NOT_DETECTED and name in _required_fields(result):
            anomalies.append(Anomaly(
                code="MISSING_REQUIRED_FIELD", severity="error",
                message=f"champ obligatoire absent : {name}"))

    # contenu non fiable (injection de prompt) : signalé, jamais exécuté
    for p in pages:
        hits = flag_untrusted_content(p.text)
        for h in hits:
            anomalies.append(Anomaly(
                code="UNTRUSTED_CONTENT", severity="warning",
                message=f"page {p.page_num} : contenu ressemblant à une instruction injectée ({h!r}) — ignoré",
                page_num=p.page_num))

    # désaccords moteurs collectés dans les runs
    disagreements: list[Disagreement] = []
    for d in result.quality.disagreements:
        disagreements.append(d)

    checks: list[dict[str, Any]] = list(result.quality.checks)

    mean_ec = sum(engine_confs) / len(engine_confs) if engine_confs else 0.0
    mean_gc = sum(global_confs) / len(global_confs) if global_confs else 0.0
    return QualityReport(
        mean_engine_confidence=round(mean_ec, 3),
        mean_global_confidence=round(mean_gc, 3),
        pages_low_confidence=low_pages,
        fields_low_confidence=low_fields,
        anomalies=anomalies,
        disagreements=disagreements,
        checks=checks,
    )


def _required_fields(result: DocumentResult) -> set[str]:
    return set(result.categories.get("_required", []))
