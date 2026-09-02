import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Update route handling
idx = content.find("request.form.get('portal_name')")
if idx > 0 and 'session_timeout_minutes' not in content[idx-50:idx+500]:
    # We need to extract session_timeout_minutes
    # find where portal_name is retrieved
    insert_str = "        session_timeout_minutes = request.form.get('session_timeout_minutes')\n"
    content = content[:idx] + insert_str + content[idx:]
    
    # find where it's updated in db
    idx2 = content.find("('portal_name', portal_name)")
    if idx2 > 0:
        insert_str2 = "\n        cur.execute('UPDATE portal_settings SET value = ? WHERE key = ?', (session_timeout_minutes, 'session_timeout_minutes'))"
        # find end of line
        end_idx2 = content.find('\n', idx2)
        content = content[:end_idx2] + insert_str2 + content[end_idx2:]
        with open('app.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Patched app.py update route")
