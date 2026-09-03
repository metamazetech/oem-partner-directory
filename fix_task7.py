import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_secret_logic = """
# Persistent Secret Key Logic
SECRET_KEY_FILE = '.secret_key'
if os.path.exists(SECRET_KEY_FILE):
    with open(SECRET_KEY_FILE, 'r') as f:
        app.secret_key = f.read().strip()
else:
    app.secret_key = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))
    with open(SECRET_KEY_FILE, 'w') as f:
        f.write(app.secret_key)
"""

old_secret_logic = "app.secret_key = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))"

content = content.replace(old_secret_logic, new_secret_logic.strip())

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Task 7 (Session Logout Bug) Fixed: Secret key is now persistent.")
