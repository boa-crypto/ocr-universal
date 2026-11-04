import re
from pathlib import Path

html_path = Path('C:/workSpace/ocr-universal/web/index.html')
html = html_path.read_text(encoding='utf-8')

# Find the description meta tag and add CSS after it
# Use regex to find and replace
pattern = r'(<meta name="description" content="UniOCC — moteur OCR universel local : texte, structure, champs, tableaux, codes-barres\.">)'
replacement = r'\1' + '''\\
  <style>
    /* Rules for RTL language support */
    [dir="rtl"] { direction: rtl; unicode-bidi: embed; }
  </style>'''

new_html = re.sub(pattern, replacement, html, count=1)

if new_html != html:
    html_path.write_text(new_html, encoding='utf-8')
    print('CSS rule added successfully')
else:
    print('Pattern not found, trying alternative...')
    # Try direct string replacement
    old = '<meta name="description" content="UniOCC — moteur OCR universel local : texte, structure, champs, tableaux, codes-barres.">'
    new = old + '''\\
  <style>
    /* Rules for RTL language support */
    [dir="rtl"] { direction: rtl; unicode-bidi: embed; }
  </style>'''
    if old in html:
        new_html = html.replace(old, new)
        html_path.write_text(new_html, encoding='utf-8')
        print('CSS rule added via direct replacement')
    else:
        print('Direct replacement also failed')
        # List what description metas exist
        metas = re.findall(r'<meta name="description"[^>]*>', html)
        for m in metas:
            print('  Found:', m[:80])