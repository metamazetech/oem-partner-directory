import os

html_to_inject = '''
    <!-- Mobile Hamburger Toggle -->
    <div class="sidebar-overlay" onclick="toggleMobileSidebar()"></div>
    <button id="global-mobile-toggle" class="mobile-toggle-btn" onclick="toggleMobileSidebar()" style="display: none;">☰</button>
    
    <script>
    function toggleMobileSidebar() {
        const sidebar = document.querySelector('.sidebar');
        const overlay = document.querySelector('.sidebar-overlay');
        if (sidebar.classList.contains('menu-open')) {
            sidebar.classList.remove('menu-open');
            if(overlay) overlay.classList.remove('active');
        } else {
            sidebar.classList.add('menu-open');
            if(overlay) overlay.classList.add('active');
        }
    }
    </script>
'''

old_toggle = '''<!-- Mobile Hamburger Toggle -->
    <button id="global-mobile-toggle" class="mobile-toggle-btn" onclick="document.querySelector('.sidebar').classList.toggle('menu-open')" style="display: none;">☰</button>'''

for file in os.listdir('templates'):
    if file.endswith('.html'):
        path = os.path.join('templates', file)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if old_toggle in content:
            content = content.replace(old_toggle, html_to_inject)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Patched {file} with new overlay logic")
        elif 'toggleMobileSidebar' not in content:
            print(f"Skipping {file} (old toggle not found exactly, might need manual replace)")
