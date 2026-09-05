import re
with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

match = re.search(r'<form.*?action=.*?search.*?>.*?</form>', content, re.IGNORECASE | re.DOTALL)
if match:
    text = match.group(0)
    print(text.encode('ascii', 'ignore').decode('ascii'))
