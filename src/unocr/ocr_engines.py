"""Moteurs OCR : interface commune, Tesseract, texte natif PDF, registre, consensus.

Principe d'honnêteté : `is_available()` est TOUJOURS vérifié à l'exécution.
Aucun moteur n'est déclaré actif s'il n'est pas installé et fonctionnel.
"""
from __future__ import annotations

import hashlib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from PIL import Image

from .logging_setup import get_logger
from .models import BBox, Word
from .resources import engine_ram_requirement

log = get_logger("ocr")


@dataclass
class EngineOutput:
    engine: str
    text: str
    words: list[Word] = field(default_factory=list)
    mean_confidence: float = 0.0   # 0-1
    languages: list[str] = field(default_factory=list)
    duration_ms: float = 0.0
    raw: dict = field(default_factory=dict)
    ok: bool = True
    error: Optional[str] = None


class OCREngine(ABC):
    name: str = "base"
    kind: str = "raster"  # raster | native

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def supported_languages(self) -> list[str]: ...

    @abstractmethod
    def recognize(self, image: Image.Image, languages: list[str] | None = None,
                  page_num: int = 1) -> EngineOutput: ...


# ---------------------------------------------------------------- Tesseract
class TesseractEngine(OCREngine):
    name = "tesseract"
    kind = "raster"

    def __init__(self, psm: int = 3, min_confidence: float = 0.0):
        self.psm = psm
        self.min_confidence = min_confidence
        self._langs_cache: list[str] | None = None

    def is_available(self) -> bool:
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def supported_languages(self) -> list[str]:
        if self._langs_cache is None:
            try:
                import pytesseract
                langs = pytesseract.get_languages(config="")
                self._langs_cache = sorted(ln for ln in langs if ln != "osd")
            except Exception:
                self._langs_cache = []
        return list(self._langs_cache)

    def recognize(self, image: Image.Image, languages: list[str] | None = None,
                  page_num: int = 1) -> EngineOutput:
        import pytesseract
        from pytesseract import Output

        t0 = time.perf_counter()
        langs = [ln for ln in (languages or []) if ln in self.supported_languages()]
        if not langs:
            langs = ["fra", "eng"] if set(self.supported_languages()) >= {"fra", "eng"} \
                else (self.supported_languages()[:1] or ["eng"])
        lang_str = "+".join(langs)
        try:
            data = pytesseract.image_to_data(
                image, lang=lang_str, config=f"--psm {self.psm}",
                output_type=Output.DICT,
            )
        except Exception as exc:
            return EngineOutput(engine=self.name, text="", ok=False, error=str(exc))

        words: list[Word] = []
        confs: list[float] = []
        lines: dict[tuple, list[str]] = {}
        n = len(data["text"])
        for i in range(n):
            txt = (data["text"][i] or "").strip()
            try:
                conf = float(data["conf"][i])
            except (ValueError, TypeError):
                conf = -1.0
            if not txt or conf < 0:
                continue
            bbox = BBox(
                x0=float(data["left"][i]), y0=float(data["top"][i]),
                x1=float(data["left"][i] + data["width"][i]),
                y1=float(data["top"][i] + data["height"][i]),
            )
            words.append(Word(text=txt, bbox=bbox, confidence=max(0.0, min(1.0, conf / 100.0)),
                              engine=self.name, page_num=page_num))
            confs.append(conf / 100.0)
            key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            lines.setdefault(key, []).append(txt)

        text = "\n".join(" ".join(ws) for _, ws in sorted(lines.items()))
        mean = float(np.mean(confs)) if confs else 0.0
        return EngineOutput(
            engine=self.name, text=text, words=words,
            mean_confidence=mean, languages=langs,
            duration_ms=(time.perf_counter() - t0) * 1000,
        )


