with open('templates/work_tools.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = '<button id="mobile-nav-toggle" class="mobile-toggle-btn">\u2630</button>'
new = '''<button id="sidebar-collapse-btn" onclick="this.closest('.sidebar').style.display='none';document.getElementById('show-sidebar-btn').style.display='flex';localStorage.setItem('sidebar-collapsed','true');" style="background:none;border:none;color:var(--text-secondary);cursor:pointer;font-size:1.1rem;padding:4px 8px;border-radius:6px;transition:all 0.2s;" title="Hide Sidebar">&laquo;</button>
                <button id="mobile-nav-toggle" class="mobile-toggle-btn">\u2630</button>'''

content = content.replace(old, new)

with open('templates/work_tools.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated work_tools.html')
