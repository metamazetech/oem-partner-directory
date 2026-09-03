import re

with open('static/js/main.js', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("fetch('/api/reminders/panel')", "fetch(getAppUrl('/api/reminders/panel'))")
content = content.replace("fetch('/user/reminders/pending')", "fetch(getAppUrl('/user/reminders/pending'))")
content = content.replace("fetch(`/user/reminders/${reminderId}/complete`", "fetch(getAppUrl(`/user/reminders/${reminderId}/complete`)")

with open('static/js/main.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed fetch paths to use getAppUrl")