# ---------------------------------------------------------------- texte natif PDF
class NativeTextEngine(OCREngine):
    """Expose la couche texte native (mots déjà extraits à l'ingestion) comme moteur."""
    name = "native_pdf"
    kind = "native"

    def is_available(self) -> bool:
        return True

    def supported_languages(self) -> list[str]:
        return ["*"]  # le texte natif est multilingue par construction

    def recognize_from_words(self, words: list[Word], text: str,
                             page_num: int = 1) -> EngineOutput:
        confs = [w.confidence for w in words] or [0.95]
        return EngineOutput(
            engine=self.name, text=text, words=list(words),
            mean_confidence=float(np.mean(confs)), languages=["*"],
            duration_ms=0.0,
        )

    def recognize(self, image: Image.Image, languages: list[str] | None = None,
                  page_num: int = 1) -> EngineOutput:
        return EngineOutput(engine=self.name, text="",
                            ok=False, error="moteur natif : nécessite la couche texte du PDF")


# ---------------------------------------------------------------- moteurs optionnels
class EasyOCREngine(OCREngine):
    """Adaptateur EasyOCR (optionnel — nécessite easyocr + torch)."""
    name = "easyocr"
    unavailable_reason = ""
    kind = "raster"

    def is_available(self) -> bool:
        try:
            import easyocr  # noqa: F401
        except Exception:
            self.unavailable_reason = "easyocr non installé (pip install easyocr)"
            return False
        # garde-fou E1 : torch présent ne veut pas dire « la machine suivra »
        from .resources import can_load
        verdict = can_load(self.name)
        if not verdict.ok:
            log.warning("moteur %s désactivé : %s", self.name, verdict.reason)
            self.unavailable_reason = verdict.reason
            return False
        self.unavailable_reason = ""
        return True

    def supported_languages(self) -> list[str]:
        return []

    def recognize(self, image: Image.Image, languages: list[str] | None = None,
                  page_num: int = 1) -> EngineOutput:
        if not self.is_available():
            return EngineOutput(engine=self.name, text="", ok=False,
                                error="easyocr non installé (requis: pip install easyocr)")
        import easyocr
        # EasyOCR utilise des codes de langue ISO 639-1 (2 lettres)
        mapping = {"fra": "fr", "eng": "en", "ara": "ar", "spa": "es", "deu": "de",
                   "ita": "it", "por": "pt", "tur": "tr", "chi_sim": "ch_sim",
                   "rus": "ru"}
        easy_langs = [mapping[ln] for ln in (languages or []) if ln in mapping]
        if not easy_langs:
            easy_langs = ["fr", "en"]
        reader = easyocr.Reader(easy_langs, gpu=False, verbose=False)
        arr = np.array(image.convert("RGB"))[:, :, ::-1]  # RGB->BGR
        result = reader.readtext(arr)
        words: list[Word] = []
        for box, txt, conf in result:
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            words.append(Word(text=txt, bbox=BBox(x0=min(xs), y0=min(ys), x1=max(xs), y1=max(ys)),
                              confidence=float(conf), engine=self.name, page_num=page_num))
        text = " ".join(w.text for w in words)
        mean = float(np.mean([w.confidence for w in words])) if words else 0.0
        return EngineOutput(engine=self.name, text=text, words=words,
                            mean_confidence=mean, languages=languages or [])


