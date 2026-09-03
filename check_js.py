with open('static/js/main.js', 'r', encoding='utf-8') as f:
    content = f.read()

for line in content.splitlines():
    if 'fetch' in line and 'reminders' in line:
        print(line.strip())
