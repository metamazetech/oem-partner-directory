import os

for file in os.listdir('templates'):
    if file.endswith('.html'):
        path = os.path.join('templates', file)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove the inner toggle button
        inner_btn1 = '<button id="mobile-nav-toggle" class="mobile-toggle-btn">☰</button>'
        inner_btn2 = '<button id="mobile-nav-toggle" class="mobile-toggle-btn" onclick="document.querySelector(\'.sidebar\').classList.toggle(\'menu-open\')">☰</button>'
        
        changed = False
        if inner_btn1 in content:
            content = content.replace(inner_btn1, '')
            changed = True
        if inner_btn2 in content:
            content = content.replace(inner_btn2, '')
            changed = True
            
        if changed:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Removed inner toggle from {file}")
