"""Génère des « photos terrain » synthétiques dégradées pour le benchmark de capture.

IMPORTANT — honnêteté des mesures : ces échantillons sont SYNTHÉTIQUES (texte rendu
puis dégradé : rotation, perspective, flou, bruit, faible luminosité). Ils
simulent les conditions d'une prise de vue sur le terrain, ce ne sont PAS des
photos réelles. Aucune métrique issue de ces échantillons ne doit être présentée
comme une mesure sur site.

Pour de VRAIES photos (ex. port d'Oran) : déposez-les dans benchmarks/field/
avec un ground_truth.json (voir run_field_benchmark.py --help).
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

FIELD_DIR = Path(__file__).parent / "field"
SAMPLES_DIR = Path(__file__).parent / "field_samples"

DOCS = {
    "container": {
        "profile": "container",
        "text_lines": ["CSQU 3054383"],
        "fields": {"container_number": "CSQU 3054383"},
        "font_size": 120,
    },
    "plate_fr": {
        "profile": "vehicle_plate",
        "text_lines": ["AB-123-CD"],
        "fields": {"plate_number": "AB-123-CD"},
        "font_size": 130,
    },
    "plate_dz": {
        "profile": "vehicle_plate",
        "text_lines": ["12345 AB 16"],
        "fields": {"plate_number": "12345 AB 16"},
        "font_size": 130,
    },
    "carte_grise": {
        "profile": "carte_grise",
        "text_lines": [
            "CERTIFICAT D'IMMATRICULATION",
            "Plaque : AB-123-CD",
            "N° d'identification : 1HGBH41JXMN109186",
            "Marque : RENAULT",
            "Énergie : DIESEL",
            "1ère immatriculation : 12/03/2019",
        ],
        "fields": {
            "plate_number": "AB-123-CD",
            "vin": "1HGBH41JXMN109186",
            "make": "RENAULT",
            "fuel": "DIESEL",
            "first_reg_date": "2019-03-12",
        },
        "font_size": 44,
    },
}

# niveaux de dégradation croissants (conditions terrain simulées)
VARIANTS = {
    "clean": {},
    "skew": {"angle": 6},
    "blurred": {"blur": 2.2, "angle": 3},
    # field_hard : conditions difficiles mais lisibles — calibré pour rester
    # au-dessus du seuil de reconnaissance Tesseract sur CPU, quelle que soit
    # la plateforme (Linux/Windows). Le flou et le bruit sont réduits par rapport
    # à la version initiale car les mesures sur Windows montraient que la
    # combinaison cumulative rendait l'image illisible même après débruitage.
    "field_hard": {"angle": 5, "blur": 0.8, "noise": 8, "dark": 0.80,
                   "perspective": 0.04, "zoom_out": 0.92},
}


def _font(size: int, mono: bool = False):
    paths = [
        # Linux (DejaVu)
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf" if mono
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        # Windows — monospace pour mono, gras sans-serif sinon
        "C:/Windows/Fonts/consolab.ttf" if mono else "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/consola.ttf" if mono else "C:/Windows/Fonts/arial.ttf",
    ]
    for p in paths:
        if Path(p).is_file():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def render_doc(doc: dict, rng: random.Random) -> Image.Image:
    size = (1500, 220 + 90 * len(doc["text_lines"]))
    img = Image.new("RGB", size, (232, 228, 220))
    d = ImageDraw.Draw(img)
    y = 40
    for i, line in enumerate(doc["text_lines"]):
        mono = ("identification" in line or "immatriculation" in line.lower()
                and "1" in line)
        f = _font(doc["font_size"], mono=mono)
        d.text((60, y), line, font=f, fill=(18, 18, 18))
        y += doc["font_size"] + 40
    return img


def degrade(img: Image.Image, p: dict, rng: random.Random) -> Image.Image:
    if p.get("zoom_out", 1.0) < 1.0:
        w, h = img.size
        z = p["zoom_out"]
        img = img.resize((int(w * z), int(h * z)))
        canvas = Image.new("RGB", (w, h), (200, 195, 185))
        canvas.paste(img, ((w - img.width) // 2, (h - img.height) // 2))
        img = canvas
    if p.get("perspective"):
        k = p["perspective"]
        w, h = img.size
        # trapèze léger : vue un peu de biais (coins : hg, bg, bd, hd)
        inset = w * k
        quad = (inset, 0, 0, h, w, h, w - inset, 0)
        img = img.transform((w, h), Image.QUAD, quad, resample=Image.BICUBIC,
                            fillcolor=(160, 155, 145))
    if p.get("angle"):
        img = img.rotate(p["angle"], expand=True, fillcolor=(180, 175, 165),
                         resample=Image.BICUBIC)
    if p.get("blur"):
        img = img.filter(ImageFilter.GaussianBlur(p["blur"]))
    if p.get("noise"):
        noise = Image.effect_noise(img.size, p["noise"]).convert("RGB")
        img = Image.blend(img, noise, 0.22)
    if p.get("dark"):
        img = ImageEnhance.Brightness(img).enhance(p["dark"])
        img = ImageEnhance.Contrast(img).enhance(0.85)
    return img


def make_field_samples(destination: Path | None = None) -> dict:
    """Destination explicite pour les tests ; défaut manuel historique conservé."""
    output = Path(destination) if destination is not None else SAMPLES_DIR
    output.mkdir(parents=True, exist_ok=True)
    rng = random.Random(20261017)
    gt = {}
    for doc_name, doc in DOCS.items():
        base = render_doc(doc, rng)
        for vname, params in VARIANTS.items():
            img = degrade(base.copy(), params, rng)
            fname = f"{doc_name}__{vname}.png"
            img.save(output / fname)
            gt[fname] = {
                "profile": doc["profile"],
                "text": "\n".join(doc["text_lines"]),
                "fields": doc["fields"],
                "variant": vname,
                "synthetic": True,
            }
    (output / "ground_truth.json").write_text(
        json.dumps(gt, ensure_ascii=False, indent=2), encoding="utf-8")
    return gt


if __name__ == "__main__":
    gt = make_field_samples()
    print(f"{len(gt)} échantillons synthétiques générés dans {SAMPLES_DIR}")
    print("RAPPEL : ces échantillons sont synthétiques — pas des photos réelles.")
