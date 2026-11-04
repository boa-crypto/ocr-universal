#!/usr/bin/env python3
from pathlib import Path
import re

html_path = Path('C:/workSpace/ocr-universal/web/index.html')
html = html_path.read_text(encoding='utf-8')

# Find </head> and insert CSS before it
head_close = html.find('</head>')
if head_close > 0:
    css_block = '\n  <style>\n    /* Rules for RTL language support */\n    [dir="rtl"] { direction: rtl; unicode-bidi: embed; }\n  </style>'

    new_html = html[:head_close] + css_block + html[head_close:]
    html_path.write_text(new_html, encoding='utf-8')
    print('CSS block inserted before </head> successfully')
else:
    print('</head> not found in HTML')
    # List what tags we have
    import re
    heads = re.findall(r'<head[^>]*>', html, re.IGNORECASE)
    print('Head tags found:', heads)