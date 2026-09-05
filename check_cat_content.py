with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('class="category-content"')
print(content[idx:idx+1500].encode('ascii', 'ignore').decode('ascii'))
