with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re
for m in re.finditer(r'@app\.route\(.*?\)', content):
    if 'search' in m.group(0):
        print(m.group(0))
