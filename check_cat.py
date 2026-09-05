import re
with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()
match = re.search(r'<div class="category-group".*?(?=</main>)', content, re.DOTALL)
if match:
    print(match.group(0).encode('ascii', 'ignore').decode('ascii')[:1500])
