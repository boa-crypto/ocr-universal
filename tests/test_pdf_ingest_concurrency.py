"""PDFium réel, documents synthétiques, processus sacrifiable avec timeout."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("dpi", [72, 100, 144])
def test_real_concurrent_ingestion_in_child(fixtures_dir, dpi):
    worker = Path(__file__).with_name("_pdf_ingest_thread_worker.py")
    result = subprocess.run([sys.executable, str(worker), str(fixtures_dir), str(dpi)],
                            env={**os.environ, "PYTHONFAULTHANDLER": "1"},
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == {"loads": 20, "pages": 30, "threads": 4, "dpi": dpi}
