with open('database.py', 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace("CURRENT_VERSION = 'v5.7'", "CURRENT_VERSION = 'v5.8'")
with open('database.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated to 5.8")
