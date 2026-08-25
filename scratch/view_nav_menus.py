import sys
import glob
import os

sys.stdout.reconfigure(encoding='utf-8')

templates_dir = r"c:\Users\Lenovo\.gemini\antigravity\scratch\sanddy-website\oem_portal\templates"
for filepath in glob.glob(os.path.join(templates_dir, "*.html")):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        for idx, line in enumerate(lines):
            if 'logout' in line:
                print(f"File: {os.path.basename(filepath)}")
                start = max(0, idx - 6)
                end = min(len(lines), idx + 4)
                for i in range(start, end):
                    print(f"  {i+1}: {lines[i].rstrip()}")
                print("-" * 40)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
