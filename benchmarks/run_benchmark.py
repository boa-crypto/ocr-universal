"""Benchmark reproductible UniOCR.

Mesure réelle sur le jeu de fixtures (généré + vérité terrain écrite à la main) :
- CER (Character Error Rate) et WER (Word Error Rate) par distance de Levenshtein,
- exactitude des champs,
- exactitude de reconstruction des tableaux,
- temps de traitement par page,
- mémoire maximale (RSS),
- taux d'extractions nécessitant une validation humaine.

Aucun score n'est inventé : tout est calculé ici, sur la taille de jeu indiquée.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from make_fixtures import FIXTURES, make_all

from unocr.config import load_config, set_config
from unocr.models import JobOptions
from unocr.pipeline import Pipeline


def levenshtein(a: str, b: str) -> int:
    from rapidfuzz.distance import Levenshtein
    return Levenshtein.distance(a, b)


def _norm_text(s: str) -> str:
    """Normalisation pour la mesure : espaces uniques, séparateurs de tableau neutres."""
    import re
    return re.sub(r"\s+", " ", s.replace("|", " ").replace("\t", " ")).strip()


def cer(ref: str, hyp: str) -> float:
    ref, hyp = _norm_text(ref), _norm_text(hyp)
    if not ref:
        return 0.0 if not hyp else 1.0
    return levenshtein(ref, hyp) / max(1, len(ref))


def wer(ref: str, hyp: str) -> float:
    r, h = _norm_text(ref).split(), _norm_text(hyp).split()
    if not r:
        return 0.0 if not h else 1.0
    from rapidfuzz.distance import Levenshtein as L
    return L.distance(r, h) / max(1, len(r))


def main() -> int:
    make_all()
    gt = json.loads((FIXTURES / "ground_truth.json").read_text(encoding="utf-8"))
    cfg = load_config()
    set_config(cfg)
    pipeline = Pipeline(cfg)

    try:
        import os

        import psutil
        proc = psutil.Process(os.getpid())
        mem_before = proc.memory_info().rss
    except Exception:
        proc = None
        mem_before = 0

    cases = [
        ("text_pdf.pdf", "invoice", True),      # PDF natif
        ("scanned_pdf.pdf", "generic", True),   # PDF scanné (OCR réel)
        ("bl_port.pdf", "port_bl", True),       # profil portuaire
        ("skewed.png", "generic", True),        # image inclinée
        ("dark.png", "generic", True),          # image sombre
        ("table_pdf.pdf", "generic", True),     # tableau
        ("qr_code.png", "generic", False),      # codes-barres
        ("letter.docx", "generic", False),      # doc numérique
        ("data.csv", "generic", False),         # tableur
    ]

    report_rows = []
    all_cer, all_wer = [], []
    fields_total = fields_hit = 0
    human_review = 0
    fields_evaluated = 0

    for fname, profile, compute_text_score in cases:
        t0 = time.perf_counter()
        try:
            result = pipeline.process_file(
                FIXTURES / fname,
                JobOptions(profile=profile, quality_mode="accurate",
                           export_formats=["json"]))
        except Exception as exc:
            report_rows.append({"file": fname, "error": str(exc)})
            continue
        dt = (time.perf_counter() - t0) * 1000
        pages = max(1, len(result.pages))
        row = {
            "file": fname,
            "profile": profile,
            "pages": len(result.pages),
            "ms_total": round(dt, 1),
            "ms_per_page": round(dt / pages, 1),
            "engine_confidence": result.quality.mean_engine_confidence,
            "global_confidence": result.quality.mean_global_confidence,
            "anomalies": len(result.quality.anomalies),
            "tables": len(result.tables),
            "barcodes": len(result.barcodes),
        }
        if compute_text_score and fname in gt:
            ref = gt[fname]
            hyp = "\n".join(p.text for p in result.pages)
            c, w = cer(ref, hyp), wer(ref, hyp)
            row["cer"] = round(c, 4)
            row["wer"] = round(w, 4)
            all_cer.append(c)
            all_wer.append(w)
        report_rows.append(row)

        # exactitude des champs sur le profil portuaire (vérité terrain BL)
        if fname == "bl_port.pdf":
            expected = {
                "container_number": "CSQU3054383",
                "bl_number": "MSCU123456789",
                "vessel_name": "MSC AURORA",
                "port_of_loading": "ALGER",
                "port_of_discharge": "HAMBURG",
                "gross_weight": "8500",
                "hs_code": "847130",
            }
            for k, v in expected.items():
                fields_total += 1
                fields_evaluated += 1
                fv = result.fields.get(k)
                val = (fv.value or "") if fv else ""
                if k == "gross_weight":
                    ok = val.startswith("8500")
                elif k == "hs_code":
                    ok = "847130" in val.replace(" ", "").replace(".", "")
                elif k in ("port_of_loading", "port_of_discharge"):
                    ok = val.upper().startswith(v)
                else:
                    ok = val.upper().replace(" ", "") == v.replace(" ", "")
                if ok:
                    fields_hit += 1
                if fv and fv.status.value in ("ambiguous", "invalid"):
                    human_review += 1

    mem_peak = proc.memory_info().rss if proc else 0
    summary = {
        "dataset_size_files": len(cases),
        "dataset_note": "jeu généré programmatiquement avec vérité terrain (tests/make_fixtures.py)",
        "mean_cer": round(sum(all_cer) / len(all_cer), 4) if all_cer else None,
        "mean_wer": round(sum(all_wer) / len(all_wer), 4) if all_wer else None,
        "text_scored_files": len(all_cer),
        "field_accuracy": round(fields_hit / fields_total, 4) if fields_total else None,
        "fields_evaluated": fields_evaluated,
        "fields_needing_human_review": human_review,
        "memory_rss_start_mb": round(mem_before / 1e6, 1),
        "memory_rss_end_mb": round(mem_peak / 1e6, 1),
        "results": report_rows,
    }

    out_dir = ROOT / "benchmarks" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    (out_dir / f"benchmark_{stamp}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    md = ["# Résultats de benchmark UniOCR", "",
          f"- Date : {time.strftime('%Y-%m-%d %H:%M:%S')}",
          f"- Taille du jeu : {summary['dataset_size_files']} fichiers",
          f"- CER moyen : {summary['mean_cer']}",
          f"- WER moyen : {summary['mean_wer']}",
          f"- Exactitude des champs (profil BL) : {summary['field_accuracy']} "
          f"({fields_hit}/{fields_total})",
          f"- Champs nécessitant une revue humaine : {human_review}/{fields_evaluated}",
          f"- Mémoire RSS fin de run : {summary['memory_rss_end_mb']} Mo", "",
          "| fichier | pages | ms/page | CER | WER | conf. moteur | conf. globale |",
          "|---|---|---|---|---|---|---|"]
    for r in report_rows:
        if "error" in r:
            md.append(f"| {r['file']} | ERREUR: {r['error']} | | | | | |")
        else:
            md.append(f"| {r['file']} | {r['pages']} | {r['ms_per_page']} | "
                      f"{r.get('cer', '—')} | {r.get('wer', '—')} | "
                      f"{r['engine_confidence']} | {r['global_confidence']} |")
    md += ["", "## Limites", "",
           "- Le jeu est synthétique (documents générés) : les scores mesurés ne sont",
           "  pas une promesse de performance sur documents réels.",
           "- CER/WER ne sont calculés que sur les documents avec vérité terrain texte.",
           "- Normalisation de mesure : espaces uniques et séparateurs « | » neutralisés",
           "  des deux côtés (référence et hypothèse) avant calcul des distances.",
           "- Environnement : 2 CPU, 2 Go RAM, sans GPU."]
    (out_dir / f"benchmark_{stamp}.md").write_text("\n".join(md), encoding="utf-8")
    (out_dir / "latest.md").write_text("\n".join(md), encoding="utf-8")
    (out_dir / "latest.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n".join(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
