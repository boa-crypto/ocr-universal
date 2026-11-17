"""Projection stricte de provenance locale, jamais copie du raw fournisseur."""
from __future__ import annotations

from .models import ConfidenceProvenance, EngineRun
from .ocr_engines import EngineOutput


def attach_confidence_provenance(run: EngineRun, output: EngineOutput) -> EngineRun:
    """Sans preuve compatible : run inchangé, sans inventer ni exposer de détail."""
    if run.engine != "baidu" or output.engine != "baidu" or not run.ok or not output.ok:
        return run
    if run.word_count != len(output.words) or run.mean_confidence != output.mean_confidence:
        return run
    if not isinstance(output.raw, dict) or "confidence" not in output.raw:
        return run
    try:
        provenance = ConfidenceProvenance.model_validate(output.raw["confidence"])
        return EngineRun.model_validate({
            **run.model_dump(), "confidence_provenance": provenance.model_dump(),
        })
    except (ValueError, TypeError):
        # Ne pas journaliser la ValidationError : elle peut inclure les données.
        return run
