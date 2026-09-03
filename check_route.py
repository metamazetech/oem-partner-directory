with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find("@app.route('/api/reminders/panel')")
print(content[idx:idx+800])
