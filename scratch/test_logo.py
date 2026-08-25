import os
import requests
import urllib.request
from urllib.parse import urlparse

def download_company_logo(website, contact_id, company_name=None):
    domain = None
    if website:
        try:
            url = website.strip().lower()
            if not url.startswith('http://') and not url.startswith('https://'):
                url = 'https://' + url
            parsed = urlparse(url)
            domain = parsed.netloc
            if domain.startswith('www.'):
                domain = domain[4:]
        except Exception:
            pass
            
    if not domain and company_name:
        clean_name = company_name.strip().lower()
        clean_name = "".join(c for c in clean_name if c.isalnum() or c in ['-'])
        for suffix in ['ltd', 'inc', 'corp', 'limited', 'systems', 'india', 'tech', 'technologies', 'group', 'solutions']:
            if clean_name.endswith(suffix):
                clean_name = clean_name[:-len(suffix)].strip('-')
        if clean_name:
            domain = clean_name + ".com"

    if not domain:
        print("No domain found.")
        return None
        
    print(f"Resolving domain: {domain}")
    filename = f"logo_{contact_id}.png"
    filepath = filename
    
    sources = [
        f"https://logo.clearbit.com/{domain}",
        f"https://www.google.com/s2/favicons?sz=128&domain={domain}",
        f"https://icons.duckduckgo.com/ip3/{domain}.ico"
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    for logo_url in sources:
        print(f"Trying source: {logo_url}")
        try:
            response = requests.get(logo_url, headers=headers, timeout=5, verify=False)
            print(f"Response code: {response.status_code}, Length: {len(response.content)}")
            if response.status_code == 200 and len(response.content) > 150:
                with open(filepath, 'wb') as out_file:
                    out_file.write(response.content)
                print(f"Success! Saved to {filepath}")
                return filename
        except Exception as e:
            print(f"Requests failed: {e}")
            
        try:
            req = urllib.request.Request(logo_url, headers=headers)
            with urllib.request.urlopen(req, timeout=4) as urllib_resp:
                content = urllib_resp.read()
                print(f"Urllib response code: {urllib_resp.status}, Length: {len(content)}")
                if urllib_resp.status == 200 and len(content) > 150:
                    with open(filepath, 'wb') as out_file:
                        out_file.write(content)
                    print(f"Urllib success! Saved to {filepath}")
                    return filename
        except Exception as e2:
            print(f"Urllib failed: {e2}")
            
    print("Failed to download from all sources.")
    return None

if __name__ == '__main__':
    download_company_logo("cisco.com", 99, "Cisco Systems")
