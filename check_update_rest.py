with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()
idx = content.find("@app.route('/admin/auto-update'")
print(content[idx+1400:idx+3500])
