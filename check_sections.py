import re
with open('web/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the import section end
import_start = content.find('id="tab-import"')
# Find the first </section> after import_start
first_close = content.find('</section>', import_start)
# Find the second </section>
second_close = content.find('</section>', first_close + 10)
# Find the third </section> (which would be the tab-docs closing)
third_close = content.find('</section>', second_close + 10)

with open('section_check.txt', 'w', encoding='utf-8') as out:
    out.write(f'First close at: {first_close}\n')
    out.write(f'Context: {repr(content[first_close-30:first_close+30])}\n\n')
    out.write(f'Second close at: {second_close}\n')
    out.write(f'Context: {repr(content[second_close-30:second_close+30])}\n\n')
    out.write(f'Third close at: {third_close}\n')
    out.write(f'Context: {repr(content[third_close-30:third_close+30])}\n')
print("Done")