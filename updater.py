import os
import re

portal_dir = r"c:\Users\Lenovo\.gemini\antigravity\scratch\sanddy-website\oem_portal"

# 1. Update templates
templates_dir = os.path.join(portal_dir, "templates")
for root, dirs, files in os.walk(templates_dir):
    for f in files:
        if f.endswith(".html"):
            path = os.path.join(root, f)
            with open(path, "r", encoding="utf-8") as file:
                content = file.read()
            
            content = content.replace("v3.1", "{{ portal_settings.get('portal_version', 'v4.0') }}")
            content = content.replace("?v=3.5", "?v={{ portal_settings.get('portal_version', '4.0') }}")
            
            with open(path, "w", encoding="utf-8") as file:
                file.write(content)

# 2. database.py changes
db_path = os.path.join(portal_dir, "database.py")
if os.path.exists(db_path):
    with open(db_path, "r", encoding="utf-8") as f:
        db_content = f.read()
    
    # insert portal_version into portal_settings
    if "'portal_version'" not in db_content:
        # Assuming there's a place where portal_settings are inserted
        db_content = re.sub(r"(INSERT OR IGNORE INTO portal_settings\s*\(setting_key,\s*setting_value\)\s*VALUES\s*)((?:\([^)]+\)[,\s]*)+)", 
                            lambda m: m.group(1) + m.group(2).rstrip().rstrip(";") + ",\n            ('portal_version', 'v4.0');", db_content)
        
        with open(db_path, "w", encoding="utf-8") as f:
            f.write(db_content)

print("Templates and database.py logic done.")
