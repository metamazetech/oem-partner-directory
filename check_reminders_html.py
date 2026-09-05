import re
with open('templates/reminders.html', 'r', encoding='utf-8') as f:
    content = f.read()
match = re.search(r'<main class="main-content">.*?</main>', content, re.DOTALL)
if match:
    print(match.group(0).encode('ascii', 'ignore').decode('ascii'))
