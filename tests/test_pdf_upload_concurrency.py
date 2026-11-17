"""Dépôts HTTP concurrents, serveur isolé, PDF natifs synthétiques réels."""
import hashlib
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import httpx

pytest_plugins = ["ui_render_server"]


def test_concurrent_pdf_uploads_keep_server_alive_and_results_distinct(ui_render_port, fixtures_dir):
    base = f"http://127.0.0.1:{ui_render_port}"
    start = Barrier(4)

    def upload(i):
        source = fixtures_dir / ("text_pdf.pdf" if i % 2 == 0 else "bl_port.pdf")
        content = source.read_bytes()
        start.wait(timeout=10)
        with httpx.Client(base_url=base, timeout=30, trust_env=False) as client:
            response = client.post("/api/documents", files={"file": (f"concurrent-{i}.pdf", content, "application/pdf")},
                                   data={"engine": "native", "quality_mode": "fast", "extract_tables": "false",
                                         "extract_barcodes": "false", "dedupe": "false"})
            response.raise_for_status()
            return response.json()["job_id"], hashlib.sha256(content).hexdigest(), 2 if i % 2 == 0 else 1

    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = list(pool.map(upload, range(4)))
    assert len({job for job, _, _ in jobs}) == 4
    with httpx.Client(base_url=base, timeout=30, trust_env=False) as client:
        deadline = time.monotonic() + 60
        while True:
            states = [client.get(f"/api/jobs/{job}").raise_for_status().json() for job, _, _ in jobs]
            assert all(state["status"] != "error" for state in states), states
            if all(state["status"] == "done" for state in states):
                break
            assert time.monotonic() < deadline, states
            time.sleep(0.1)
        assert all(state["attempts"] == 1 for state in states)
        for job, digest, count in jobs:
            result = client.get(f"/api/jobs/{job}/result").raise_for_status().json()
            assert result["source_hash"] == digest
            assert len(result["pages"]) == count
            assert result["engines_used"] == ["native_pdf"]
            assert all(page["has_native_text"] and page["text"] for page in result["pages"])
        assert client.get("/api/health").raise_for_status().json()["status"] == "ok"
