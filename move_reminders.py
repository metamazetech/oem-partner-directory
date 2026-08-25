with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

reminders_start = content.find('<aside class="glass-card" id="reminders-panel-tour"')
reminders_end = content.find('</aside>', reminders_start) + len('</aside>')
reminders_html = content[reminders_start:reminders_end]

# Modify the reminders HTML to have margin-bottom
reminders_html = reminders_html.replace('margin-bottom: 0;', 'margin-bottom: 1.5rem;')

new_content = content[:reminders_start] + content[reminders_end:]
search_start = new_content.find('<section class="search-bar-container"')

new_content = new_content[:search_start] + reminders_html + '\n\n' + new_content[search_start:]
new_content = new_content.replace('class="dashboard-layout-grid"', 'class="dashboard-layout-grid layout-single-column"')

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(new_content)
print("Updated dashboard.html")
