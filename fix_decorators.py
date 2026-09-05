import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove the duplicated decorators
bad_decorators = """@app.route('/admin/auto-update', methods=['POST'])
@admin_required
@app.route('/admin/auto-update', methods=['POST'])
@admin_required"""

good_decorators = """@app.route('/admin/auto-update', methods=['POST'])
@admin_required"""

if bad_decorators in content:
    content = content.replace(bad_decorators, good_decorators)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed duplicate decorators")
else:
    print("Could not find duplicate decorators")
