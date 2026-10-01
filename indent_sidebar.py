import os
import re

for root, _, files in os.walk('templates'):
    for f in files:
        if f.endswith('.html'):
            filepath = os.path.join(root, f)
            with open(filepath, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Find the injected list items and add indentation
            old_excel = '<li class="nav-item {% if request.endpoint == \'excel_tool.index\' %}active{% endif %}">'
            new_excel = '<li class="nav-item {% if request.endpoint == \'excel_tool.index\' %}active{% endif %}" style="padding-left: 1.25rem; font-size: 0.9em; opacity: 0.9; border-left: 2px solid rgba(255,255,255,0.1); margin-left: 1rem;">'
            
            old_builder = '<li class="nav-item {% if request.endpoint == \'system_builder.index\' %}active{% endif %}">'
            new_builder = '<li class="nav-item {% if request.endpoint == \'system_builder.index\' %}active{% endif %}" style="padding-left: 1.25rem; font-size: 0.9em; opacity: 0.9; border-left: 2px solid rgba(255,255,255,0.1); margin-left: 1rem;">'
            
            content = content.replace(old_excel, new_excel)
            content = content.replace(old_builder, new_builder)
            
            with open(filepath, 'w', encoding='utf-8') as file:
                file.write(content)
print("Indented sub-items.")
