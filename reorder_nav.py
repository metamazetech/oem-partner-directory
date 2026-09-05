import os
import re

for filename in os.listdir('templates'):
    if filename.endswith('.html'):
        filepath = os.path.join('templates', filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find the <ul class="nav-menu">
        match = re.search(r'(<ul class="nav-menu">.*?)(</ul>)', content, re.DOTALL)
        if match:
            ul_content = match.group(1)
            
            # Find the Reminders li
            reminders_match = re.search(r'<li[^>]*>\s*<a[^>]*href="[^"]*reminders[^"]*"[^>]*>.*?</li>', ul_content, re.DOTALL)
            # Find the Sign Out li
            signout_match = re.search(r'<li[^>]*>\s*<a[^>]*href="[^"]*logout[^"]*"[^>]*>.*?</li>', ul_content, re.DOTALL)
            
            if reminders_match and signout_match:
                # Remove them from ul_content
                ul_content = ul_content.replace(reminders_match.group(0), '')
                ul_content = ul_content.replace(signout_match.group(0), '')
                
                # Append them in correct order
                ul_content += reminders_match.group(0) + '\n' + signout_match.group(0) + '\n'
                
                content = content.replace(match.group(1), ul_content)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Reordered nav in {filename}")
