import os
import re

path = os.path.join('templates', 'work_tools.html')
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

new_content = re.sub(
    r'<a title="\{% if portal_settings\.get.*?\{% endif %\}"side class="sidebar">',
    r'<aside class="sidebar">',
    content,
    flags=re.DOTALL
)

if new_content != content:
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f'Fixed broken sidebar tag in work_tools.html')
else:
    print('Still did not match')
