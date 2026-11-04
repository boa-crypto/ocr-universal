import re

# Read the index.html file
with open('web/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Read the refactored import section
with open('import_refactored.html', 'r', encoding='utf-8') as f:
    new_import = f.read()

# Find and replace the #tab-import section
# The section starts with "<!-- ─────────── 01 · IMPORT ─────────── -->" and ends before "<!-- ─────────── 02 · DOCUMENTS ─────────── -->"
pattern = r'(<!-- ─────────── 01 · IMPORT ─────────── -->.*?)</section>\s*(?=<!-- ─────────── 02 · DOCUMENTS ─────────── -->)'

# Use DOTALL flag to match across newlines
new_content = re.sub(pattern, new_import + '\n      </section>', content, flags=re.DOTALL)

# Write back
with open('web/index.html', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Replacement completed successfully!")