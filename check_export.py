with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find("@app.route('/export')")
print(content[idx:idx+1500])
