import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the logo fetcher sources array
old_sources = '''    sources = [
        f"https://logo.clearbit.com/{domain}",
        f"https://www.google.com/s2/favicons?sz=128&domain={domain}",
        f"https://icons.duckduckgo.com/ip3/{domain}.ico"
    ]'''

new_sources = '''    # We will prioritize Google since Clearbit often fails or returns placeholder blocks
    sources = [
        f"https://www.google.com/s2/favicons?sz=128&domain={domain}",
        f"https://logo.clearbit.com/{domain}",
        f"https://icons.duckduckgo.com/ip3/{domain}.ico"
    ]'''

if old_sources in content:
    content = content.replace(old_sources, new_sources)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Task 5 (Logo Fetching) Fixed: Re-ordered sources to prefer Google Favicon API.")
else:
    print("Could not find old_sources to patch in Task 5.")
