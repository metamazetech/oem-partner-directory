with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Patch success return
old_success = 'return jsonify({"status": "success", "message": chr(10).join(logs)})'
new_success = '''flash("Update complete!", "success")
        return redirect(url_for('admin_panel'))'''
content = content.replace(old_success, new_success)

# Patch error returns
old_err1 = 'return jsonify({"status": "error", "message": "No file uploaded."})'
new_err1 = '''flash("No file uploaded.", "error")
        return redirect(url_for('admin_panel'))'''
content = content.replace(old_err1, new_err1)

old_err2 = 'return jsonify({"status": "error", "message": "No file selected."})'
new_err2 = '''flash("No file selected.", "error")
        return redirect(url_for('admin_panel'))'''
content = content.replace(old_err2, new_err2)

old_err3 = 'return jsonify({"status": "error", "message": "Invalid file format. Please upload a .zip codebase archive."})'
new_err3 = '''flash("Invalid file format. Please upload a .zip codebase archive.", "error")
        return redirect(url_for('admin_panel'))'''
content = content.replace(old_err3, new_err3)

old_err4 = 'return jsonify({"status": "error", "message": f"Failed to create backup: {backup_err}. Aborted."})'
new_err4 = '''flash(f"Failed to create backup: {backup_err}. Aborted.", "error")
        return redirect(url_for('admin_panel'))'''
content = content.replace(old_err4, new_err4)

old_err5 = 'return jsonify({"status": "error", "message": f"Update failed: {update_err}"})'
new_err5 = '''flash(f"Update failed: {update_err}", "error")
        return redirect(url_for('admin_panel'))'''
content = content.replace(old_err5, new_err5)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Patched app.py for native auto update.')
