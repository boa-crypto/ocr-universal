"""Benchmark « terrain » : mesure CER/WER + précision des champs sur photos.

Deux sources :
1. --suite synth (défaut) : échantillons synthétiques dégradés générés par
   make_field_samples.py. Les chiffres obtenus décrivent des CONDITIONS
   simulées — ce ne sont PAS des mesures sur site.
2. --suite real : VRAIES photos déposées dans benchmarks/field/ avec un
   ground_truth.json :

   {
     "ma_photo.jpg": {
       "profile": "container",
       "text": "texte attendu pour le CER (optionnel)",
       "fields": {"container_number": "CSQU3054383"}
     }
   }

   Aucune photo réelle fournie → le rapport l'écrit explicitement et aucun
   chiffre « terrain réel » n'est produit.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from unocr.models import JobOptions
from unocr.pipeline import Pipeline


def _norm(s: str) -> str:
    return " ".join((s or "").split())


def cer(ref: str, hyp: str) -> float:
    ref, hyp = _norm(ref), _norm(hyp)
    if not ref:
        return 0.0 if not hyp else 1.0
    # distance de Levenshtein (matrice)
    m, n = len(ref), len(hyp)
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        cur = [i] + [0] * n
        for j in range(1, n + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1,
                         prev[j - 1] + (ref[i - 1] != hyp[j - 1]))
        prev = cur
    return prev[n] / max(1, len(ref))


def wer(ref: str, hyp: str) -> float:
    ref_w, hyp_w = _norm(ref).split(), _norm(hyp).split()
    if not ref_w:
        return 0.0 if not hyp_w else 1.0
    m, n = len(ref_w), len(hyp_w)
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        cur = [i] + [0] * n
        for j in range(1, n + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1,
                         prev[j - 1] + (ref_w[i - 1] != hyp_w[j - 1]))
        prev = cur
    return prev[n] / max(1, len(ref_w))


def evaluate(samples_dir: Path, gt_path: Path, label: str) -> dict:
    gt = json.loads(gt_path.read_text(encoding="utf-8"))
    pipeline = Pipeline()
    rows = []
    for fname, expect in sorted(gt.items()):
        path = samples_dir / fname
        if not path.is_file():
            continue
        t0 = time.perf_counter()
        res = pipeline.process_file(
            path, JobOptions(profile=expect.get("profile", "generic"),
                             quality_mode="fast"))
        dt = time.perf_counter() - t0
        row = {"file": fname, "variant": expect.get("variant", "real"),
               "seconds": round(dt, 2)}
        if expect.get("text"):
            row["cer"] = round(cer(expect["text"], res.pages[0].text), 4)
            row["wer"] = round(wer(expect["text"], res.pages[0].text), 4)
        fields = expect.get("fields", {})
        if fields:
            hits, det = 0, 0
            detail = {}
            for key, want in fields.items():
                fv = res.fields.get(key)
                got = _norm(fv.normalized_value or fv.raw_value or "") if fv else ""
                ok = got.replace(" ", "") == _norm(want).replace(" ", "")
                hits += ok
                det += bool(got)
                detail[key] = {"attendu": want, "obtenu": got or None, "exact": ok}
            row["fields_exact"] = f"{hits}/{len(fields)}"
            row["fields_detected"] = f"{det}/{len(fields)}"
            row["field_detail"] = detail
        rows.append(row)

    out = {"suite": label, "samples": len(rows), "rows": rows}
    cers = [r["cer"] for r in rows if "cer" in r]
    wers = [r["wer"] for r in rows if "wer" in r]
    if cers:
        out["mean_cer"] = round(sum(cers) / len(cers), 4)
        out["mean_wer"] = round(sum(wers) / len(wers), 4)
    tot = sum(int(r["fields_exact"].split("/")[1]) for r in rows if "fields_exact" in r)
    hit = sum(int(r["fields_exact"].split("/")[0]) for r in rows if "fields_exact" in r)
    if tot:
        out["field_accuracy"] = f"{hit}/{tot}"
    return out


def to_markdown(res: dict) -> str:
    lines = [f"# Benchmark terrain — suite « {res['suite']} »", ""]
    if res["suite"] == "synth":
        lines += ["> **Échantillons synthétiques dégradés** (rotation, perspective,",
                  "> flou, bruit, faible lumière). Conditions terrain *simulées* —",
                  "> ce ne sont pas des mesures sur photos réelles.", ""]
    else:
        lines += ["> Suite **photos réelles** (fournies par l'utilisateur).", ""]
    lines.append(f"- Échantillons évalués : {res['samples']}")
    if "mean_cer" in res:
        lines.append(f"- CER moyen : **{res['mean_cer']}** — WER moyen : **{res['mean_wer']}**")
    if "field_accuracy" in res:
        lines.append(f"- Champs exacts : **{res['field_accuracy']}**")
    lines += ["", "| fichier | variante | CER | WER | champs exacts | secondes |",
              "|---|---|---|---|---|---|"]
    for r in res["rows"]:
        lines.append(f"| {r['file']} | {r['variant']} | {r.get('cer', '—')} "
                     f"| {r.get('wer', '—')} | {r.get('fields_exact', '—')} "
                     f"| {r['seconds']} |")
    return "\n".join(lines) + "\n"


def init_template(field_dir: Path) -> Path:
    """Crée/remet à jour ground_truth.json à partir des photos présentes."""
    photos = sorted(p for p in field_dir.glob("*") if p.suffix.lower()
                    in (".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"))
    gt_path = field_dir / "ground_truth.json"
    existing = {}
    if gt_path.is_file():
        try:
            existing = json.loads(gt_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
    for p in photos:
        existing.setdefault(p.name, {
            "profile": "generic", "text": "", "fields": {},
            "_note": "complétez avec la valeur réelle vérifiée par vos soins",
        })
    gt_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2),
                       encoding="utf-8")
    return gt_path


def main() -> int:
    ap = argparse.ArgumentParser(description="Benchmark terrain (photos)")
    ap.add_argument("--suite", choices=["synth", "real", "both"], default="both")
    ap.add_argument("--init-template", action="store_true",
                    help="génère ground_truth.json à partir des photos de benchmarks/field/")
    args = ap.parse_args()
    root = Path(__file__).resolve().parent
    results = []

    if args.init_template:
        path = init_template(root / "field")
        print(f"gabarit écrit : {path} — complétez les valeurs réelles puis "
              "relancez avec --suite real")
        return 0

    if args.suite in ("synth", "both"):
        from make_field_samples import SAMPLES_DIR, make_field_samples
        if not (SAMPLES_DIR / "ground_truth.json").is_file():
            make_field_samples()
        res = evaluate(SAMPLES_DIR, SAMPLES_DIR / "ground_truth.json", "synth")
        results.append(res)
        print(f"[synth] {res['samples']} échantillons — CER moyen {res.get('mean_cer')} "
              f"— champs {res.get('field_accuracy')}")

    if args.suite in ("real", "both"):
        field_dir = root / "field"
        gt = field_dir / "ground_truth.json"
        photos = [p for p in field_dir.glob("*") if p.suffix.lower()
                  in (".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp")]
        if photos and gt.is_file():
            res = evaluate(field_dir, gt, "real")
            results.append(res)
            print(f"[real] {res['samples']} photos réelles — CER moyen {res.get('mean_cer')} "
                  f"— champs {res.get('field_accuracy')}")
        else:
            print("[real] AUCUNE photo réelle fournie dans benchmarks/field/ — "
                  "aucun chiffre terrain réel n'est produit.")
            results.append({"suite": "real", "samples": 0, "rows": [],
                            "note": "aucune photo réelle fournie — voir --help"})

    out_dir = root / "results"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "field_latest.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    md = "\n".join(to_markdown(r) for r in results)
    (out_dir / "field_latest.md").write_text(md, encoding="utf-8")
    print(f"rapport : {out_dir / 'field_latest.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
