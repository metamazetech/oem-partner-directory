import os
import re

nav_link = '''
                        <li class="nav-item">
                            <a title="Reminders" href="{{ url_for('reminders') }}">
                                <span>⏰</span> Reminders
                            </a>
                        </li>
'''

for filename in os.listdir('templates'):
    if filename.endswith('.html'):
        filepath = os.path.join('templates', filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if '<span>⏰</span> Reminders' not in content:
            # We want to inject it before </ul> in the nav menu
            # Specifically before the closing </ul> of <ul class="nav-menu">
            match = re.search(r'<ul class="nav-menu">.*?(</ul>)', content, re.DOTALL)
            if match:
                # Find the position of the last </ul> in this match
                ul_end = match.end(1) - 5
                new_content = content[:ul_end] + nav_link + content[ul_end:]
                
                # Make the link active if it is reminders.html
                if filename == 'reminders.html':
                    new_content = new_content.replace('<li class="nav-item">\n                            <a title="Reminders"', '<li class="nav-item active">\n                            <a title="Reminders"')
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Added link to {filename}")
