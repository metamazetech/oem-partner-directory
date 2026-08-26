import os
import zipfile

output_path = r'C:\Users\Lenovo\.gemini\antigravity\brain\0f9f4218-9183-45ad-b1fe-c3c9aff03e13\oem_portal_v3.3_update.zip'

def build_zip():
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk('.'):
            # Skip unwanted directories
            if any(skip in root for skip in ['venv', '.git', '__pycache__', 'scratch']):
                continue
            
            for file in files:
                if file.endswith('.zip') or file.endswith('.pyc') or file == 'oem_tracker.db':
                    continue
                
                file_path = os.path.join(root, file)
                # Ensure correct arcname relative to the root folder
                arcname = os.path.relpath(file_path, '.')
                zf.write(file_path, arcname)
    print(f"Zip created at {output_path}")

if __name__ == '__main__':
    build_zip()
