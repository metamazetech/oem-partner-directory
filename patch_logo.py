with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re
old_sources = """    sources = [
        f"https://www.google.com/s2/favicons?sz=128&domain={domain}",
        f"https://logo.clearbit.com/{domain}",
        f"https://icons.duckduckgo.com/ip3/{domain}.ico"
    ]"""

new_sources = """    sources = [
        f"https://logo.clearbit.com/{domain}",
        f"https://icons.duckduckgo.com/ip3/{domain}.ico",
        f"https://www.google.com/s2/favicons?sz=128&domain={domain}"
    ]"""

content = content.replace(old_sources, new_sources)

old_loop = """    for logo_url in sources:
        try:
            response = requests.get(logo_url, headers=headers, timeout=5, verify=False)
            if response.status_code == 200 and len(response.content) > 500:
                with open(filepath, 'wb') as out_file:
                    out_file.write(response.content)
                return filename"""

new_loop = """    for logo_url in sources:
        try:
            response = requests.get(logo_url, headers=headers, timeout=5, verify=False)
            content_length = len(response.content)
            # Skip Google's default 726-byte globe icon
            is_google_globe = 'google.com' in logo_url and content_length == 726
            if response.status_code == 200 and content_length > 150 and not is_google_globe:
                with open(filepath, 'wb') as out_file:
                    out_file.write(response.content)
                return filename"""

content = content.replace(old_loop, new_loop)

# Also fix the urllib fallback loop
old_urllib = """        try:
            import ssl
            context = ssl._create_unverified_context()
            req = urllib.request.Request(logo_url, headers=headers)
            with urllib.request.urlopen(req, timeout=4, context=context) as urllib_resp:
                content = urllib_resp.read()
                if urllib_resp.status == 200 and len(content) > 500:
                    with open(filepath, 'wb') as out_file:
                        out_file.write(content)
                    return filename"""

new_urllib = """        try:
            import ssl
            context = ssl._create_unverified_context()
            req = urllib.request.Request(logo_url, headers=headers)
            with urllib.request.urlopen(req, timeout=4, context=context) as urllib_resp:
                urllib_content = urllib_resp.read()
                c_len = len(urllib_content)
                is_google_globe = 'google.com' in logo_url and c_len == 726
                if urllib_resp.status == 200 and c_len > 150 and not is_google_globe:
                    with open(filepath, 'wb') as out_file:
                        out_file.write(urllib_content)
                    return filename"""
content = content.replace(old_urllib, new_urllib)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Patched logo logic.')
