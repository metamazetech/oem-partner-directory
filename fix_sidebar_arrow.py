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
        
        # Remove the Hide Sidebar nav item completely
        content = content.replace(
            '''
                        <li class="nav-item" style="margin-top: 0.5rem;">
                            <a href="javascript:void(0)" onclick="hideSidebar();" style="color: #a5b4fc;">
                                <span>&laquo;</span> Hide Sidebar
                            </a>
                        </li>''',
            ''
        )
        
        # Add a collapse arrow button inside the sidebar-header div
        # Find the mobile-toggle-btn and add our collapse button next to it
        old_mobile = '<button id="mobile-nav-toggle" class="mobile-toggle-btn">\u2630</button>'
        new_mobile = '''<button id="sidebar-collapse-btn" onclick="this.closest('.sidebar').style.display='none';document.getElementById('show-sidebar-btn').style.display='flex';localStorage.setItem('sidebar-collapsed','true');" style="background:none;border:none;color:var(--text-secondary);cursor:pointer;font-size:1.1rem;padding:4px 8px;border-radius:6px;transition:all 0.2s;" title="Hide Sidebar">&laquo;</button>
                <button id="mobile-nav-toggle" class="mobile-toggle-btn">\u2630</button>'''
        
        content = content.replace(old_mobile, new_mobile)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Updated {file}')

print('Done!')
