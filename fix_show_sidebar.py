import os, re

for root, dirs, files in os.walk('templates'):
    for file in files:
        if not file.endswith('.html'):
            continue
        path = os.path.join(root, file)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'class="sidebar"' not in content:
            continue
        
        # 1. Remove old show-sidebar-btn button and its script if present
        content = re.sub(
            r'<button id="show-sidebar-btn"[^>]*>[^<]*</button>\s*<script>.*?</script>',
            '',
            content,
            flags=re.DOTALL
        )
        
        # 2. Remove any JS sidebar toggle code reference from main.js DOMContentLoaded in the template
        # (the main.js code will still exist but won't conflict)
        
        # 3. Add a clean show-sidebar solution right before </body>
        show_sidebar_block = '''
    <!-- Sidebar Show Button (appears when sidebar is hidden) -->
    <div id="show-sidebar-btn" style="position:fixed;top:12px;left:0;z-index:9999;display:none;">
        <button onclick="var s=document.querySelector('.sidebar');s.style.display='';this.parentElement.style.display='none';localStorage.setItem('sidebar-collapsed','false');" style="background:linear-gradient(135deg,#6366f1,#8b5cf6);color:white;border:none;border-radius:0 10px 10px 0;width:32px;height:48px;cursor:pointer;box-shadow:2px 0 12px rgba(99,102,241,0.4);font-size:1.4rem;display:flex;align-items:center;justify-content:center;">&raquo;</button>
    </div>
    <script>
    (function(){
        if(localStorage.getItem('sidebar-collapsed')==='true'){
            var s=document.querySelector('.sidebar');
            var b=document.getElementById('show-sidebar-btn');
            if(s) s.style.display='none';
            if(b) b.style.display='block';
        }
    })();
    </script>
'''
        content = content.replace('</body>', show_sidebar_block + '</body>')
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Updated {file}')

print('Done!')
