import os
import re

for root, _, files in os.walk('templates'):
    for f in files:
        if f.endswith('.html'):
            filepath = os.path.join(root, f)
            with open(filepath, 'r', encoding='utf-8') as file:
                content = file.read()
                
            original_content = content
            
            # 1. Change Timesheet Icon
            content = re.sub(r'<span>[^<]+</span>\s*Time Sheet', r'<span>⏱️</span> Time Sheet', content)
            content = re.sub(r'<span>[^<]+</span>\s*Master Timesheets', r'<span>⏱️</span> Master Timesheets', content)
            
            # 2. Add Excel Utility and System Builder under Work Tools
            if 'Work Tools' in content and 'Excel Utility' not in content:
                addition = '''
                        <li class="nav-item {% if request.endpoint == 'excel_tool.excel_view' %}active{% endif %}">
                            <a title="Excel Utility" href="{{ url_for('excel_tool.excel_view') }}">
                                <span>🔓</span> Excel Utility
                            </a>
                        </li>
                        <li class="nav-item {% if request.endpoint == 'system_builder.builder_view' %}active{% endif %}">
                            <a title="System Builder" href="{{ url_for('system_builder.builder_view') }}">
                                <span>🛠️</span> System Builder
                            </a>
                        </li>'''
                content = re.sub(r'(<li class="nav-item \{% if request\.endpoint == \'work_tools\' %\}.*?</li>)', r'\1' + addition, content, flags=re.DOTALL)

            # 3. Remove System Change Logs button from OEM directory in dashboard
            if f == 'dashboard.html':
                content = re.sub(r'<span onclick="openModal\(\'changelogs-modal\'\)".*?</span>', '', content, flags=re.DOTALL)

            if original_content != content:
                with open(filepath, 'w', encoding='utf-8') as file:
                    file.write(content)
                print(f'Updated {f}')
