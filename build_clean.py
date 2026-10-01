import os
import zipfile

source_dir = r"c:\Users\Lenovo\.gemini\antigravity\scratch\sanddy-website\oem_portal"
output_zip = r"C:\Users\Lenovo\.gemini\antigravity\brain\0f9f4218-9183-45ad-b1fe-c3c9aff03e13\oem_portal_v5.8_clean_install.zip"

def should_exclude(dir_name):
    return dir_name in ['venv', '__pycache__', '.git', '.pytest_cache', 'tmp'] or dir_name.endswith('.egg-info')

def should_exclude_file(file_name):
    # Exclude the local dirty DB, but we will inject the clean one manually
    return file_name in ['oem_tracker.db', 'clean_oem_tracker.db', '.env', 'update_58.py', 'indent_sidebar.py', 'remove_sidebar_items.py', 'patch_admin.py', 'patch_auto_update.py', 'patch_dashboard_stats.py', 'patch_enabled_tools.py', 'patch_logo.py', 'patch_scraper.py', 'patch_version.py'] or file_name.endswith('.pyc') or file_name.endswith('.zip') or file_name.endswith('.log')

print(f"Building CLEAN INSTALL ZIP: {output_zip}")
with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(source_dir):
        # Prevent traversing into excluded directories
        dirs[:] = [d for d in dirs if not should_exclude(d)]
        
        # Add the uploads folder itself (even if empty, though we'll add .gitkeep)
        if 'uploads' in dirs:
            zipf.write(os.path.join(root, 'uploads'), arcname=os.path.relpath(os.path.join(root, 'uploads'), source_dir))

        for file in files:
            # Skip files inside uploads except .gitkeep
            if 'uploads' in root and file != '.gitkeep':
                continue
                
            if should_exclude_file(file):
                continue
            
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, source_dir)
            zipf.write(file_path, arcname)
            
    # Inject the clean database as oem_tracker.db
    if os.path.exists('clean_oem_tracker.db'):
        zipf.write('clean_oem_tracker.db', arcname='oem_tracker.db')
        
    # Ensure uploads/.gitkeep exists in the zip
    zipf.writestr('uploads/.gitkeep', '')
    zipf.writestr('tmp/restart.txt', 'restart_clean_install')

print("Clean Install ZIP successfully created!")
