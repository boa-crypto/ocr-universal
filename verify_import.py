import re
with open('web/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the import section end
import_start = content.find('id="tab-import"')
# Find the first </section> after import_start
first_close = content.find('</section>', import_start)
# Find the second </section>
second_close = content.find('</section>', first_close + 10)

# The import section should be from import_start to first_close + 10
import_section = content[import_start:first_close + 10]
open_count = import_section.count('<section')
close_count = import_section.count('</section>')

with open('verify_result.txt', 'w', encoding='utf-8') as out:
    out.write(f'Import section: {open_count} opening, {close_count} closing\n')
    out.write(f'Import section length: {len(import_section)}\n')
    out.write(f'Ends with: {repr(import_section[-50:])}\n\n')

    # Check what's between first and second close (should be tab-docs)
    between = content[first_close + 10:second_close + 10]
    out.write(f'Between first and second close: {len(between)} chars\n')
    out.write(f'Starts with: {repr(between[:100])}\n')
    out.write(f'Contains tab-docs: {"tab-docs" in between}\n')
    tab_docs_check = 'id="tab-docs"' in between
    out.write(f'Contains id="tab-docs": {tab_docs_check}\n')

print("Done")