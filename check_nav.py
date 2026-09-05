import re
with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()
match = re.search(r'<ul class="nav-menu">.*?</nav>', content, re.DOTALL)
if match:
    for item in re.finditer(r'<a[^>]*>(.*?)</a>', match.group(0), re.DOTALL):
        text = item.group(1).strip().replace('\n', ' ')
        # clean up multiple spaces
        text = re.sub(r'\s+', ' ', text)
        print(text.encode('ascii', 'ignore').decode('ascii'))
