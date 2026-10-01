with open('README.md', 'r', encoding='utf-8') as f:
    content = f.read()

old_text = '3. Resolves and upgrades any new dependencies in `requirements.txt` via `pip`.'
new_text = '3. Resolves and upgrades any new dependencies in `requirements.txt` via `pip`.\n  4. Natively bypasses aggressive cPanel ModSecurity WAF rules (which typically block AJAX/XHR payloads) ensuring smooth large-file uploads.'

if old_text in content:
    content = content.replace(old_text, new_text)
    content = content.replace('4. Touches `tmp/restart.txt`', '5. Touches `tmp/restart.txt`')
    
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(content)
    print('README updated.')
