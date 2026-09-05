with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find("def admin_auto_update():")
print(content[idx+2000:idx+4000])
