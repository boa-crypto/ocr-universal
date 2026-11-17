"""Stress réel isolé : un défaut natif ne doit pas tuer le processus pytest."""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from unocr.ingest import load_document


def main():
    directory, dpi = Path(sys.argv[1]), int(sys.argv[2])
    start = Barrier(4)
    names = ["text_pdf.pdf", "bl_port.pdf", "scanned_pdf.pdf"]

    def load(i):
        start.wait(timeout=10)
        pages = 0
        for _ in range(5):
            name = names[i % len(names)]
            result = load_document(directory / name, dpi=dpi)
            assert result.pages
            for page in result.pages:
                assert page.image.mode == "RGB"
                assert page.image.getpixel((0, 0)) is not None
                assert page.image.width > 0 and page.image.height > 0
            if name == "text_pdf.pdf":
                assert "FACTURE" in result.pages[0].native_text
            pages += len(result.pages)
        return pages

    with ThreadPoolExecutor(max_workers=4) as pool:
        pages = sum(pool.map(load, range(4)))
    print(json.dumps({"loads": 20, "pages": pages, "threads": 4, "dpi": dpi}))


if __name__ == "__main__":
    main()
