import os

html_to_replace = '''action="{{ url_for('universal_search') }}"'''
replacement = '''action="javascript:void(0);" onsubmit="window.location.href = getAppUrl('/search?q=' + encodeURIComponent(this.q.value));"'''

for filename in os.listdir('templates'):
    if filename.endswith('.html'):
        filepath = os.path.join('templates', filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if html_to_replace in content:
            content = content.replace(html_to_replace, replacement)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Patched search form in {filename}")
