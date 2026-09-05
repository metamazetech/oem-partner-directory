import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the return statement in reminders()
old_ret = "return render_template('reminders_panel.html', reminders=reminders, rfp_reminders=rfp_reminders, today_str=today_str)"
new_ret = "return render_template('reminders.html', reminders=reminders, rfp_reminders=rfp_reminders, today_str=today_str, portal_settings=get_portal_settings())"

if old_ret in content:
    content = content.replace(old_ret, new_ret)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed return statement in /reminders")
else:
    print("Could not find old return statement")