class PaddleOCREngine(OCREngine):
    """Adaptateur PaddleOCR (optionnel — nécessite paddleocr + paddlepaddle)."""
    name = "paddleocr"
    unavailable_reason = ""
    kind = "raster"

    def is_available(self) -> bool:
        try:
            import paddleocr  # noqa: F401
        except Exception:
            self.unavailable_reason = ("paddleocr non installé "
                                       "(pip install paddleocr paddlepaddle)")
            return False
        from .resources import can_load
        verdict = can_load(self.name)
        if not verdict.ok:
            log.warning("moteur %s désactivé : %s", self.name, verdict.reason)
            self.unavailable_reason = verdict.reason
            return False
        self.unavailable_reason = ""
        return True

    def supported_languages(self) -> list[str]:
        return []

    def recognize(self, image: Image.Image, languages: list[str] | None = None,
                  page_num: int = 1) -> EngineOutput:
        if not self.is_available():
            return EngineOutput(engine=self.name, text="", ok=False,
                                error="paddleocr non installé (requis: pip install paddleocr paddlepaddle)")
        from paddleocr import PaddleOCR
        # Mise à jour des paramètres : suppression de cls
        ocr = PaddleOCR(use_textline_orientation=True, lang="fr")
        arr = np.array(image.convert("RGB"))[:, :, ::-1]
        result = ocr.ocr(arr)
        words: list[Word] = []
        for page in result or []:
            for box, (txt, conf) in (page or []):
                xs = [p[0] for p in box]
                ys = [p[1] for p in box]
                words.append(Word(text=txt,
                                  bbox=BBox(x0=min(xs), y0=min(ys), x1=max(xs), y1=max(ys)),
                                  confidence=float(conf), engine=self.name, page_num=page_num))
        text = " ".join(w.text for w in words)
        mean = float(np.mean([w.confidence for w in words])) if words else 0.0
        return EngineOutput(engine=self.name, text=text, words=words,
                            mean_confidence=mean, languages=languages or [])


class IndraEngine(OCREngine):
    """Adaptateur Indra OCR."""
    name = "indra"
    unavailable_reason = ""
    kind = "raster"

    def is_available(self) -> bool:
        try:
            import indra_ocr  # noqa: F401
        except Exception:
            self.unavailable_reason = "indra-ocr non installé"
            return False
        from .resources import can_load
        verdict = can_load(self.name)
        if not verdict.ok:
            log.warning("moteur %s désactivé : %s", self.name, verdict.reason)
            self.unavailable_reason = verdict.reason
            return False
        self.unavailable_reason = ""
        return True

    def supported_languages(self) -> list[str]:
        return ["fra", "eng", "ara"]

    def recognize(self, image: Image.Image, languages: list[str] | None = None,
                  page_num: int = 1) -> EngineOutput:
        if not self.is_available():
            return EngineOutput(engine=self.name, text="", ok=False,
                                error="indra-ocr non installé")
        import indra_ocr
        import numpy as np

        t0 = time.perf_counter()
        gray = np.array(image.convert("L"))

        conv = indra_ocr.load()
        page = conv.ocr(gray)

        words: list[Word] = []
        for line in page.lines:
            box = line.box
            words.append(Word(
                text=line.text,
                bbox=BBox(x0=float(box[0]), y0=float(box[1]), x1=float(box[2]), y1=float(box[3])),
                confidence=float(line.conf),
                engine=self.name,
                page_num=page_num
            ))

        text = page.text
        mean = float(np.mean([w.confidence for w in words])) if words else 0.0

        return EngineOutput(
            engine=self.name, text=text, words=words,
            mean_confidence=mean, languages=languages or [],
            duration_ms=(time.perf_counter() - t0) * 1000
        )


