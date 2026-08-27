import os, re

for root, dirs, files in os.walk('templates'):
    for file in files:
        if file.endswith('.html'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            content = content.replace('?v=3.3', '?v=3.5')
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
print('Bumped all to v=3.5')
