import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse

def clean_url(url):
    url = url.strip()
    if not url:
        return ""
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url

def scrape_oem_website(url):
    cleaned_url = clean_url(url)
    if not cleaned_url:
        return {"status": "error", "message": "Invalid website URL"}
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }
    
    result = {
        "status": "success",
        "title": "",
        "description": "",
        "products": [],
        "services": [],
        "errors": []
    }
    
    try:
        # Fetch homepage
        response = requests.get(cleaned_url, headers=headers, timeout=6, verify=False)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        # Graceful fallback: return a status indicating scraping failed but UI shouldn't crash
        return {
            "status": "partial",
            "title": urlparse(cleaned_url).netloc,
            "description": "Auto-scraping unavailable. The website might be using anti-bot protection (e.g., Cloudflare) or took too long to respond.",
            "products": ["Hardware Integration (System Integrator Suggestion)", "Cloud Services & Infrastructure", "IT Consultancy & Design"],
            "services": ["Managed IT Services", "SLA & Post-Sales Support", "Security Auditing & Hardening"],
            "errors": [str(e)]
        }
        
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 1. Fetch metadata
    result["title"] = soup.title.string.strip() if soup.title else urlparse(cleaned_url).netloc
    
    meta_desc = soup.find('meta', attrs={'name': re.compile(r'description', re.I)})
    if not meta_desc:
        meta_desc = soup.find('meta', attrs={'property': 'og:description'})
    
    if meta_desc and meta_desc.get('content'):
        result["description"] = meta_desc.get('content').strip()
        
    # 2. Heuristics for finding Products & Services links
    subpage_links = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        text = link.get_text().lower()
        
        # Look for product or service subpages
        if any(keyword in text for keyword in ['product', 'service', 'solution', 'what we do', 'portfolio', 'offering']):
            full_link = urljoin(cleaned_url, href)
            # Ensure it is the same domain
            if urlparse(full_link).netloc == urlparse(cleaned_url).netloc:
                subpage_links.append((full_link, text))
                
    # Deduplicate and limit to top 2 links to parse to avoid performance issues
    seen_links = set()
    unique_subpage_links = []
    for link, name in subpage_links:
        if link not in seen_links and link != cleaned_url:
            seen_links.add(link)
            unique_subpage_links.append((link, name))
            if len(unique_subpage_links) >= 2:
                break
                
    # 3. Extract items from homepage
    homepage_items = extract_items_from_soup(soup)
    result["products"].extend(homepage_items["products"])
    result["services"].extend(homepage_items["services"])
    
    # 4. Extract from top subpages
    for link, name in unique_subpage_links:
        try:
            sub_resp = requests.get(link, headers=headers, timeout=4, verify=False)
            if sub_resp.status_code == 200:
                sub_soup = BeautifulSoup(sub_resp.text, 'html.parser')
                sub_items = extract_items_from_soup(sub_soup)
                
                if 'product' in name:
                    result["products"].extend(sub_items["products"])
                    result["products"].extend(sub_items["services"]) # sometimes mixed
                else:
                    result["services"].extend(sub_items["services"])
                    result["services"].extend(sub_items["products"])
        except Exception:
            pass # ignore subpage download errors to prevent complete failure
            
    # Clean up, deduplicate, and filter lists
    result["products"] = clean_and_deduplicate(result["products"])
    result["services"] = clean_and_deduplicate(result["services"])
    
    # If we found nothing, let's seed some smart default suggestions based on titles/meta
    if not result["products"] and not result["services"]:
        # Seed default list
        text_corpus = (result["title"] + " " + (result["description"] or "")).lower()
        if any(kw in text_corpus for kw in ['network', 'switch', 'router', 'cisco', 'firewall']):
            result["products"] = ["Routing & Switching hardware", "Next-Gen Firewalls", "Wireless Access Points", "SD-WAN Solutions"]
            result["services"] = ["Network Design & Auditing", "Network Management", "Deployment & Integration Services"]
        elif any(kw in text_corpus for kw in ['cloud', 'aws', 'azure', 'server', 'storage', 'data center']):
            result["products"] = ["Hyperconverged Infrastructure", "Network Attached Storage (NAS)", "Enterprise Servers", "Cloud Backup Modules"]
            result["services"] = ["Cloud Migration & Strategy", "Data Center Virtualization", "Backup & Disaster Recovery Managed Services"]
        elif any(kw in text_corpus for kw in ['security', 'antivirus', 'cyber', 'endpoint', 'threat']):
            result["products"] = ["Endpoint Protection Platforms", "SIEM & SOAR software licensing", "Identity & Access Management", "Email Security Gateways"]
            result["services"] = ["Vulnerability Assessment", "Penetration Testing (VAPT)", "24/7 Security Operations Center (SOC) monitoring"]
        else:
            result["products"] = ["Enterprise hardware systems", "Software licenses & subscriptions", "Core networking gear"]
            result["services"] = ["Technical consultation", "Implementation & Setup", "Annual Maintenance Contracts (AMC)"]

    # Limit to top 8 items each to keep UI tidy
    result["products"] = result["products"][:8]
    result["services"] = result["services"][:8]
    
    return result

