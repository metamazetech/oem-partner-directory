import os
import zipfile

source_dir = r"c:\Users\Lenovo\.gemini\antigravity\scratch\sanddy-website\oem_portal"
output_zip = r"C:\Users\Lenovo\.gemini\antigravity\brain\0f9f4218-9183-45ad-b1fe-c3c9aff03e13\oem_portal_v5.8_cpanel_deploy.zip"

def should_exclude(dir_name):
    return dir_name in ['venv', '__pycache__', '.git', '.pytest_cache', 'uploads'] or dir_name.endswith('.egg-info')

def should_exclude_file(file_name):
    return file_name in ['oem_tracker.db', '.env'] or file_name.endswith('.pyc') or file_name.endswith('.zip') or file_name.endswith('.log')

print(f"Building deployment ZIP: {output_zip}")
with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(source_dir):
        dirs[:] = [d for d in dirs if not should_exclude(d)]
        for file in files:
            if should_exclude_file(file):
                continue
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, source_dir)
            zipf.write(file_path, arcname)

print("Deployment ZIP successfully created!")
