import re

# Update database.py to seed session_timeout_minutes
with open('database.py', 'r', encoding='utf-8') as f:
    db_content = f.read()

if "('session_timeout_minutes'" not in db_content:
    db_content = db_content.replace(
        "('portal_version', 'v4.0')",
        "('portal_version', 'v4.0'),\n            ('session_timeout_minutes', '600')"
    )
    with open('database.py', 'w', encoding='utf-8') as f:
        f.write(db_content)
    print("Patched database.py")

# Update app.py to configure the timeout
with open('app.py', 'r', encoding='utf-8') as f:
    app_content = f.read()

if "app.permanent_session_lifetime" not in app_content:
    before_req_str = """
@app.before_request
def make_session_permanent():
    session.permanent = True
    try:
        conn = get_db_connection()
        val = conn.execute('SELECT setting_value FROM portal_settings WHERE setting_key = ?', ('session_timeout_minutes',)).fetchone()
        conn.close()
        timeout = int(val['setting_value']) if val else 600
    except:
        timeout = 600
    app.permanent_session_lifetime = timedelta(minutes=timeout)
"""
    app_content = re.sub(r'(@app\.before_request)', before_req_str + r'\n\1', app_content, count=1)
    
    if 'from datetime import timedelta' not in app_content:
        app_content = app_content.replace('from datetime import datetime', 'from datetime import datetime, timedelta')
    
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(app_content)
    print("Patched app.py")
