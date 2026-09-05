import re

with open('templates/rfps.html', 'r', encoding='utf-8') as f:
    skeleton = f.read()

with open('templates/reminders_panel.html', 'r', encoding='utf-8') as f:
    panel_html = f.read()

match = re.search(r'(<main class="main-content">).*?(</main>)', skeleton, re.DOTALL)
if match:
    new_main_content = match.group(1) + "\n"
    new_main_content += '''
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
        <div>
            <h1 style="font-size: 1.8rem; font-weight: 700; margin-bottom: 0.25rem;">Reminders & Follow-ups</h1>
            <p style="color: var(--text-secondary); font-size: 0.95rem;">Manage your pending tasks and communications.</p>
        </div>
    </div>
    <div style="background: rgba(30, 41, 59, 0.5); padding: 1.5rem; border-radius: 12px; border: 1px solid var(--border-glass);">
    '''
    new_main_content += panel_html
    new_main_content += "\n</div>\n"
    new_main_content += match.group(2)
    
    new_html = skeleton.replace(match.group(0), new_main_content)
    new_html = new_html.replace('<li class="nav-item active">', '<li class="nav-item">')
    
    with open('templates/reminders.html', 'w', encoding='utf-8') as f:
        f.write(new_html)
    print("Created reminders.html")
else:
    print("Could not match main-content")
