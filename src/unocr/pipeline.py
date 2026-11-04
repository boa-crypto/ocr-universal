"""Orchestrateur du pipeline OCR.

Flux : sécurité/ingestion → prétraitement → OCR (sélection + consensus) →
mise en page → tableaux → champs/profil → qualité → export.
Le fichier source n'est jamais modifié ; toutes les étapes sont chronométrées.
"""
from __future__ import annotations

import hashlib
import os
import time
from concurrent.futures import as_completed
from pathlib import Path

from PIL import Image

from .calibration import Calibration
from .classification import DocumentClassifier, consigne_classification
from .config import Config, get_config
from .direction import detect_direction, dominant_direction
from .extract_fields import extract_generic_fields, locate_value
from .extract_tables import (
    extract_borderless_table,
    extract_ruled_table,
    merge_multipage_tables,
    ocr_cell_factory,
)
from .ingest import LoadedDocument, load_document
from .layout import build_blocks, group_words_into_lines
from .logging_setup import get_logger
from .models import (
    DocumentResult,
    EngineRun,
    JobOptions,
    PageResult,
    PreprocessOp,
)
from .ocr_engines import EngineRegistry, consensus_merge
from .preprocess import analyze_quality, preprocess_page
from .profiles import apply_profile, check_required, load_all_profiles
from .quality import build_quality_report, global_confidence
from .security import SecurityError

log = get_logger("pipeline")


