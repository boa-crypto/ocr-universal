"""Operational redesign: real list data, linked tabs and no invented permissions."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_operations_studio_runtime():
    subprocess.run(['node', 'tests/ui_operations_studio.cjs'], cwd=ROOT, check=True, timeout=30)


def test_studio_assets_and_native_integrity():
    html = (ROOT/'web/index.html').read_text()
    worker = (ROOT/'web/sw.js').read_text()
    js = (ROOT/'web/operations-studio.js').read_text()
    assert html.index('visual-motion.css') < html.index('operations-studio.css')
    assert html.index('product-experience.js') < html.index('operations-studio.js')
    for asset in ('operations-studio.js', 'operations-studio.css'):
        assert '/web/'+asset in worker
    for forbidden in ('fetch(', 'innerHTML', 'localStorage', 'sessionStorage', 'preventDefault('):
        assert forbidden not in js
    dossier = (ROOT/'web/dossiers.js').read_text()
    assert 'function voie(d)' in dossier
    assert 'return "autres"' in dossier
    assert 'Confiance · ' in dossier
    assert 'dossier-panel-' in dossier and 'aria-controls' in dossier


def test_source_freshness_runtime():
    subprocess.run(['node', 'tests/ui_source_freshness.cjs'], cwd=ROOT, check=True, timeout=30)


def test_legacy_date_placeholders_do_not_invent_an_epoch_opening_date():
    code = r"""
const assert = require('node:assert/strict'), fs = require('node:fs'), vm = require('node:vm');
const source = fs.readFileSync('web/ecrans.js', 'utf8');
const formatter = vm.runInNewContext(source.slice(source.indexOf('  var MOIS ='), source.indexOf('  function nombre(')) + ';horodatage;');
for (const value of [null, undefined, '', 0, '0']) assert.equal(formatter(value), '—');
assert.equal(formatter('2026-11-04T12:00:00Z'), '4 nov. 2026');
assert.equal(formatter(1793793600), '4 nov. 2026');
assert.equal(formatter(1793793600000), '4 nov. 2026');
assert.equal(formatter('date invalide'), 'date invalide');
"""
    subprocess.run(['node', '-e', code], cwd=ROOT, check=True, timeout=30)
