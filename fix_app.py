with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    "return send_file(apk_path, as_attachment=True, download_name='OEM_Portal_v3.1.apk')",
    "from flask import send_file\n    return send_file(apk_path, as_attachment=True, download_name='OEM_Portal_v3.1.apk')"
)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed send_file in app.py")