def _available_ram_mb() -> int:
    """RAM réellement disponible, en Mo. 0 si indisponible (on ignore alors
    cette contrainte plutôt que de bloquer le traitement)."""
    try:
        with open("/proc/meminfo", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) // 1024
    except (OSError, ValueError, IndexError):
        pass
    try:  # repli multi-plateforme
        import psutil
        return int(psutil.virtual_memory().available // (1024 * 1024))
    except Exception:
        return 0





class Pipeline:
    def __init__(self, cfg: Config | None = None, registry: EngineRegistry | None = None):
        self.cfg = cfg or get_config()
        self.registry = registry or EngineRegistry()
        # A2 : courbe de calibration (identité par défaut — sans effet)
        self._calibration = Calibration.load(
            self.cfg.data_dir / "calibration.json")

    # ------------------------------------------------------------------
    def process_file(self, path: Path | str, options: JobOptions | None = None,
                     progress=None, job_id: str | None = None) -> DocumentResult:
        t_start = time.perf_counter()
        options = options or JobOptions()
        path = Path(path)

        def report(stage: str, frac: float) -> None:
            if progress:
                progress(stage, frac)

        raw_bytes = path.read_bytes()
        source_hash = hashlib.sha256(raw_bytes).hexdigest()

        # 1. ingestion (inclut la validation de sécurité)
        report("ingest", 0.05)
        t0 = time.perf_counter()
        render_dpi = options.render_dpi or self.cfg.get("render_dpi", 200)
        render_dpi = max(72, min(400, int(render_dpi)))
        loaded = load_document(
            path, dpi=render_dpi,
            max_pages=self.cfg.get("max_pages", 500),
            max_size_mb=self.cfg.get("max_file_size_mb", 50),
            max_zip_uncompressed_mb=self.cfg.get("security.max_zip_uncompressed_mb", 200),
            max_zip_ratio=self.cfg.get("security.max_zip_ratio", 100),
        )
        timings = {"ingest_ms": (time.perf_counter() - t0) * 1000}

        # plage de pages demandée (option)
        selected = set(parse_page_range(options.page_range, len(loaded.pages)))
        if selected != set(range(1, len(loaded.pages) + 1)):
            loaded.pages = [p for p in loaded.pages if p.page_num in selected]
            if not loaded.pages:
                loaded.pages = []
                raise SecurityError(f"plage de pages hors document : {options.page_range!r}")

        result = DocumentResult(source_file=path.name, source_hash=source_hash)
        # l'identifiant du résultat doit être celui du document réel : sans ce
        # réalignement, le journal d'audit tracerait la classification sous un
        # « doc_… » que ni le magasin ni l'API ne savent retrouver
        if job_id:
            result.id = job_id
        result.warnings.extend(loaded.warnings)
        if options.page_range.strip():
            result.warnings.append(f"plage de pages appliquée : {options.page_range}")

        # 2. pages : prétraitement + OCR (parallélisable — voir E4)
        t0 = time.perf_counter()
        page_images: dict[int, Image.Image] = {}
        n = len(loaded.pages)
        workers = self._page_workers(n)
        results_by_idx: dict[int, PageResult] = {}

        if workers > 1:
            # Tesseract est appelé en sous-processus : le GIL est libéré,
            # les threads donnent donc un parallélisme réel.
            from concurrent.futures import ThreadPoolExecutor

            done = 0
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {
                    pool.submit(self._process_page, lp, options, i, n): i
                    for i, lp in enumerate(loaded.pages)}
                for fut in as_completed(futures):
                    idx = futures[fut]
                    results_by_idx[idx] = fut.result()
                    done += 1
                    report("ocr", 0.1 + 0.55 * (done / max(1, n)))
        else:
            for i, lpage in enumerate(loaded.pages):
                report("ocr", 0.1 + 0.55 * (i / max(1, n)))
                results_by_idx[i] = self._process_page(lpage, options,
                                                       page_index=i, page_count=n)

        # ordre des pages préservé quoi qu'il arrive
        result.pages = [results_by_idx[i] for i in range(n)]
        for lpage in loaded.pages:
            if lpage.image is not None:
                page_images[lpage.page_num] = lpage.image
        timings["ocr_ms"] = (time.perf_counter() - t0) * 1000
        timings["ocr_workers"] = float(workers)

        # 3. tableaux numériques (CSV/Excel/DOCX/ODT) + tableaux image
        if options.extract_tables:
            result.tables.extend(loaded.digital_tables)
            report("tables", 0.7)
            t0 = time.perf_counter()
            result.tables = self._extract_tables(loaded, result, options) + result.tables
            timings["tables_ms"] = (time.perf_counter() - t0) * 1000
        else:
            result.warnings.append("extraction des tableaux désactivée (option)")

        # 4. champs + profil métier
        if options.extract_fields:
            report("fields", 0.8)
            t0 = time.perf_counter()
            fields, categories = extract_generic_fields(result.pages)
            result.fields.update(fields)
            result.categories.update(categories)

            profiles = load_all_profiles(self.cfg.profiles_dir,
                                        self.cfg.user_profiles_dir)

            # 3bis. classification (étape 4) — AVANT l'extraction, pour choisir
            # le bon profil. Le profil explicite de l'utilisateur reste
            # prioritaire : la classification ne le contourne jamais.
            # « generic » est la valeur par défaut : elle ne compte pas comme un
            # choix explicite. Un profil nommé autrement est respecté tel quel.
            profil_force = bool(options.profile) and options.profile != "generic"
            classification = None
            if options.auto_classify and not profil_force:
                classifieur = DocumentClassifier(
                    self.cfg.profiles_dir, self.cfg.data_dir / "document_types")
                classification = classifieur.classify(
                    "\n\n".join(p.text for p in result.pages))
                result.classification = classification.as_dict()
                if classification.category != "unknown":
                    suggere = classifieur.profil_pour(classification.category)
                    if suggere and suggere in profiles:
                        options = options.model_copy(
                            update={"profile": suggere})
                    else:
                        result.warnings.append(
                            f"document classé « {classification.label} » mais "
                            f"aucun profil d'extraction ne lui correspond : "
                            "champs génériques utilisés.")
                if classification.needs_review:
                    result.warnings.append(
                        f"classification incertaine ({classification.reason}) : "
                        "à confirmer avant de transmettre.")

            profile_name = options.profile or self.cfg.get("extraction.default_profile", "generic")
            profile = profiles.get(profile_name) or profiles.get("generic")
            if profile:
                def loc(v):
                    return locate_value(result.pages, v)

                profile_fields = apply_profile(
                    "\n\n".join(p.text for p in result.pages), profile, locate=loc)
                # les champs de profil ont priorité sur les génériques homonymes
                for k, fv in profile_fields.items():
                    fv.profile = profile.name
                    result.fields[k] = fv
                issues = check_required(profile, result.fields)
                result.quality.checks.extend(issues)
                result.categories["_required"] = [f.key for f in profile.fields if f.required]
                result.profile_used = profile.name
                if classification is not None:
                    consigne_classification(self.cfg.log_dir, result.id,
                                            classification)
                # infos document
                result.info.doc_type = profile.name
                for key, attr in (("document_number", "doc_number"), ("invoice_number", "doc_number"),
                                  ("bl_number", "doc_number"), ("issue_date", "issue_date"),
                                  ("due_date", "due_date"), ("date", "issue_date"),
                                  ("shipper", "sender"), ("consignee", "recipient")):
                    fv = result.fields.get(key)
                    if fv and fv.value:
                        setattr(result.info, attr, fv.value.split(" | ")[0])
            timings["fields_ms"] = (time.perf_counter() - t0) * 1000
        else:
            result.warnings.append("extraction des champs désactivée (option)")

        # 5. codes-barres (pages image uniquement)
        if options.extract_barcodes:
            t0 = time.perf_counter()
            result.barcodes = self._decode_barcodes(loaded)
            timings["barcodes_ms"] = (time.perf_counter() - t0) * 1000

        # 6. qualité (seuil de revue humaine configurable)
        report("quality", 0.9)
        result.quality = build_quality_report(
            result, review_threshold=options.min_confidence_review)
        # recalcule les confiances globales des champs avec le facteur qualité
        for fv in result.fields.values():
            if fv.page_num:
                page = next((p for p in result.pages if p.page_num == fv.page_num), None)
                if page and fv.engine_confidence:
                    g = global_confidence(fv.engine_confidence, page,
                                          disagreement=bool(result.quality.disagreements))
                    fv.confidence = round(g, 3)
                    # A2 : probabilité calibrée (égale à la confiance si inactive)
                    fv.calibrated_confidence = self._calibration.apply(fv.confidence)

        # 8. métadonnées
        result.engines_used = sorted({r.engine for p in result.pages for r in p.engine_runs})
        # C3 : direction d'écriture par page et pour le document
        for p in result.pages:
            p.direction = detect_direction(p.text)
        result.direction = dominant_direction([p.direction for p in result.pages])
        result.info.page_count = len(result.pages)
        result.info.source_format = loaded.format
        langs: list[str] = []
        for p in result.pages:
            for ln in p.detected_languages:
                if ln not in langs:
                    langs.append(ln)
        result.info.languages = langs
        result.info.title = result.info.title or result.fields.get("title", None) and \
            result.fields["title"].value

        timings["total_ms"] = (time.perf_counter() - t_start) * 1000
        result.timings_ms = {k: round(v, 1) for k, v in timings.items()}
        report("done", 1.0)
        return result

    # ------------------------------------------------------------------
    def _page_workers(self, n_pages: int) -> int:
        """Nombre de pages traitées en parallèle (E4).

        Borné par le nombre de cœurs, par la RAM disponible (chaque page
        consomme de la mémoire) et par le réglage `jobs.workers`. Une seule
        page ne se parallélise pas.
        """
        if n_pages <= 1:
            return 1
        cfg_workers = 0
        try:
            cfg_workers = int(self.cfg.get("jobs.workers", 0) or 0)
        except Exception:
            cfg_workers = 0
        cpus = os.cpu_count() or 1
        avail = _available_ram_mb()
        # ~350 Mo par page en mode accurate ; on garde une marge
        by_ram = max(1, int(avail // 450)) if avail else cpus
        limit = cfg_workers if cfg_workers > 0 else cpus
        return max(1, min(n_pages, cpus, by_ram, limit))

    def _process_page(self, lpage, options: JobOptions, page_index: int,
                      page_count: int) -> PageResult:
        native_words = list(lpage.native_words)
        native_text = lpage.native_text
        page_res = PageResult(
            page_num=lpage.page_num, width=lpage.width, height=lpage.height,
            has_native_text=bool(native_text.strip()),
            native_text_ratio=min(1.0, len(native_text.strip()) / 200.0),
        )

        # pas d'image (texte numérique) : pas d'OCR raster
        if lpage.image is None:
            page_res.text = native_text
            page_res.words = native_words
            page_res.lines = group_words_into_lines(native_words)
            page_res.blocks = build_blocks(page_res.lines, lpage.width, lpage.height)
            page_res.detected_languages = _detect_languages(native_text)
            page_res.engine_runs.append(EngineRun(
                engine="native_text", page_num=lpage.page_num,
                mean_confidence=0.95, word_count=len(native_words), ok=True))
            return page_res

        # Vérification du cache SQLite
        import io

        from .cache import PageCache
        cache = PageCache()
        buffered = io.BytesIO()
        lpage.image.save(buffered, format="PNG")
        img_bytes = buffered.getvalue()
        cached_res = cache.get(img_bytes)
        if cached_res is not None:
            cached_res.page_num = lpage.page_num
            return cached_res

        quality = analyze_quality(lpage.image, lpage.estimated_dpi)
        page_res.quality = quality
        page_res.blank = quality.is_blank
        if quality.is_blank:
            page_res.text = ""
            return page_res

        # prétraitement (mode : off | standard | aggressive)
        variants = []
        pre_mode = options.preprocess_mode or "standard"
        if options.preprocess and pre_mode != "off" and self.cfg.get("preprocess.enabled", True):
            pre = preprocess_page(lpage.image, quality, lpage.estimated_dpi,
                                  aggressive=(pre_mode == "aggressive"))
            page_res.preprocess_ops = pre.ops
            variants.append((pre.variant_name, pre.image))
        else:
            page_res.preprocess_ops = []
            if pre_mode == "off" or not options.preprocess:
                page_res.preprocess_ops.append(PreprocessOp(
                    name="preprocess", applied=False,
                    reason="prétraitement désactivé par option"))
        variants.append(("original", lpage.image))

        # langue : auto depuis le texte natif, sinon défaut config
        languages = list(options.languages or [])
        if not languages:
            detected = _detect_languages(native_text) if native_text else []
            # Support both Tesseract and Indra language codes
            supported = set()
            tesseract = self.registry.get("tesseract")
            indra = self.registry.get("indra")
            if tesseract:
                supported.update(tesseract.supported_languages())
            if indra:
                supported.update(indra.supported_languages())
            mapping = {"fr": "fra", "en": "eng", "ar": "ara", "es": "spa", "de": "deu",
                       "it": "ita", "pt": "por", "tr": "tur", "zh-cn": "chi_sim",
                       "ru": "rus"}
            languages = [mapping[d] for d in detected if mapping.get(d) in supported]
            if not languages:
                languages = [ln for ln in self.cfg.get("default_languages", ["fra", "eng"])
                             if not supported or ln in supported]

        best = None
        best_score = -1.0
        engine_runs = []

        quality_mode = options.quality_mode or self.cfg.get("quality_mode", "accurate")
        compare = (quality_mode == "accurate" and options.variant_comparison
                   and self.cfg.get("preprocess.variant_comparison", True)
                   and len(variants) > 1)

        for name, img in variants:
            # en mode non-comparatif : une seule variante SAUF si elle ne donne
            # rien — on tente alors les suivantes (l'original sauve souvent la
            # mise quand le prétraitement dégrade la page)
            if (not compare and name != variants[0][0]
                    and best is not None and best[1].words):
                continue
            outputs = []
            engines = self.registry.select(
                has_native_text=bool(native_text.strip()),
                quality_issues=quality.issues,
                want_all=(quality_mode == "accurate"),
            )
            # choix forcé du moteur (option)
            if options.engine == "tesseract":
                engines = [e for e in engines if e.name == "tesseract"]
            elif options.engine == "indra":
                engines = [e for e in engines if e.name == "indra"]
            elif options.engine == "native":
                if native_text.strip():
                    engines = []  # texte natif uniquement
                else:
                    # pas de couche texte sur cette page : repli sur Indra puis Tesseract
                    engines = [e for e in engines if e.name in ("indra", "tesseract")]
            # moteur natif : reconstruit depuis les mots déjà extraits
            native_eng = self.registry.get("native_pdf")
            if (native_text.strip() and native_eng and name == variants[0][0]
                    and options.engine != "tesseract"):
                native_out = native_eng.recognize_from_words(native_words, native_text,
                                                             lpage.page_num)
                outputs.append(native_out)
                engine_runs.append(EngineRun(
                    engine=native_eng.name, page_num=lpage.page_num,
                    languages=["*"], mean_confidence=native_out.mean_confidence,
                    word_count=len(native_out.words), duration_ms=0.0, ok=True))
            for eng in engines:
                if eng.kind == "native":
                    continue
                try:
                    out = eng.recognize(img, languages, lpage.page_num)
                except Exception as exc:
                    # Un moteur optionnel qui plante ne doit pas faire échouer
                    # tout le document : on consigne l'échec et on continue.
                    log.warning("moteur %s en échec page %s : %s",
                                eng.name, lpage.page_num, exc)
                    engine_runs.append(EngineRun(
                        engine=eng.name, page_num=lpage.page_num,
                        languages=languages, mean_confidence=0.0,
                        word_count=0, duration_ms=0.0, ok=False, error=str(exc)))
                    continue
                # Calibration de la confiance moteur (A2) — pour Indra notamment
                if hasattr(self, '_calibration') and self._calibration.active:
                    calibrated = self._calibration.apply(out.mean_confidence)
                else:
                    calibrated = out.mean_confidence
                engine_runs.append(EngineRun(
                    engine=eng.name, page_num=lpage.page_num,
                    languages=languages, mean_confidence=out.mean_confidence,
                    word_count=len(out.words),
                    duration_ms=out.duration_ms, ok=out.ok, error=out.error))
                if out.ok:
                    outputs.append(out)
                # Fallback intelligent : si Indra échoue ou confiance trop faible, tenter Tesseract
                if eng.name == "indra" and (not out.ok or calibrated < 0.6):
                    tesseract_eng = self.registry.get("tesseract")
                    if tesseract_eng and tesseract_eng.is_available():
                        log.info("Fallback Indra → Tesseract (page %s): indra.ok=%s, conf=%.2f",
                                 lpage.page_num, out.ok, calibrated)
                        try:
                            out2 = tesseract_eng.recognize(img, languages, lpage.page_num)
                            if out2.ok:
                                engine_runs.append(EngineRun(
                                    engine="tesseract", page_num=lpage.page_num,
                                    languages=languages, mean_confidence=out2.mean_confidence,
                                    word_count=len(out2.words), duration_ms=out2.duration_ms,
                                    ok=True, error=None))
                                outputs.append(out2)
                        except Exception as exc2:
                            log.warning("Fallback Tesseract aussi en échec: %s", exc2)
            if not outputs:
                continue
            merged = consensus_merge(outputs, lpage.page_num)
            score = merged.mean_confidence + (0.05 if merged.words else 0)
            # bonus au texte natif (exact) s'il existe
            if any(o.engine == "native_pdf" for o in outputs) and merged.words:
                score += 0.25
            if score > best_score:
                best_score = score
                best = (name, merged)

        if best is None:
            # aucun OCR : on garde le texte natif s'il existe
            if native_text.strip():
                page_res.text = native_text
                page_res.words = native_words
            page_res.engine_runs = engine_runs
            return page_res

        name, merged = best
        page_res.variant_selected = name
        page_res.text = merged.text or native_text
        page_res.words = merged.words or native_words
        page_res.engine_runs = engine_runs
        for w in page_res.words:
            w.page_num = lpage.page_num
        page_res.lines = group_words_into_lines(page_res.words)
        page_res.blocks = build_blocks(page_res.lines, lpage.width, lpage.height)
        # reconstruit le texte dans l'ordre de lecture (colonnes, RTL) quand des
        # blocs ont pu être formés — corrige l'ordre brut des couches texte PDF
        if page_res.blocks:
            page_res.text = "\n".join(b.text for b in page_res.blocks)
        page_res.detected_languages = _detect_languages(page_res.text)

        # Stockage dans le cache pour les traitements futurs
        try:
            cache.set(img_bytes, page_res)
        except Exception:
            pass  # le cache est un optimiseur, jamais un point de défaillance

        return page_res

    # ------------------------------------------------------------------
    def _extract_tables(self, loaded: LoadedDocument, result: DocumentResult,
                        options: JobOptions) -> list:
        tables = []
        tesseract = self.registry.get("tesseract")
        for lpage in loaded.pages:
            page_res = next((p for p in result.pages if p.page_num == lpage.page_num), None)
            if lpage.image is not None and tesseract and tesseract.is_available():
                try:
                    # OCR de secours par cellule : psm 7 (ligne unique) plus fiable
                    # sur petits recadrages que le mode auto
                    from .ocr_engines import TesseractEngine
                    cell_engine = TesseractEngine(psm=7)
                    langs = options.languages or ["fra", "eng"]
                    ocr_cell = ocr_cell_factory(cell_engine.recognize, langs)
                    ruled = extract_ruled_table(
                        lpage.image, lpage.page_num,
                        ocr_cell=ocr_cell,
                        words=page_res.words if page_res else None)
                    if ruled and ruled.n_rows >= 2:
                        tables.append(ruled)
                        continue
                except Exception:
                    log.exception("extraction table à filets échouée page %s", lpage.page_num)
            if page_res and len(page_res.words) >= 8:
                borderless = extract_borderless_table(page_res.words, lpage.page_num)
                if borderless:
                    tables.append(borderless)
        return merge_multipage_tables(tables)

    # ------------------------------------------------------------------
    def _decode_barcodes(self, loaded: LoadedDocument) -> list[dict]:
        barcodes = []
        try:
            import zxingcpp
        except ImportError:
            return barcodes
        for lpage in loaded.pages:
            if lpage.image is None:
                continue
            try:
                for res in zxingcpp.read_barcodes(lpage.image):
                    poly = None
                    try:
                        pos = res.position
                        pts = []
                        for attr in ("topLeft", "topRight", "bottomRight", "bottomLeft"):
                            p = getattr(pos, attr, None)
                            if p is not None:
                                pts.append((p.x, p.y))
                        poly = pts or None
                    except Exception:
                        poly = None
                    barcodes.append({
                        "page": lpage.page_num,
                        "format": str(res.format),
                        "text": res.text,
                        "polygon": poly,
                    })
            except Exception:
                log.exception("décodage codes-barres échoué page %s", lpage.page_num)
        return barcodes


# ------------------------------------------------------------------ utilitaires
def parse_page_range(spec: str, total: int) -> list[int]:
    """Parse '1-3, 5' en liste de pages 1-based.

    Règles : entrée vide ou illisible = toutes les pages (tolérance) ;
    numéros hors document ignorés ; sélection vide après bornage → []
    (le pipeline refuse alors la demande au lieu d'agir en secret).
    """
    if not spec or not spec.strip():
        return list(range(1, total + 1))
    out: set[int] = set()
    try:
        for part in spec.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                a, b = (int(x) for x in part.split("-", 1))
                if a < 1 or b < 1:
                    raise ValueError("pages >= 1")
                out.update(range(min(a, b), max(a, b) + 1))
            else:
                n = int(part)
                if n < 1:
                    raise ValueError("pages >= 1")
                out.add(n)
    except ValueError:
        return list(range(1, total + 1))
    return sorted(p for p in out if p <= total)


def _detect_languages(text: str) -> list[str]:
    if not text or not text.strip():
        return []
    try:
        from langdetect import detect_langs
        langs = [ln.lang for ln in detect_langs(text[:3000]) if ln.prob > 0.2][:3]
        return langs or []
    except Exception:
        return []
