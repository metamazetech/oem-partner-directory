import re

# Update database.py
with open('database.py', 'r', encoding='utf-8') as f:
    db_content = f.read()

if "'session_timeout_minutes'" not in db_content:
    search_str = 'cursor.execute("INSERT OR IGNORE INTO portal_settings (key, value) VALUES (?, ?)", (\'portal_name\', \'OEM Directory\'))'
    replace_str = search_str + '\n    cursor.execute("INSERT OR IGNORE INTO portal_settings (key, value) VALUES (?, ?)", (\'session_timeout_minutes\', \'600\'))'
    db_content = db_content.replace(search_str, replace_str)
    with open('database.py', 'w', encoding='utf-8') as f:
        f.write(db_content)
    print("Patched database.py")

# Update app.py fixing the SELECT statement
with open('app.py', 'r', encoding='utf-8') as f:
    app_content = f.read()

app_content = app_content.replace("setting_key", "key").replace("setting_value", "value")
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_content)
print("Fixed app.py SQL")