class BaiduOCREngine(OCREngine):
    """Adaptateur Baidu OCR (API Cloud)."""
    name = "baidu"
    unavailable_reason = ""
    kind = "raster"

    def is_available(self) -> bool:
        import os
        api_key = os.environ.get("BAIDU_OCR_API_KEY") or os.environ.get("BAIDU_API_KEY")
        secret_key = os.environ.get("BAIDU_OCR_SECRET_KEY") or os.environ.get("BAIDU_SECRET_KEY")
        if not api_key or not secret_key:
            self.unavailable_reason = "Clés API Baidu manquantes (BAIDU_API_KEY / BAIDU_SECRET_KEY)"
            return False
        try:
            import requests  # noqa: F401
        except ImportError:
            self.unavailable_reason = "Transport Baidu absent (installer unocr[baidu])"
            return False
        self.unavailable_reason = ""
        return True

    def supported_languages(self) -> list[str]:
        return ["chn_eng", "eng", "fra", "spa", "por", "deu", "ita"]

    def recognize(self, image: Image.Image, languages: list[str] | None = None,
                  page_num: int = 1) -> EngineOutput:
        if not self.is_available():
            return EngineOutput(engine=self.name, text="", ok=False, error=self.unavailable_reason)

        import base64
        import io
        import os

        from .baidu_http import MAX_TOKEN_CHARS, MAX_WORDS, OCR_URL, TOKEN_URL, post_json
        from .baidu_response import confidence_from_item

        api_key = os.environ.get("BAIDU_OCR_API_KEY") or os.environ.get("BAIDU_API_KEY")
        secret_key = os.environ.get("BAIDU_OCR_SECRET_KEY") or os.environ.get("BAIDU_SECRET_KEY")

        t0 = time.perf_counter()
        stage = "authentification"
        try:
            # Le fournisseur utilise des paramètres query : encodage structuré,
            # pas interpolation. Ces URL ne doivent jamais devenir un diagnostic.
            token_data = post_json(TOKEN_URL, params={
                "grant_type": "client_credentials", "client_id": api_key,
                "client_secret": secret_key,
            }, read_timeout=10)
            access_token = token_data.get("access_token")
            if ("error" in token_data or "error_code" in token_data
                    or not isinstance(access_token, str) or not access_token
                    or len(access_token) > MAX_TOKEN_CHARS
                    or any(ord(ch) < 33 or ord(ch) > 126 for ch in access_token)):
                return EngineOutput(engine=self.name, text="", ok=False,
                                    error="Baidu : authentification refusée ou réponse invalide")

            stage = "préparation image"
            buffered = io.BytesIO()
            image.convert("RGB").save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode("ascii")

            stage = "reconnaissance"
            result = post_json(OCR_URL, params={"access_token": access_token},
                               data={"image": img_str}, read_timeout=15)
            if "error_code" in result or "error" in result:
                return EngineOutput(engine=self.name, text="", ok=False,
                                    error="Baidu : reconnaissance refusée")
            words_result = result.get("words_result")
            if not isinstance(words_result, list) or len(words_result) > MAX_WORDS:
                return EngineOutput(engine=self.name, text="", ok=False,
                                    error="Baidu : réponse de reconnaissance invalide")

            words: list[Word] = []
            score_counts = {"reported": 0, "missing": 0, "invalid": 0}
            for item in words_result:
                if not isinstance(item, dict) or not isinstance(item.get("words"), str):
                    return EngineOutput(engine=self.name, text="", ok=False,
                                        error="Baidu : réponse de reconnaissance invalide")
                txt = item["words"]
                loc = item.get("location")
                if loc:
                    x0 = float(loc.get("left", 0))
                    y0 = float(loc.get("top", 0))
                    w = float(loc.get("width", 0))
                    h = float(loc.get("height", 0))
                    bbox = BBox(x0=x0, y0=y0, x1=x0+w, y1=y0+h)
                else:
                    bbox = BBox(x0=0, y0=0, x1=float(image.width), y1=float(image.height))

                confidence, score_source = confidence_from_item(item)
                score_counts[score_source] += 1
                words.append(Word(
                    text=txt,
                    bbox=bbox,
                    confidence=confidence,
                    engine=self.name,
                    page_num=page_num
                ))

            text = "\n".join(w.text for w in words)
            mean = sum(w.confidence for w in words) / len(words) if words else 0.0

            return EngineOutput(
                engine=self.name, text=text, words=words,
                mean_confidence=mean, languages=languages or [],
                duration_ms=(time.perf_counter() - t0) * 1000,
                raw={"confidence": {"policy": "provider_average_else_zero",
                                    "calibrated": False, **score_counts}},
            )
        except Exception:
            # URL, identifiants, jeton, corps distant et exception ne sortent pas.
            return EngineOutput(engine=self.name, text="", ok=False,
                                error=f"Baidu : échec {stage}")