def extract_items_from_soup(soup):
    products = []
    services = []
    
    # Heuristic A: Look for list items that contain useful product names
    # Or look for headings like Products, Services, Solutions and get their adjacent list items
    for heading in soup.find_all(['h2', 'h3', 'h4']):
        heading_text = heading.get_text().strip().lower()
        is_product_heading = any(k in heading_text for k in ['product', 'hardware', 'appliance', 'device', 'software', 'licensing'])
        is_service_heading = any(k in heading_text for k in ['service', 'solution', 'consult', 'support', 'training', 'professional'])
        
        if is_product_heading or is_service_heading:
            # Look at sibling lists
            sibling = heading.find_next_sibling()
            # If sibling is not list, try to find next element
            limit = 3
            while sibling and limit > 0:
                if sibling.name in ['ul', 'ol']:
                    list_items = [li.get_text().strip() for li in sibling.find_all('li')]
                    if is_product_heading:
                        products.extend(list_items)
                    else:
                        services.extend(list_items)
                    break
                elif sibling.name in ['div']:
                    # Might have sub lists
                    list_items = [li.get_text().strip() for li in sibling.find_all('li')]
                    if list_items:
                        if is_product_heading:
                            products.extend(list_items)
                        else:
                            services.extend(list_items)
                        break
                sibling = sibling.next_sibling
                limit -= 1
                
    # Heuristic B: Look at general cards or grid items that might represent products or services
    # CSS classes commonly used for product items
    for item in soup.find_all(class_=re.compile(r'(product|service|solution)-card|item|box', re.I)):
        text = item.get_text().strip()
        if 0 < len(text) < 100:  # avoid large text blocks
            # Clean text (remove extra whitespaces/newlines)
            clean_text = " ".join(text.split())
            if any(k in clean_text.lower() for k in ['service', 'consult', 'support', 'management']):
                services.append(clean_text)
            else:
                products.append(clean_text)
                
    return {"products": products, "services": services}

def clean_and_deduplicate(items_list):
    cleaned = []
    seen = set()
    for item in items_list:
        # Clean item
        item = re.sub(r'\s+', ' ', item).strip()
        # Filter out item text that is too long, too short, or looks like navigation labels
        if not item or len(item) < 3 or len(item) > 80:
            continue
        if any(nav in item.lower() for nav in ['view more', 'learn more', 'read more', 'contact us', 'get started', 'sign up', 'see details', 'home', 'about', 'careers', 'blog', 'privacy policy']):
            continue
        
        item_lower = item.lower()
        if item_lower not in seen:
            seen.add(item_lower)
            cleaned.append(item)
            
    return cleaned

# Turn off SSL warnings since we are ignoring verify=False
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
