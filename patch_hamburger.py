import os

html_to_inject = '''
    <!-- Mobile Hamburger Toggle -->
    <button id="global-mobile-toggle" class="mobile-toggle-btn" onclick="document.querySelector('.sidebar').classList.toggle('menu-open')" style="display: none;">☰</button>
'''

for file in os.listdir('templates'):
    if file.endswith('.html'):
        path = os.path.join('templates', file)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Inject just inside the body
        if 'id="global-mobile-toggle"' not in content:
            content = content.replace('<body', html_to_inject + '<body')
            # wait, `<body` replacing might break attributes. Better to replace `<div class="app-container">`
            content = content.replace('<div class="app-container">', '<div class="app-container">\n' + html_to_inject)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
                print(f"Patched {file}")
