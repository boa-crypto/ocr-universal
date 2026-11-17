"""Doubles unitaires : verrou et fermeture, pas preuve d'extraction réelle."""
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, RLock, get_ident

import pytest
from PIL import Image

from unocr import ingest
from unocr.models import BBox, Word
from unocr.security import SecurityError


class TrackedLock:
    def __init__(self):
        self.lock = RLock()
        self.owner = None

    def __enter__(self):
        self.lock.acquire()
        assert self.owner is None
        self.owner = get_ident()
        return self

    def __exit__(self, *args):
        self.owner = None
        self.lock.release()


@pytest.fixture
def native_double(monkeypatch):
    import pdfminer.high_level
    import pypdfium2

    lock = TrackedLock()
    state = {"failure": None, "objects": [], "events": []}
    monkeypatch.setattr(ingest, "_PDFIUM_LOCK", lock)

    def checkpoint(stage):
        assert lock.owner == get_ident(), (stage, "appel natif hors verrou")
        state["events"].append(stage)
        if state["failure"] == stage:
            raise RuntimeError(stage)

    class Native:
        def __init__(self, name):
            self.name = name
            self.closed = False
            state["objects"].append(self)

        def close(self):
            checkpoint("close_" + self.name)
            assert not self.closed
            self.closed = True

    class Bitmap(Native):
        def to_pil(self):
            checkpoint("to_pil")
            return Pixels()

    class Pixels:
        def convert(self, mode):
            checkpoint("convert")
            assert mode == "RGB"
            return Image.new(mode, (8, 6), (10, 20, 30))

    class Page(Native):
        def get_size(self):
            checkpoint("get_size")
            return 8, 6

        def render(self, **kwargs):
            checkpoint("render")
            time.sleep(0.002)
            return Bitmap("bitmap")

    class Document(Native):
        def __init__(self, path):
            checkpoint("construct")
            super().__init__("document")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

        def __len__(self):
            checkpoint("length")
            return 2

        def __getitem__(self, index):
            checkpoint("get_page")
            return Page("page")

    def layouts(*args, **kwargs):
        checkpoint("layouts")
        return [object(), object()]

    def words(*args):
        checkpoint("native")
        return "NATIVE", [Word(text="NATIVE", bbox=BBox(x0=1, y0=1, x1=7, y1=4))], []

    monkeypatch.setattr(pypdfium2, "PdfDocument", Document)
    monkeypatch.setattr(pdfminer.high_level, "extract_pages", layouts)
    monkeypatch.setattr(ingest, "_pdf_native_words", words)
    return state


@pytest.mark.parametrize("failure", [
    "construct", "length", "layouts", "get_page", "get_size", "native",
    "render", "to_pil", "convert", "limit", None,
])
def test_native_lifetime_and_exception_release(native_double, tmp_path, failure):
    state = native_double
    state["failure"] = failure
    if failure:
        error = SecurityError if failure == "limit" else RuntimeError
        with pytest.raises(error):
            ingest._load_pdf(tmp_path / "double.pdf", 72, max_pages=1 if failure == "limit" else 2)
    else:
        result = ingest._load_pdf(tmp_path / "double.pdf", 72)
        assert len(result.pages) == 2
        assert result.pages[1].native_words[0].page_num == 2
        assert result.pages[0].image.getpixel((0, 0)) == (10, 20, 30)
    assert all(obj.closed for obj in state["objects"])
    if failure == "limit":
        assert "layouts" not in state["events"]
    state["failure"] = None
    # Un autre thread doit pouvoir reprendre, même après une erreur.
    with ThreadPoolExecutor(max_workers=1) as pool:
        assert len(pool.submit(ingest._load_pdf, tmp_path / "double.pdf", 72).result(timeout=5).pages) == 2
    assert all(obj.closed for obj in state["objects"])


def test_concurrent_calls_keep_every_native_operation_locked(native_double, tmp_path):
    start = Barrier(4)

    def load(i):
        start.wait(timeout=5)
        return ingest._load_pdf(tmp_path / f"double-{i}.pdf", 72)

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(load, range(4)))
    assert all(len(result.pages) == 2 for result in results)
    assert all(obj.closed for obj in native_double["objects"])
    closures = [event for event in native_double["events"] if event.startswith("close_")]
    assert closures == ["close_bitmap", "close_page", "close_bitmap", "close_page", "close_document"] * 4
