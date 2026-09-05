with open('static/js/main.js', 'r', encoding='utf-8') as f:
    content = f.read()

import re
# The ui-dashboard-worker added logic in DOMContentLoaded to fetch /api/reminders/panel
# It looks like: fetch(getAppUrl('/api/reminders/panel')) ... remindersWrapper.innerHTML = html;
# We will just comment out or remove that block.
match = re.search(r'// Fetch the HTML panel.*?fetch\(getAppUrl\(\'/api/reminders/panel\'\)\).*?\}\s*\)\s*\.catch.*?;\s*\}\s*\}\);', content, re.DOTALL)
if match:
    content = content.replace(match.group(0), '')
    
# Let's also remove the remindersWrapper creation logic before it
match2 = re.search(r'// Check if sidebar has nav-menu.*?const navContainer = document.querySelector.*?;.*?const remindersWrapper = document.createElement\(\'div\'\);.*?navContainer\.parentNode\.insertBefore\(remindersWrapper, navContainer\.nextSibling\);', content, re.DOTALL)
if match2:
    content = content.replace(match2.group(0), '')
    
with open('static/js/main.js', 'w', encoding='utf-8') as f:
    f.write(content)
print("Removed sidebar injection from main.js")
