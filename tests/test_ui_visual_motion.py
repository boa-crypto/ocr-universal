"""Premium motion is optional; permissions, data and content remain authoritative."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_motion_runtime():
    subprocess.run(['node', 'tests/ui_visual_motion.cjs'], cwd=ROOT, check=True, timeout=30)


def test_visual_assets_offline_csp_and_progressive_enhancement():
    html = (ROOT/'web/index.html').read_text()
    worker = (ROOT/'web/sw.js').read_text()
    css = (ROOT/'web/visual-motion.css').read_text()
    js = (ROOT/'web/visual-motion.js').read_text()
    for asset in ('visual-motion.js', 'visual-motion.css', 'assets/document-flow.svg'):
        assert '/web/'+asset in worker
        assert (ROOT/'web'/asset).is_file()
    assert html.index('product-experience.js') < html.index('visual-motion.js')
    assert 'width="600" height="400"' in html
    assert 'prefers-reduced-motion:reduce' in css.replace(' ', '')
    assert 'opacity:0;' not in css.replace(' ', '')
    assert all(api not in js for api in ('fetch(', 'innerHTML', 'localStorage', '.textContent = next'))
    assert (ROOT/'web/assets/document-flow.svg').stat().st_size < 10000
