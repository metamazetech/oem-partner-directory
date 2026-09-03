import re
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_func = """@app.before_request
def make_session_permanent():
    from datetime import timedelta
    session.permanent = True
    session.modified = True
    try:
        conn = get_db_connection()
        val = conn.execute("SELECT value FROM portal_settings WHERE key = 'session_timeout_minutes'").fetchone()
        conn.close()
        timeout = int(val['value']) if (val and val['value']) else 600
    except:
        timeout = 600
    app.permanent_session_lifetime = timedelta(minutes=timeout)"""

content = re.sub(r'@app\.before_request.*?def make_session_permanent\(\):.*?app\.permanent_session_lifetime = timedelta\(minutes=timeout\)', new_func, content, flags=re.DOTALL)

if 'SESSION_REFRESH_EACH_REQUEST' not in content:
    content = content.replace("app.config['SECRET_KEY']", "app.config['SESSION_REFRESH_EACH_REQUEST'] = True\napp.config['SECRET_KEY']")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('app.py patched')
