import re

with open('database.py', 'r', encoding='utf-8') as f:
    content = f.read()

migration_code = """
    # Version Auto-Migration Block
    CURRENT_VERSION = 'v5.7'
    try:
        db_ver_row = cursor.execute("SELECT value FROM portal_settings WHERE key = 'portal_version'").fetchone()
        db_ver = db_ver_row['value'] if db_ver_row else 'v4.0'
        
        if db_ver != CURRENT_VERSION:
            # Update the DB version
            cursor.execute("UPDATE portal_settings SET value = ? WHERE key = 'portal_version'", (CURRENT_VERSION,))
            
            # Insert change log for v5.7 if not exists
            check_cl = cursor.execute("SELECT id FROM change_logs WHERE version = ?", (CURRENT_VERSION,)).fetchone()
            if not check_cl:
                import datetime
                cursor.execute('''
                    INSERT INTO change_logs (version, release_date, features, improvements) 
                    VALUES (?, ?, ?, ?)
                ''', (
                    CURRENT_VERSION, 
                    datetime.date.today().strftime('%Y-%m-%d'),
                    'Timesheet & Productivity Tracker, System Builder Engine, Excel Password Remover Utility',
                    'Fixed CSV dual-format parser logic, removed cPanel WAF tarpitting via native forms, enhanced mobile responsive UI routing.'
                ))
    except Exception as e:
        print(f"Migration error: {e}")

    conn.commit()
"""

# Insert right before `conn.commit()`
if "    conn.commit()\n    conn.close()\n    print(\"Database initialized successfully.\")" in content:
    content = content.replace(
        "    conn.commit()\n    conn.close()\n    print(\"Database initialized successfully.\")",
        migration_code + "\n    conn.close()\n    print(\"Database initialized successfully.\")"
    )
    with open('database.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched database.py successfully.")
else:
    print("Could not find the hook location.")
