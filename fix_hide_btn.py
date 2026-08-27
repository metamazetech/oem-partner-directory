import os

for root, dirs, files in os.walk('templates'):
    for file in files:
        if not file.endswith('.html'):
            continue
        path = os.path.join(root, file)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'sidebar-collapse-btn' not in content:
            continue
        
        # Update the hide button onclick to also show the show-sidebar-btn
        old_onclick = """onclick="this.closest('.sidebar').style.display='none';document.getElementById('show-sidebar-btn').style.display='flex';localStorage.setItem('sidebar-collapsed','true');\""""
        new_onclick = """onclick="this.closest('.sidebar').style.display='none';var b=document.getElementById('show-sidebar-btn');if(b)b.style.display='flex';localStorage.setItem('sidebar-collapsed','true');\""""
        
        content = content.replace(old_onclick, new_onclick)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Updated {file}')

print('Done!')
