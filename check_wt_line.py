with open('templates/work_tools.html', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if '"side class="sidebar"' in line:
            print(f'Line {i+1}: {line.strip()}')
