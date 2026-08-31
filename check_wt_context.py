with open('templates/work_tools.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('{% endif %}"side class="sidebar">')
if idx != -1:
    print(content[idx-200:idx+50])
