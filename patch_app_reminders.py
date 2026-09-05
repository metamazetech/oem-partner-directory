import os

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the api/reminders/panel route
old_route = """@app.route('/api/reminders/panel')
@login_required
def reminders_panel():"""

new_route = """@app.route('/reminders')
@login_required
def reminders():"""

# and the return statement
old_return = """return render_template('reminders_panel.html', reminders=all_reminders)"""
new_return = """return render_template('reminders.html', reminders=all_reminders, portal_settings=get_portal_settings())"""

if old_route in content:
    content = content.replace(old_route, new_route)
    content = content.replace(old_return, new_return)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("app.py updated for /reminders route")
else:
    print("Could not find old route in app.py")
