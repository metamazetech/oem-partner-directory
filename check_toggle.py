with open('static/js/main.js', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find("function toggleCategoryAccordion")
if idx != -1:
    print(content[idx:idx+800])
