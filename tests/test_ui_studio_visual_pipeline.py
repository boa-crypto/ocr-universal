"""Opt-in real Chromium + native OCR on an isolated temporary business store."""
import json
import os
import subprocess
from pathlib import Path

import httpx
import pytest

pytest_plugins = ['ui_render_server']
ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(os.environ.get('UI_STUDIO_BROWSER') != '1', reason='Opt-in Chromium: UI_STUDIO_BROWSER=1')
def test_native_source_and_operational_journeys(ui_render_port, tmp_path):
    base = f'http://127.0.0.1:{ui_render_port}'
    out = Path(os.environ.get('UI_STUDIO_ARTIFACTS', str(tmp_path/'studio-browser')))
    out.mkdir(parents=True, exist_ok=True)
    with httpx.Client(base_url=base, timeout=30, trust_env=False) as client:
        jobs = client.get('/api/jobs').raise_for_status().json()
        assert len(jobs) >= 2
        dossier = client.post('/api/dossiers', json={'label': 'Recette visuelle isolée — sources natives', 'profile': 'importation'}).raise_for_status().json()
        for job in jobs:
            client.post(f'/api/dossiers/{dossier["id"]}/pieces', json={'job_id':job['id'],'filename':job['filename']}).raise_for_status()
    run = subprocess.run(['node','tests/ui_operations_studio_browser.cjs',str(out)], cwd=ROOT, env={**os.environ,'UI_BASE':base}, capture_output=True, text=True, timeout=360)
    (out/'runner.log').write_text(run.stdout+run.stderr)
    assert run.returncode == 0, run.stdout+run.stderr
    report = json.loads((out/'report.json').read_text())
    assert len(report) == 4
    assert all(case['sourceInspectorHTTP'] == 200 for case in report)
