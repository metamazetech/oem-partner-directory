import os
import re
import traceback

portal_dir = r"c:\Users\Lenovo\.gemini\antigravity\scratch\sanddy-website\oem_portal"

def update_templates():
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
    print("Updated templates.")

def update_database_py():
    db_path = os.path.join(portal_dir, "database.py")
    with open(db_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    if "'portal_version'" not in content:
        # Find where 'forgot_password_enabled' is inserted
        target = "cursor.execute(\"INSERT OR IGNORE INTO portal_settings (key, value) VALUES (?, ?)\", ('forgot_password_enabled', 'true'))"
        replacement = target + "\n    cursor.execute(\"INSERT OR IGNORE INTO portal_settings (key, value) VALUES (?, ?)\", ('portal_version', 'v4.0'))"
        content = content.replace(target, replacement)
        
        with open(db_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Updated database.py")

def update_app_py():
    app_path = os.path.join(portal_dir, "app.py")
    with open(app_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Task 1: Auto-versioning
    auto_update_target = """        # 4. Trigger WSGI restart for Passenger/cPanel"""
    auto_update_replacement = """        # Read current version, increment and update
        try:
            conn = database.get_db_connection()
            ver_row = conn.execute("SELECT value FROM portal_settings WHERE key = 'portal_version'").fetchone()
            current_ver = ver_row['value'] if ver_row else 'v4.0'
            import re
            m = re.match(r'v(\d+)\.(\d+)', current_ver)
            if m:
                major, minor = int(m.group(1)), int(m.group(2))
                new_ver = f"v{major}.{minor + 1}"
            else:
                new_ver = 'v4.1'
            conn.execute("UPDATE portal_settings SET value = ? WHERE key = 'portal_version'", (new_ver,))
            import datetime
            conn.execute("INSERT INTO change_logs (version, release_date, features, improvements) VALUES (?, ?, ?, ?)",
                         (new_ver, datetime.date.today().strftime('%Y-%m-%d'), 'Auto-update applied', 'Minor patch update from codebase push'))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Failed to bump version: {e}")
            
        # 4. Trigger WSGI restart for Passenger/cPanel"""
    if "increment and update" not in content:
        content = content.replace(auto_update_target, auto_update_replacement)

    # Task 2.1 & 2.2 & 2.5: secret key, session cookie secure, csrf setup
    secret_target = "app.secret_key = 'presales_oem_distributor_tracker_secret_key_1928'"
    secret_replacement = """import secrets\napp.secret_key = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))"""
    if "secrets.token_hex(32)" not in content:
        content = content.replace(secret_target, secret_replacement)

    cookie_secure_target = "app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'"
    cookie_secure_replacement = """app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'\nif not app.debug:\n    app.config['SESSION_COOKIE_SECURE'] = True"""
    if "SESSION_COOKIE_SECURE" not in content:
        content = content.replace(cookie_secure_target, cookie_secure_replacement)
        
    before_request_csrf_target = """@app.before_request\ndef check_rfp_access_lock():"""
    before_request_csrf_replacement = """@app.before_request\ndef csrf_protect():\n    if 'csrf_token' not in session:\n        import secrets\n        session['csrf_token'] = secrets.token_hex(16)\n\n@app.before_request\ndef check_rfp_access_lock():"""
    if "csrf_protect" not in content:
        content = content.replace(before_request_csrf_target, before_request_csrf_replacement)

    context_target = "settings.setdefault('favicon', '')"
    context_replacement = """settings.setdefault('favicon', '')\n    settings['csrf_token'] = session.get('csrf_token', '')"""
    if "settings['csrf_token']" not in content:
        content = content.replace(context_target, context_replacement)

    # Task 2.3 & 2.4: zip-slip
    auto_update_zip_slip_target = """                target_path = os.path.join(app.root_path, rel_path)\n                os.makedirs(os.path.dirname(target_path), exist_ok=True)"""
    auto_update_zip_slip_replacement = """                target_path = os.path.join(app.root_path, rel_path)\n                real_target = os.path.realpath(target_path)\n                if not real_target.startswith(os.path.realpath(app.root_path)):\n                    continue  # skip files trying to escape app directory\n                os.makedirs(os.path.dirname(target_path), exist_ok=True)"""
    if "skip files trying to escape" not in content:
        content = content.replace(auto_update_zip_slip_target, auto_update_zip_slip_replacement)
        
    restore_zip_slip_target = """                    target_path = os.path.join(app.config['UPLOAD_FOLDER'], rel_path)\n                    os.makedirs(os.path.dirname(target_path), exist_ok=True)"""
    restore_zip_slip_replacement = """                    target_path = os.path.join(app.config['UPLOAD_FOLDER'], rel_path)\n                    real_target = os.path.realpath(target_path)\n                    if not real_target.startswith(os.path.realpath(app.root_path)):\n                        continue  # skip files trying to escape app directory\n                    os.makedirs(os.path.dirname(target_path), exist_ok=True)"""
    if "skip files trying to escape" not in content:
        content = content.replace(restore_zip_slip_target, restore_zip_slip_replacement)

    # Task 2.6: Login rate limiting
    login_rate_target = """@app.route('/login', methods=['GET', 'POST'])\ndef login():"""
    login_rate_replacement = """import time\nlogin_attempts = {}\n\n@app.route('/login', methods=['GET', 'POST'])\ndef login():"""
    if "login_attempts = {}" not in content:
        content = content.replace(login_rate_target, login_rate_replacement)
        
    login_rate_target2 = """    if request.method == 'POST':\n        username = request.form['username'].strip()"""
    login_rate_replacement2 = """    if request.method == 'POST':\n        ip = request.remote_addr\n        now = time.time()\n        if ip in login_attempts:\n            login_attempts[ip] = [t for t in login_attempts[ip] if now - t < 60]\n            if len(login_attempts[ip]) >= 5:\n                flash('Too many login attempts. Please try again later.', 'error')\n                return render_template('login.html')\n        login_attempts.setdefault(ip, []).append(now)\n\n        username = request.form['username'].strip()"""
    if "login_attempts[ip]" not in content:
        content = content.replace(login_rate_target2, login_rate_replacement2)

    # Task 2.7: CSP Header
    csp_target = "response.headers['Content-Security-Policy'] = \"default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self';\""
    csp_replacement = "response.headers['Content-Security-Policy'] = \"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self';\""
    if csp_target in content:
        content = content.replace(csp_target, csp_replacement)

    # Task 3: OEM News Date Ordering
    content = re.sub(r"SELECT \* FROM oem_news ORDER BY id DESC", "SELECT * FROM oem_news ORDER BY pub_date DESC", content)
    
    news_insert_target = """                    conn.execute('''\n                    INSERT OR IGNORE INTO oem_news (oem_name, title, link, pub_date, source, snippet)\n                    VALUES (?, ?, ?, ?, ?, ?)\n                    ''', (oem, item['title'], item['link'], item.get('pubDate', ''), source, item.get('snippet', '')))"""
    news_insert_replacement = """                    import email.utils\n                    import datetime\n                    pub_date_str = item.get('pubDate', '')\n                    if pub_date_str:\n                        try:\n                            dt = email.utils.parsedate_to_datetime(pub_date_str)\n                            pub_date_str = dt.isoformat()\n                        except Exception:\n                            pass\n                    conn.execute('''\n                    INSERT OR IGNORE INTO oem_news (oem_name, title, link, pub_date, source, snippet)\n                    VALUES (?, ?, ?, ?, ?, ?)\n                    ''', (oem, item['title'], item['link'], pub_date_str, source, item.get('snippet', '')))"""
    if "email.utils.parsedate_to_datetime" not in content:
        content = content.replace(news_insert_target, news_insert_replacement)

    # Task 4: Improve OEM Logo Resolution
    logo_size_target = "if response.status_code == 200 and len(response.content) > 150:"
    logo_size_replacement = "if response.status_code == 200 and len(response.content) > 500:"
    content = content.replace(logo_size_target, logo_size_replacement)
    
    logo_size_target2 = "if urllib_resp.status == 200 and len(content) > 150:"
    logo_size_replacement2 = "if urllib_resp.status == 200 and len(content) > 500:"
    content = content.replace(logo_size_target2, logo_size_replacement2)
    
    with open(app_path, "w", encoding="utf-8") as f:
        f.write(content)
        
try:
    update_templates()
    update_database_py()
    update_app_py()
except Exception as e:
    traceback.print_exc()
