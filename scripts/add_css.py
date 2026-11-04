#!/usr/bin/env python3
from pathlib import Path

html = Path('C:/workSpace/ocr-universal/web/index.html').read_text(encoding='utf-8')

# Add a style block with [dir='rtl'] rule - find the description meta and insert after it
insert_after = '<meta name="description" content="UniOCR — moteur OCR universel local : texte, structure, champs, tableaux, codes-barres.">'
new_block = insert_after + '''\\
  <style>
    /* Rules for RTL language support */
    [dir="rtl"] { direction: rtl; unicode-bidi: embed; }
  </style>'''

if insert_after in html:
    html = html.replace(insert_after, new_block)
    Path('C:/workSpace/ocr-universal/web/index.html').write_text(html, encoding='utf-8')
    print('CSS rule added successfully')
else:
    print('Insert point not found')
    # Try alternative location
    print('Looking for description meta...')
    if '<meta name="description"' in html:
        print('Description meta found')