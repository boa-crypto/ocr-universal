#!/usr/bin/env python3
from pathlib import Path

html = Path('C:/workSpace/ocr-universal/web/index.html').read_text(encoding='utf-8')

# Add a style block with [dir='rtl'] rule after the description meta tag
old = '<meta name="description" content="UniOCR — moteur OCR universel local : texte, structure, champs, tableaux, codes-barres.">'
new = '<meta name="description" content="UniOCR — moteur OCR universel local : texte, structure, champs, tableaux, codes-barres.">' + '''\\
  <style>
    /* Rules for RTL language support */
    [dir="rtl"] { direction: rtl; unicode-bidi: embed; }
  </style>'''

if old in html:
    html = html.replace(old, new)
    Path('C:/workSpace/ocr-universal/web/index.html').write_text(html, encoding='utf-8')
    print('CSS rule added successfully')
else:
    print('Insert point not found')
    # Try with escaped quotes
    old2 = '\"' + '<meta name=\"description\" content=\"UniOCR — moteur OCR universel local : texte, structure, champs, tableaux, codes-barres.\">' + '\"'
    print('Looking for:', repr(old2[:50]))