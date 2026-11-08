"""Semantic input colors: central pairs, state contrast and offline delivery."""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def luminance(color):
    channels = [int(color[i:i+2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in channels]
    return sum(c * k for c, k in zip(linear, (.2126, .7152, .0722)))


def contrast(a, b):
    a, b = sorted((luminance(a), luminance(b)))
    return (b + .05) / (a + .05)


@pytest.mark.parametrize('theme', ['light', 'dark'])
def test_field_tokens_have_aa_contrast_in_every_surface(theme):
    css = (ROOT / 'web/field-accessibility.css').read_text()
    block = re.search(r'\[data-theme="' + theme + r'"\]\s*\{([^}]+)', css).group(1)
    tokens = dict(re.findall(r'--field-([\w-]+):\s*(#[\da-f]{6})', block))
    assert contrast(tokens['choice-text'], tokens['focus']) >= 4.5
    for bg in ('bg', 'muted-bg'):
        for fg in ('text', 'placeholder'):
            assert contrast(tokens[fg], tokens[bg]) >= 4.5
        for fg in ('border', 'focus', 'error', 'success'):
            assert contrast(tokens[fg], tokens[bg]) >= 3


def test_field_contract_loaded_after_legacy_styles_and_cached():
    html = (ROOT / 'web/index.html').read_text()
    assert html.index('/web/field-accessibility.css') > html.index('/web/operations-studio.css')
    assert '/web/field-accessibility.css' in (ROOT / 'web/sw.js').read_text()
    css = (ROOT / 'web/field-accessibility.css').read_text()
    for contract in ('-webkit-text-fill-color', 'caret-color', '::placeholder', ':autofill', 'option', 'optgroup', '[readonly]', ':disabled', ':user-invalid', 'forced-colors', '[role="listbox"]'):
        assert contract in css
    source = (ROOT / 'web/uniocr-ds.css').read_text()
    assert 'background: var(--field-bg, var(--ds-surface))' in source
    assert 'input:where(' in css  # exclusions must not outrank error/readonly/focus states
