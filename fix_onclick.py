import os

for root, dirs, files in os.walk('templates'):
    for file in files:
        if not file.endswith('.html'):
            continue
        path = os.path.join(root, file)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'Hide Sidebar' not in content:
            continue
        
        # Fix the onclick to use the global hideSidebar function
        content = content.replace(
            """onclick="document.querySelector('.sidebar').style.display='none'; localStorage.setItem('sidebar-collapsed','true');\"""",
            """onclick="hideSidebar();\""""
        )
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Updated {file}')

print('Done!')
