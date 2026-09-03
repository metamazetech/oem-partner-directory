import re

with open('templates/rfp_detail.html', 'r', encoding='utf-8') as f:
    content = f.read()

# find BOQ items block
idx = content.find('boq-table-body')
if idx > 0:
    print(content[idx:idx+1500])
