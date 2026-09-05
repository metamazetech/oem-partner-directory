import ast
import re

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# We will use regex to replace the function body of admin_auto_update.
# Actually, since it's a long function, I'll provide the replacement string directly.
old_func_start = "def admin_auto_update():"
old_func_end = "return redirect(url_for('admin_panel'))"

# Using ast to find exact boundaries
tree = ast.parse(code)
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == 'admin_auto_update':
        start_lineno = node.lineno
        end_lineno = node.end_lineno
        break

lines = code.splitlines()
old_func_body = '\n'.join(lines[start_lineno-1:end_lineno])

new_func = """@app.route('/admin/auto-update', methods=['POST'])
@admin_required
def admin_auto_update():
    logs = ["Starting update process..."]
    if 'update_file' not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded."})
        
    file = request.files['update_file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No file selected."})
        
    if not file.filename.endswith('.zip'):
        return jsonify({"status": "error", "message": "Invalid file format. Please upload a .zip codebase archive."})
        
    import zipfile
    import shutil
    import datetime
    import subprocess
    import sys
    
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"pre_update_backup_{timestamp}.zip"
    backup_zip_path = os.path.join(app.config['UPLOAD_FOLDER'], backup_filename)
    
    # 1. Complete Pre-Update Backup
    try:
        logs.append("Initializing pre-update safety backup...")
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        compress_method = zipfile.ZIP_DEFLATED
        with zipfile.ZipFile(backup_zip_path, 'w', compress_method) as zipf:
            db_path = database.DB_PATH
            if os.path.exists(db_path):
                zipf.write(db_path, arcname='oem_tracker.db')
                logs.append("Backed up database.")
            
            upload_folder = app.config['UPLOAD_FOLDER']
            if os.path.exists(upload_folder):
                for root, dirs, files in os.walk(upload_folder):
                    for f in files:
                        if f.startswith('pre_update_backup_') or f in ['.gitkeep', 'temp_restore.zip']:
                            continue
                        filepath = os.path.join(root, f)
                        rel_path = os.path.relpath(filepath, upload_folder)
                        zipf.write(filepath, arcname=os.path.join('uploads', rel_path))
                logs.append("Backed up user uploads.")
                        
            root_dir = os.getcwd()
            for root, dirs, files in os.walk(root_dir):
                if 'venv' in root or '.git' in root or '__pycache__' in root or 'uploads' in root or 'tmp' in root:
                    continue
                for f in files:
                    if f.endswith('.zip') or f.endswith('.pyc') or f.endswith('.log') or f.endswith('.db') or f.endswith('.bak'):
                        continue
                    filepath = os.path.join(root, f)
                    rel_path = os.path.relpath(filepath, root_dir)
                    zipf.write(filepath, arcname=os.path.join('code', rel_path))
            logs.append("Backed up codebase files.")
                    
        log_audit('PORTAL_UPDATE_BACKUP', f"Created automatic pre-update backup: {backup_filename}")
        logs.append(f"Backup created successfully: {backup_filename}")
    except Exception as backup_err:
        return jsonify({"status": "error", "message": f"Failed to create backup: {backup_err}. Aborted."})
        
    # 2. Extract Uploaded Codebase ZIP
    logs.append("Extracting uploaded update archive...")
    temp_zip_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_update.zip')
    try:
        file.save(temp_zip_path)
        
        with zipfile.ZipFile(temp_zip_path, 'r') as zipf:
            namelist = zipf.namelist()
            
            common_prefix = ""
            if namelist:
                first_parts = namelist[0].split('/')
                if len(first_parts) > 1:
                    first = first_parts[0]
                    if all(name.startswith(first + '/') or name == first for name in namelist):
                        common_prefix = first + '/'
            
            extracted_files = 0
            for name in namelist:
                if name == common_prefix or name.endswith('/'):
                    continue
                
                rel_path = name[len(common_prefix):] if common_prefix else name
                
                if 'venv/' in name or '.git/' in name or '__pycache__/' in name or name.endswith('.zip') or name.endswith('.db'):
                    continue
                    
                target_path = os.path.join(app.root_path, rel_path)
                real_target = os.path.realpath(target_path)
                if not real_target.startswith(os.path.realpath(app.root_path)):
                    continue 
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                
                file_data = zipf.read(name)
                with open(target_path, 'wb') as f_out:
                    f_out.write(file_data)
                extracted_files += 1
                
        logs.append(f"Successfully extracted and overwritten {extracted_files} core files.")
                
        # 3. Automatically Install Dependencies
        req_path = os.path.join(app.root_path, 'requirements.txt')
        if os.path.exists(req_path):
            logs.append("Found requirements.txt, checking dependencies...")
            try:
                subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', req_path], check=True)
                logs.append("Python dependencies verified and updated.")
            except Exception as pip_err:
                logs.append(f"Warning: Dependency check returned error: {pip_err}")
                
        # Read current version, increment and update
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
            logs.append(f"Version bumped to {new_ver}.")
        except Exception as e:
            logs.append(f"Notice: Failed to bump version: {e}")
            
        # 4. Trigger WSGI restart for Passenger/cPanel
        try:
            logs.append("Triggering application server reload (WSGI Restart)...")
            tmp_dir = os.path.join(os.getcwd(), 'tmp')
            os.makedirs(tmp_dir, exist_ok=True)
            with open(os.path.join(tmp_dir, 'restart.txt'), 'w') as f_restart:
                f_restart.write(f'restart_{timestamp}')
        except Exception as restart_err:
            logs.append(f"Warning: WSGI Restart trigger error: {restart_err}")
            
        log_audit('PORTAL_UPDATE_APPLIED', f"Application auto-update applied: {extracted_files} files.")
        logs.append("Update complete! The portal will now restart automatically.")
        
        return jsonify({"status": "success", "message": chr(10).join(logs)})
        
    except Exception as update_err:
        return jsonify({"status": "error", "message": f"Update failed: {update_err}"})
    finally:
        if os.path.exists(temp_zip_path):
            try: os.remove(temp_zip_path)
            except: pass
"""

new_code = code.replace(old_func_body, new_func)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(new_code)
    
print("Replaced admin_auto_update")
