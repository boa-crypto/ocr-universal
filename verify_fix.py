#!/usr/bin/env python3
from pathlib import Path
import re

html = Path('C:/workSpace/ocr-universal/web/index.html').read_text(encoding='utf-8')
mod = Path('C:/workSpace/ocr-universal/web/modules/i18n-controls.js').read_text(encoding='utf-8') if Path('C:/workSpace/ocr-universal/web/modules/i18n-controls.js').exists() else ''

combined = html + '\n' + mod

# Check RTL test
print('=== test_rtl_switching_logic_present ===')
print('dir=rtl string:', 'document.documentElement.dir = rtl' in combined)
print('rtl keyword:', 'rtl' in combined)
print('dir=rtl selector:', '[dir="rtl"]' in combined)

# Check external resources
print()
print('=== test_no_external_resource_for_i18n ===')
srcs = re.findall(r'src="([^"]+)"', combined)
for s in srcs:
    print(f'  "{s}" starts with "/": {s.startswith("/")}')