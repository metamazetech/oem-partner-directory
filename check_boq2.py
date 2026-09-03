import re

with open('templates/rfp_detail.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('Associated OEMs')
if idx > 0:
    # Print the table body that follows it
    tbody_start = content.find('<tbody', idx)
    tbody_end = content.find('</tbody>', tbody_start)
    if tbody_start > 0 and tbody_end > 0:
        with open('boq_out.txt', 'w', encoding='utf-8') as out:
            out.write(content[tbody_start:tbody_end+100])
