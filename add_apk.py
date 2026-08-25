import os

apk_item = '''<li class="nav-item">
                            <a href="{{ url_for('download_apk') }}" style="color: #34d399;">
                                <span>📱</span> Download APK
                            </a>
                        </li>'''

for root, _, files in os.walk('templates'):
    for file in files:
        if file.endswith('.html'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            if 'Sign Out' in content and 'Download APK' not in content:
                new_content = content.replace(
                    '''<li class="nav-item">
                            <a href="{{ url_for('logout') }}"''',
                    apk_item + '''\n                        <li class="nav-item">
                            <a href="{{ url_for('logout') }}"'''
                )
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f'Updated {path}')
