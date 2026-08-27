import os

for root, dirs, files in os.walk('templates'):
    for file in files:
        if not file.endswith('.html'):
            continue
        path = os.path.join(root, file)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'Download APK' not in content:
            continue
        
        # Replace Download APK link with Install App link
        content = content.replace(
            '''<li class="nav-item">
                            <a href="{{ url_for('download_apk') }}" style="color: #34d399;">
                                <span>\U0001f4f1</span> Download APK
                            </a>
                        </li>''',
            '''<li class="nav-item" id="install-app-item">
                            <a href="javascript:void(0)" onclick="installApp()" style="color: #34d399;">
                                <span>\U0001f4f1</span> Install App
                            </a>
                        </li>'''
        )
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Updated {file}')

print('Done!')
