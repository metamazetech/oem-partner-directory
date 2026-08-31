import os
for f in os.listdir('templates'):
    if not f.endswith('.html'): continue
    with open(os.path.join('templates', f), 'r', encoding='utf-8') as fh:
        content = fh.read()
    if '"side class="sidebar"' in content:
        print('Found broken tag in', f)
print('Done checking')
