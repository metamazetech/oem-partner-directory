with open('templates/work_tools.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix sidebar alignment in work_tools.html
content = content.replace(
'''        <aside class="sidebar">
            <div class="sidebar-header">''',
'''        <aside class="sidebar">
            <div style="display: flex; flex-direction: column; flex-grow: 1;">
            <div class="sidebar-header">'''
)
content = content.replace(
'''                </nav>
            </div>
            
            <div class="sidebar-user-profile"''',
'''                </nav>
            </div>
            </div>
            
            <div class="sidebar-user-profile"'''
)

# Fix Task 3: include main.js
if 'js/main.js' not in content:
    content = content.replace('</body>', '<script src="{{ url_for(\'static\', filename=\'js/main.js\') }}?v=1.6"></script>\n</body>')

with open('templates/work_tools.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated work_tools.html")
