with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

import re
old_div = '<div class="grid-stack-item-content" style="display: flex; justify-content: space-between; align-items: center;">'
new_div = '<div class="grid-stack-item-content" style="display: flex; justify-content: space-between; align-items: center; width: 100%; height: 100%;">'

if old_div in content:
    content = content.replace(old_div, new_div)
    with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Patched stats cards alignment!')
else:
    print('old_div not found in dashboard.html')
