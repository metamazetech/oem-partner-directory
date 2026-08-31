import os
import re

for root, dirs, files in os.walk('templates'):
    for file in files:
        if file.endswith('.html'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # The tooltips script replaced <aside with `<a title="..."side`
            # Let's fix that back to <aside class="sidebar">
            
            # Pattern to match the broken tag block which looks like:
            # <a title="{% if portal_settings['portal_logo'] %} ... {% endif %}"side class="sidebar">
            # We can use a regex to replace it
            new_content = re.sub(
                r'<a title="\{% if portal_settings\[\'portal_logo\'\] %\}.*?\{% endif %\}"side class="sidebar">',
                r'<aside class="sidebar">',
                content,
                flags=re.DOTALL
            )
            
            if new_content != content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f'Fixed broken sidebar tag in {file}')

print('Done')
