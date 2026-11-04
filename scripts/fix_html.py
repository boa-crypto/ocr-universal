#!/usr/bin/env python3
"""Fix web/index.html to match test expectations."""
from pathlib import Path

html_path = Path('C:/workSpace/ocr-universal/web/index.html')
html = html_path.read_text(encoding='utf-8')

# 1. Remove the inline style block we added (with the RTL rule)
old_style = '''\n  <style>\n    /* Rules for RTL language support */\n    [dir="rtl"] { direction: rtl; unicode-bidi: embed; }\n  </style>'''
if old_style in html:
    html = html.replace(old_style, '')
    print('Removed inline style block')

# 2. Change absolute script paths back to relative
replacements = {
    '/connectors.js': 'connectors.js',
    '/dossier.js': 'dossier.js',
    '/formulaire.js': 'formulaire.js',
    '/tracabilite.js': 'tracabilite.js',
    '/transmission.js': 'transmission.js',
}
for old, new in replacements.items():
    html = html.replace(old, new)
print('Changed script paths back to relative')

# 3. Add defer to script tags
html = html.replace('<script src="connectors.js"></script>', '<script src="connectors.js" defer></script>')
html = html.replace('<script src="dossier.js"></script>', '<script src="dossier.js" defer></script>')
html = html.replace('<script src="formulaire.js"></script>', '<script src="formulaire.js" defer></script>')
html = html.replace('<script src="tracabilite.js"></script>', '<script src="tracabilite.js" defer></script>')
html = html.replace('<script src="transmission.js"></script>', '<script src="transmission.js" defer></script>')
print('Added defer to script tags')

html_path.write_text(html, encoding='utf-8')
print('HTML updated successfully')