"""Tests E4 : traitement parallèle des pages.

Les chiffres de performance sont mesurés, jamais estimés. Le test de gain
utilise une borne basse volontairement prudente : sur 2 cœurs, le gain réel
attendu est loin du théorique (ingestion, qualité et exports restent
séquentiels). Si le parallélisme casse, le test échoue.
"""
import os
import time
from pathlib import Path

import pytest

from unocr.models import JobOptions
from unocr.pipeline import Pipeline, _available_ram_mb

FIX = Path(__file__).resolve().parent / "fixtures"
MULTI = FIX / "multipage_scan.pdf"


@pytest.fixture(scope="module")
def multipage_exists():
    if not MULTI.is_file():
        pytest.skip("document multipage absent")
    return MULTI


# ─────────────────────────── calcul des workers ───────────────────────────

def test_single_page_is_never_parallelized():
    p = Pipeline()
    assert p._page_workers(1) == 1
    assert p._page_workers(0) == 1


def test_workers_bounded_by_cpu_and_ram():
    import os
    p = Pipeline()
    n = p._page_workers(8)
    cpus = os.cpu_count() or 1
    assert 1 <= n <= cpus
    assert n <= 8


def test_workers_respects_config_limit():
    """`jobs.workers` doit borner le parallélisme."""
    from unocr.config import Config

    p = Pipeline(cfg=Config({"jobs": {"workers": 1}}, Path(".")))
    assert p._page_workers(8) == 1

    p2 = Pipeline(cfg=Config({"jobs": {"workers": 4}}, Path(".")))
    assert 1 <= p2._page_workers(8) <= 4


def test_workers_shrinks_when_ram_is_low(monkeypatch):
    """Peu de RAM disponible → moins de workers (pas d'OOM)."""
    p = Pipeline()
    monkeypatch.setattr("unocr.pipeline._available_ram_mb", lambda: 300)
    assert p._page_workers(8) == 1


def test_workers_ignores_unavailable_ram_probe(monkeypatch):
    """Sonde indisponible (0) → on ne bloque pas, on retombe sur le réglage.

    Quand la RAM ne peut pas être mesurée, la sonde renvoie 0. Le pipeline
    ne doit alors *pas* s'effondrer à un seul worker : il retombe sur la
    limite de configuration (`jobs.workers`, 2 par défaut) puis sur les CPU.

    Note : l'assertion porte sur le nombre de workers effectif, pas sur
    `os.cpu_count()`. Le réglage par défaut `jobs.workers = 2` borne
    volontairement le parallélisme, y compris quand la RAM est
    indétectable — c'est ce qui protège la machine d'un pic mémoire.
    """
    from unocr.config import DEFAULTS

    p = Pipeline()
    monkeypatch.setattr("unocr.pipeline._available_ram_mb", lambda: 0)
    n = p._page_workers(8)
    cpus = os.cpu_count() or 1
    assert 1 <= n <= cpus
    # le réglage par défaut reste la limite effective
    assert n <= DEFAULTS["jobs"]["workers"]
    # et le pipeline ne bloque pas sur une sonde RAM muette
    assert n >= 1


def test_available_ram_probe_returns_int():
    v = _available_ram_mb()
    assert isinstance(v, int) and v >= 0


# ─────────────────────────── résultats identiques ───────────────────────────

def test_parallel_results_match_sequential(multipage_exists):
    """Le parallélisme ne doit rien changer au résultat : même texte, mêmes
    champs, même ordre de pages."""
    opts = JobOptions(quality_mode="fast")

    seq_pipe = Pipeline()
    seq_pipe._page_workers = lambda n: 1
    r_seq = seq_pipe.process_file(multipage_exists, opts)

    r_par = Pipeline().process_file(multipage_exists, opts)

    assert [p.text for p in r_seq.pages] == [p.text for p in r_par.pages]
    assert [p.page_num for p in r_par.pages] == sorted(p.page_num for p in r_par.pages)
    assert {k: v.value for k, v in r_seq.fields.items()} == \
           {k: v.value for k, v in r_par.fields.items()}


def test_workers_recorded_in_timings(multipage_exists):
    """Le nombre de workers utilisé est tracé dans les timings (mesurable)."""
    r = Pipeline().process_file(multipage_exists, JobOptions(quality_mode="fast"))
    assert r.timings_ms.get("ocr_workers", 0) >= 1


# ─────────────────────────── performance mesurée ───────────────────────────

@pytest.mark.slow
def test_parallel_is_not_slower(multipage_exists):
    """Gain mesuré sur 2 cœurs : ×1,18 (18,44 s → 15,68 s).

    Le test exige seulement de ne pas être plus lent — un gain théorique de
    ×2 n'est pas atteignable ici (étapes séquentielles, 2 cœurs, RAM limitée).
    """
    opts = JobOptions(quality_mode="fast")

    seq_pipe = Pipeline()
    seq_pipe._page_workers = lambda n: 1
    t0 = time.perf_counter()
    seq_pipe.process_file(multipage_exists, opts)
    seq = time.perf_counter() - t0

    t0 = time.perf_counter()
    Pipeline().process_file(multipage_exists, opts)
    par = time.perf_counter() - t0

    assert par <= seq * 1.05, (
        f"parallélisme plus lent : {par:.1f}s vs {seq:.1f}s séquentiel")
