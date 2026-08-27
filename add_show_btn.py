import os

show_btn_html = '''<button id="show-sidebar-btn" onclick="document.querySelector('.sidebar').style.display='';this.style.display='none';localStorage.setItem('sidebar-collapsed','false');" style="position:fixed;top:50%;left:0;transform:translateY(-50%);z-index:9999;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:white;border:none;border-radius:0 8px 8px 0;width:28px;height:56px;display:none;align-items:center;justify-content:center;cursor:pointer;box-shadow:2px 0 12px rgba(99,102,241,0.4);font-size:1.3rem;">&raquo;</button>
    <script>if(localStorage.getItem('sidebar-collapsed')==='true'){var sb=document.querySelector('.sidebar');if(sb){sb.style.display='none';}var btn=document.getElementById('show-sidebar-btn');if(btn){btn.style.display='flex';}}</script>'''

for root, dirs, files in os.walk('templates'):
    for file in files:
        if not file.endswith('.html'):
            continue
        path = os.path.join(root, file)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Skip if no sidebar (like login page, rfp_unlock)
        if 'class="sidebar"' not in content and "class='sidebar'" not in content:
            continue
        
        # Skip if already has show-sidebar-btn in HTML
        if 'show-sidebar-btn' in content and '<button id="show-sidebar-btn"' in content:
            continue
        
        # Insert right after <body ...>
        import re
        content = re.sub(
            r'(<body[^>]*>)',
            r'\1\n    ' + show_btn_html,
            content,
            count=1
        )
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Updated {file}')

print('Done!')
