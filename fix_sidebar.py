import os

toggle_button_html = '''
                        <li class="nav-item" style="margin-top: 0.5rem;">
                            <a href="javascript:void(0)" onclick="document.querySelector('.sidebar').style.display='none'; localStorage.setItem('sidebar-collapsed','true');" style="color: #a5b4fc;">
                                <span>&laquo;</span> Hide Sidebar
                            </a>
                        </li>'''

for root, dirs, files in os.walk('templates'):
    for file in files:
        if not file.endswith('.html'):
            continue
        path = os.path.join(root, file)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'Download APK' not in content:
            continue
        
        # Step 1: Remove the existing Download APK block
        old_apk = '''<li class="nav-item">
                            <a href="{{ url_for('download_apk') }}" style="color: #34d399;">
                                <span>\U0001f4f1</span> Download APK
                            </a>
                        </li>
                        <li class="nav-item">
                            <a href="{{ url_for('logout') }}"'''
        
        new_without_apk = '''<li class="nav-item">
                            <a href="{{ url_for('logout') }}"'''
        
        content = content.replace(old_apk, new_without_apk)
        
        # Step 2: Insert Download APK + Toggle right BEFORE Sign Out
        sign_out_block = '''<li class="nav-item">
                            <a href="{{ url_for('logout') }}"'''
        
        apk_and_toggle = '''<li class="nav-item">
                            <a href="{{ url_for('download_apk') }}" style="color: #34d399;">
                                <span>\U0001f4f1</span> Download APK
                            </a>
                        </li>''' + toggle_button_html + '''
                        <li class="nav-item">
                            <a href="{{ url_for('logout') }}"'''
        
        content = content.replace(sign_out_block, apk_and_toggle)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Updated {file}')

print('Done!')