# ---------------------------------------------------------------- registre
class EngineRegistry:
    def __init__(self):
        self._engines: dict[str, OCREngine] = {}
        for eng in (TesseractEngine(), NativeTextEngine(), EasyOCREngine(), PaddleOCREngine(), IndraEngine(), BaiduOCREngine()):
            self.register(eng)

    def register(self, engine: OCREngine) -> None:
        self._engines[engine.name] = engine

    def get(self, name: str) -> OCREngine | None:
        return self._engines.get(name)

    def list_engines(self) -> list[dict]:
        out = []
        for name, eng in self._engines.items():
            avail = eng.is_available()
            row = {
                "name": name,
                "kind": eng.kind,
                "available": avail,
                "languages": eng.supported_languages() if avail else [],
                "active": avail,
                "ram_required_mb": engine_ram_requirement(name),
            }
            reason = getattr(eng, "unavailable_reason", "")
            if reason:
                row["unavailable_reason"] = reason
            out.append(row)
        return out

    def available_raster_engines(self) -> list[OCREngine]:
        return [e for e in self._engines.values()
                if e.kind == "raster" and e.is_available()]

    def select(self, has_native_text: bool = False,
               quality_issues: list[str] | None = None,
               want_all: bool = False) -> list[OCREngine]:
        """Sélection automatique des moteurs selon le type de page et la qualité."""
        selected: list[OCREngine] = []
        native = self.get("native_pdf")
        if has_native_text and native:
            selected.append(native)
        raster = self.available_raster_engines()

        def engine_priority(e):
            # Priorité haute : Indra, sauf si des problèmes de qualité détectés
            if e.name == "indra":
                if quality_issues and "blurry" in quality_issues:
                    return 2
                return 0
            if e.name == "tesseract":
                return 1
            return 2

        raster.sort(key=lambda e: (engine_priority(e), e.name))
        if want_all:
            selected.extend(raster)
        elif raster:
            selected.append(raster[0])
        return selected


# ---------------------------------------------------------------- consensus
@dataclass
class ConsensusResult:
    text: str
    words: list[Word]
    mean_confidence: float
    disagreements: list[dict] = field(default_factory=list)
    chosen_engine: str = ""


def _words_fingerprint(words: list[Word]) -> str:
    return hashlib.sha1(" ".join(w.text for w in words).encode("utf-8", "replace")).hexdigest()


def consensus_merge(outputs: list[EngineOutput], page_num: int = 1) -> ConsensusResult:
    """Combine plusieurs sorties moteurs.

    Le vote majoritaire n'est PAS la vérité : on retient la sortie du moteur avec
    la meilleure confiance, et tout écart de texte significatif est signalé pour
    vérification (score de confiance global réduit en aval).
    """
    valid = [o for o in outputs if o.ok and o.words]
    if not valid:
        best = next((o for o in outputs if o.ok), None)
        return ConsensusResult(text=best.text if best else "", words=[],
                               mean_confidence=best.mean_confidence if best else 0.0,
                               chosen_engine=best.engine if best else "")

    valid.sort(key=lambda o: o.mean_confidence, reverse=True)
    best = valid[0]
    disagreements: list[dict] = []
    if len(valid) > 1:
        for other in valid[1:]:
            if _words_fingerprint(best.words) != _words_fingerprint(other.words):
                # localise la première divergence pour signaler la zone
                zone = None
                for wa, wb in zip(best.words, other.words):
                    if wa.text != wb.text:
                        zone = wa.bbox
                        disagreements.append({
                            "page_num": page_num,
                            "bbox": zone.model_dump() if zone else None,
                            "text_by_engine": {best.engine: wa.text, other.engine: wb.text},
                            "resolution": "best_confidence",
                        })
                        break
                if zone is None:
                    disagreements.append({
                        "page_num": page_num, "bbox": None,
                        "text_by_engine": {best.engine: best.text[:120], other.engine: other.text[:120]},
                        "resolution": "best_confidence",
                    })
    return ConsensusResult(
        text=best.text, words=best.words,
        mean_confidence=best.mean_confidence, disagreements=disagreements,
        chosen_engine=best.engine,
    )
