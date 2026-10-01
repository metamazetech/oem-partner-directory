import os
import re

for root, _, files in os.walk('templates'):
    for f in files:
        if f.endswith('.html'):
            filepath = os.path.join(root, f)
            with open(filepath, 'r', encoding='utf-8') as file:
                content = file.read()
            
            content = re.sub(r'<li class="nav-item \{% if request\.endpoint == \'excel_tool\.index\' %\}.*?</li>', '', content, flags=re.DOTALL)
            content = re.sub(r'<li class="nav-item \{% if request\.endpoint == \'system_builder\.index\' %\}.*?</li>', '', content, flags=re.DOTALL)
            
            with open(filepath, 'w', encoding='utf-8') as file:
                file.write(content)
print('Removed from sidebar!')
