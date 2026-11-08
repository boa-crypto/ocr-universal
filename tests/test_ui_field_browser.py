"""Opt-in real Chromium audit; no writes to the user's store."""
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(os.environ.get('UI_FIELD_BROWSER') != '1', reason='Real Chromium opt-in')
def test_all_routes_and_native_states_in_real_browser(tmp_path):
    subprocess.run(['node', 'tests/ui_field_contrast_browser.cjs', str(tmp_path)], cwd=ROOT, check=True, timeout=600)
