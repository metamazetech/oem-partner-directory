import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
import urllib3

# Turn off SSL warnings since we are ignoring verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def clean_url(url):
    url = url.strip()
    if not url:
        return ""
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url

def generate_oem_portfolio_summary(company_name, url=None, products=None, services=None, group_name=None, meta_description=None):
    """
    Generates a dense, pre-sales actionable 10-15 line catalog overview paragraph
    detailing the OEM's practical hardware products, appliances, software licensing tiers,
    workload specifications, professional engineering services, and mission-critical SLAs.
    """
    if isinstance(url, list) and products is None:
        products = url
        url = None
    clean_name = (company_name or "The enterprise vendor").strip()
    p = products or []
    s = services or []
    scope_target = group_name if group_name else "enterprise IT infrastructure, cloud platforms, and mission-critical networks"
    
    sentences = []
    
    # 1. Product & Platform Scope
    if p:
        sentences.append(f"{clean_name} delivers an enterprise-grade hardware, appliance, and software portfolio specifically engineered for {scope_target}.")
        sentences.append(f"At the core of their hardware and platform catalog are flagship solutions including {', '.join(p[:3])}, engineered for high-density performance, low latency, and mission-critical reliability.")
        if len(p) > 3:
            sentences.append(f"Their broader hardware and appliance lineup features {', '.join(p[3:6])}, offering modular chassis expansion and flexible deployment form factors.")
    else:
        sentences.append(f"{clean_name} maintains a comprehensive catalog of enterprise hardware systems, modular appliances, and licensed software packages.")
        sentences.append("Their core product lines provide high-availability computing, scalable networking, and unified management across physical and virtualized environments.")
        
    # 2. Software Licensing & Central Management
    sentences.append("Centralized management consoles, intelligent telemetry controllers, and administrative dashboards provide single-pane-of-glass oversight, granular policy enforcement, and audit compliance logging.")
    sentences.append("Software offerings are available in perpetual licenses, term subscriptions, and consumption-based models with built-in zero-trust security postures and automated threat protection.")
    
    # 3. Workload Optimization & Technical Specifications
    sentences.append("Engineered for demanding enterprise workloads, these systems deliver high-throughput data processing, automated failover clustering, and integrated data protection to prevent operational downtime.")
    sentences.append("Native interoperability with industry-standard hypervisors, hybrid cloud platforms, and container orchestration frameworks ensures frictionless deployment in heterogeneous datacenter environments.")
    
    # 4. Professional Engineering Services
    if s:
        sentences.append(f"To accelerate implementation, {clean_name} backs their technology catalog with structured professional services, including {', '.join(s[:3])}.")
        if len(s) > 3:
            sentences.append(f"Specialized technical scopes also encompass {', '.join(s[3:6])}, delivered by certified pre-sales engineers and solution architects.")
    else:
        sentences.append("Professional lifecycle services encompass pre-sales architecture sizing, bill-of-materials (BOM) design, site surveys, and proof-of-concept (POC) staging.")
        sentences.append("Certified systems engineers provide hands-on implementation, zero-downtime cutover planning, and customized operational training for technical personnel.")
        
    # 5. Mission-Critical SLAs & Maintenance Contracts
    sentences.append("Ongoing maintenance is anchored by multi-tier Service Level Agreements (SLAs), offering 24/7/365 technical helpdesk access, 4-hour on-site rapid hardware replacement, and next-business-day part dispatch.")
    sentences.append("Proactive health monitoring, automated diagnostic telemetry, and scheduled firmware patch cycles ensure continuous risk mitigation and maximum operational availability.")
    
    # 6. Pre-Sales Procurement & RFP Compliance
    sentences.append(f"Through transparent commercial discounting, certified partner margins, and fast-track quoting support, {clean_name} enables systems integrators and pre-sales teams to confidently fulfill RFP technical compliance.")
    sentences.append("This unified synergy of field-proven products, robust lifecycle services, and enterprise-grade SLAs delivers predictable total cost of ownership (TCO) and long-term investment protection.")
    
    return " ".join(sentences)

def scrape_oem_website(url, company_name=None):
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
        "portfolio_summary": "",
        "errors": []
    }
    
    # 1. Fetch homepage
    try:
        response = requests.get(cleaned_url, headers=headers, timeout=5, verify=False)
        response.raise_for_status()
        homepage_html = response.text
    except Exception as e:
        result["errors"].append(f"Homepage fetch failed: {str(e)}")
        # If homepage fails, try fallback seeding early
        fallback = seed_industry_offerings(company_name, cleaned_url)
        if fallback:
            result["status"] = "partial"
            result["title"] = company_name or urlparse(cleaned_url).netloc
            result["description"] = "Offerings loaded from catalog database."
            result["products"] = fallback["products"]
            result["services"] = fallback["services"]
            result["portfolio_summary"] = generate_oem_portfolio_summary(company_name, cleaned_url, fallback["products"], fallback["services"])
            return result
            
        # Try fetching real offerings from open internet
        open_fallback = search_open_internet_offerings(company_name)
        if open_fallback and (open_fallback.get("products") or open_fallback.get("services")):
            result["status"] = "partial"
            result["title"] = company_name or urlparse(cleaned_url).netloc
            result["description"] = f"Offerings fetched from open internet for {company_name or cleaned_url}."
            result["products"] = open_fallback.get("products", [])
            result["services"] = open_fallback.get("services", [])
            result["portfolio_summary"] = generate_oem_portfolio_summary(company_name, cleaned_url, open_fallback.get("products", []), open_fallback.get("services", []))
            return result
            
        default_p = [f"{company_name or 'Enterprise'} Technology Solutions", "Cloud Solutions & Infrastructure", "IT Consultancy & Architecture"]
        default_s = ["Managed IT Services", "SLA & Post-Sales Support", "Security Auditing & Hardening"]
        return {
            "status": "partial",
            "title": urlparse(cleaned_url).netloc,
            "description": "Auto-scraping unavailable. The website took too long to respond.",
            "products": default_p,
            "services": default_s,
            "portfolio_summary": generate_oem_portfolio_summary(company_name, cleaned_url, default_p, default_s),
            "errors": [str(e)]
        }
        
    soup = BeautifulSoup(homepage_html, 'html.parser')
    
    # Extract metadata
    result["title"] = soup.title.get_text().strip() if (soup.title and soup.title.get_text()) else urlparse(cleaned_url).netloc
    meta_desc = soup.find('meta', attrs={'name': re.compile(r'description', re.I)})
    if not meta_desc:
        meta_desc = soup.find('meta', attrs={'property': 'og:description'})
    if meta_desc and meta_desc.get('content'):
        result["description"] = meta_desc.get('content').strip()
        
    # 2. Heuristics for finding Solutions/Products/Services subpages
    subpage_links = []
    keywords = [
        'product', 'service', 'solution', 'what we do', 'portfolio', 'offering',
        'capability', 'platform', 'system', 'software', 'hardware', 'technology',
        'expertise', 'security', 'infrastructure', 'cloud', 'backup'
    ]
    
    for link in soup.find_all('a', href=True):
        href = link['href']
        text = link.get_text().lower()
        
        if any(kw in text or kw in href.lower() for kw in keywords):
            if any(ignore in text or ignore in href.lower() for ignore in ['contact', 'career', 'job', 'blog', 'news', 'privacy', 'term', 'support', 'help', 'login', 'register']):
                continue
                
            full_link = urljoin(cleaned_url, href)
            if urlparse(full_link).netloc == urlparse(cleaned_url).netloc:
                subpage_links.append((full_link, text))
                
    # Deduplicate and limit to top 3 subpages for speed
    seen_links = set()
    unique_subpage_links = []
    for link, name in subpage_links:
        if link not in seen_links and link != cleaned_url:
            seen_links.add(link)
            unique_subpage_links.append((link, name))
            if len(unique_subpage_links) >= 3:
                break
                
    # 3. Extract items from homepage
    homepage_items = extract_items_from_soup(soup, is_subpage=False)
    result["products"].extend(homepage_items["products"])
    result["services"].extend(homepage_items["services"])
    
    # 4. Extract from subpages in parallel using ThreadPoolExecutor for fast execution
    import concurrent.futures
    def fetch_subpage(item):
        s_link, s_name = item
        try:
            s_resp = requests.get(s_link, headers=headers, timeout=3.5, verify=False)
            if s_resp.status_code == 200:
                s_soup = BeautifulSoup(s_resp.text, 'html.parser')
                s_items = extract_items_from_soup(s_soup, is_subpage=True)
                return s_link, s_name, s_items
        except Exception:
            pass
        return s_link, s_name, None

    if unique_subpage_links:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(3, len(unique_subpage_links))) as sub_exec:
            for s_link, s_name, s_items in sub_exec.map(fetch_subpage, unique_subpage_links):
                if s_items:
                    if any(p_kw in s_link.lower() or p_kw in s_name for p_kw in ['product', 'hardware', 'appliance', 'software', 'device']):
                        result["products"].extend(s_items["products"])
                        result["products"].extend(s_items["services"])
                    elif any(s_kw in s_link.lower() or s_kw in s_name for s_kw in ['service', 'consult', 'support', 'management', 'professional']):
                        result["services"].extend(s_items["services"])
                        result["services"].extend(s_items["products"])
                    else:
                        result["products"].extend(s_items["products"])
                        result["services"].extend(s_items["services"])
            
    # Clean up, deduplicate, and filter lists
    result["products"] = clean_and_deduplicate(result["products"])
    result["services"] = clean_and_deduplicate(result["services"])
    
    # 5. Enrichment & Fallback: Prioritize curated enterprise catalog if available, or enrich with open internet
    fallback = seed_industry_offerings(company_name, cleaned_url)
    if fallback:
        # Prepend curated catalog offerings for high accuracy
        for p in reversed(fallback["products"]):
            if p not in result["products"]:
                result["products"].insert(0, p)
        for s in reversed(fallback["services"]):
            if s not in result["services"]:
                result["services"].insert(0, s)
    elif len(result["products"]) < 3 or len(result["services"]) < 3:
        open_fallback = search_open_internet_offerings(company_name)
        if open_fallback:
            for p in open_fallback.get("products", []):
                if p not in result["products"]:
                    result["products"].append(p)
            for s in open_fallback.get("services", []):
                if s not in result["services"]:
                    result["services"].append(s)

    # Double-check default fallbacks if still empty
    if not result["products"] and not result["services"]:
        result["products"] = ["Enterprise Systems Infrastructure", "Software Licenses & Maintenance", "Technology Modules"]
        result["services"] = ["Implementation & Integration", "Professional Consultation Services", "Annual Support SLA Contracts"]
        
    # Limit to top 8 items each to keep UI tidy
    result["products"] = result["products"][:8]
    result["services"] = result["services"][:8]
    
    # 6. Generate rich 10-15 line portfolio overview from internet intelligence & offerings
    result["portfolio_summary"] = generate_oem_portfolio_summary(
        company_name,
        cleaned_url,
        result["products"],
        result["services"],
        result.get("description", "")
    )
    
    return result

def extract_items_from_soup(soup, is_subpage=False):
    products = []
    services = []
    
    # Helper to check if string looks like navigation, questions, or marketing noise
    def is_noise(text):
        text_l = text.lower().strip()
        if len(text_l) < 4 or len(text_l) > 75:
            return True
        # Marketing noise, questions, CTAs, footers
        if text_l.endswith('?'):
            return True
        if text_l.startswith(('call ', 'tel:', 'mailto:')) or '1-800' in text_l or '1-888' in text_l:
            return True
        words_lower = text_l.split()
        sentence_verbs = {'is', 'are', 'was', 'were', 'has', 'have', 'had', 'will', 'can', 'should', 'could', 'why', 'how', 'what', 'when'}
        if any(w in sentence_verbs for w in words_lower):
            return True
        imperative_starts = ('innovate', 'modernize', 'accelerate', 'transform', 'discover', 'explore', 'read', 'watch', 'see', 'learn', 'try', 'join')
        if text_l.startswith(imperative_starts):
            return True
        nav_elements = [
            'view more', 'learn more', 'read more', 'contact us', 'get started', 'sign up', 'see details',
            'home', 'about', 'careers', 'blog', 'privacy policy', 'site map', 'all rights reserved',
            'quick links', 'industries', 'company', 'resources', 'products', 'services', 'solutions',
            'support', 'partners', 'downloads', 'legal', 'newsletter', 'follow us', 'search',
            'free trial', 'free', 'trial', 'no credit card', 'faq', 'faqs', 'request demo',
            'schedule demo', 'book demo', 'get a quote', 'sign in', 'log in', 'register now',
            'cookie', 'cookies', 'terms of', 'press release'
        ]
        return any(nav == text_l or nav in text_l for nav in nav_elements)

    # Heuristic A: Look for list items next to heading titles containing product/service keywords
    for heading in soup.find_all(['h1', 'h2', 'h3', 'h4']):
        heading_text = heading.get_text().strip().lower()
        is_product_heading = any(k in heading_text for k in ['product', 'hardware', 'appliance', 'device', 'software', 'licensing'])
        is_service_heading = any(k in heading_text for k in ['service', 'solution', 'consult', 'support', 'training', 'professional', 'what we do'])
        
        if is_product_heading or is_service_heading:
            # Look at sibling lists
            sibling = heading.find_next_sibling()
            limit = 3
            while sibling and limit > 0:
                if sibling.name in ['ul', 'ol']:
                    list_items = [li.get_text().strip() for li in sibling.find_all('li')]
                    for li in list_items:
                        if not is_noise(li):
                            if is_product_heading:
                                products.append(li)
                            else:
                                services.append(li)
                    break
                elif sibling.name in ['div']:
                    list_items = [li.get_text().strip() for li in sibling.find_all('li')]
                    for li in list_items:
                        if not is_noise(li):
                            if is_product_heading:
                                products.append(li)
                            else:
                                services.append(li)
                    break
                sibling = sibling.next_sibling
                limit -= 1

    # Heuristic B: Look at general cards or grid items that might represent products or services
    for item in soup.find_all(class_=re.compile(r'(product|service|solution|portfolio)-?(card|item|box|title|name)', re.I)):
        text = item.get_text().strip()
        if not is_noise(text):
            clean_text = " ".join(text.split())
            if any(k in clean_text.lower() for k in ['service', 'consult', 'support', 'management', 'professional']):
                services.append(clean_text)
            else:
                products.append(clean_text)

    # Heuristic C: On Solutions/Services subpages, headings (h2, h3) themselves are often the service names
    if is_subpage:
        for heading in soup.find_all(['h2', 'h3', 'h4']):
            text = heading.get_text().strip()
            # Ensure text is not navigation noise and is capitalized/title-cased (e.g. "Unified Communications")
            if not is_noise(text) and len(text.split()) >= 1:
                # Check capitalization (at least first letter of words is capital)
                words = [w for w in text.split() if w.isalpha()]
                capital_words = [w for w in words if w[0].isupper()]
                if len(words) > 0 and len(capital_words) / len(words) >= 0.6:
                    clean_text = " ".join(text.split())
                    if any(k in clean_text.lower() for k in ['service', 'consult', 'support', 'management', 'security', 'sla', 'outsourc']):
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
        # Remove trailing periods or quotes
        item = item.strip('."\'')
        # Filter out item text that is too long, too short, or has navigation labels
        if not item or len(item) < 3 or len(item) > 75:
            continue
        # Ignore numbers only or boilerplate
        if item.isdigit():
            continue
        
        # Check against common noise keywords, questions, or marketing CTAs
        if item.endswith('?') or item.startswith(('call ', 'tel:', 'mailto:')):
            continue
        noise_words = [
            'view more', 'learn more', 'read more', 'contact us', 'get started', 'sign up', 'see details', 'click here',
            'free trial', 'free', 'trial', 'no credit card', 'faq', 'faqs', 'request demo',
            'schedule demo', 'book demo', 'get a quote', 'sign in', 'log in', 'register now',
            'cookie', 'cookies', 'terms of', 'press release', 'all rights reserved'
        ]
        if any(nw in item.lower() for nw in noise_words):
            continue
            
        item_lower = item.lower()
        words_lower = item_lower.split()
        sentence_verbs = {'is', 'are', 'was', 'were', 'has', 'have', 'had', 'will', 'can', 'should', 'could', 'why', 'how', 'what', 'when'}
        if any(w in sentence_verbs for w in words_lower):
            continue
        imperative_starts = ('innovate', 'modernize', 'accelerate', 'transform', 'discover', 'explore', 'read', 'watch', 'see', 'learn', 'try', 'join')
        if item_lower.startswith(imperative_starts):
            continue
            
        if item_lower not in seen:
            seen.add(item_lower)
            cleaned.append(item)
            
    return cleaned

def seed_industry_offerings(company_name, url):
    """
    Indigenous fallback DB offering customized product catalogs for major brands
    """
    corpus = f"{company_name or ''} {url or ''}".lower()
    
    if "crowdstrike" in corpus or "falcon" in corpus:
        return {
            "products": ["CrowdStrike Falcon Insight XDR", "Falcon Prevent Next-Gen Antivirus (NGAV)", "Falcon Cloud Security (CNAPP)", "Falcon Identity Threat Protection", "Falcon LogScale Next-Gen SIEM"],
            "services": ["CrowdStrike Falcon Complete Managed Detection (MDR)", "CrowdStrike Incident Response & Forensics", "Cybersecurity Maturity Assessment", "Proactive Threat Hunting & Readiness"]
        }
    elif "pure storage" in corpus or "purestorage" in corpus:
        return {
            "products": ["Pure Storage FlashArray //X & //C", "Pure Storage FlashBlade Unified Fast File & Object", "Portworx Enterprise Kubernetes Storage", "Pure1 AI-Powered Storage Management"],
            "services": ["Evergreen//One Storage-as-a-Service SLA", "Storage Modernization & Migration Consulting", "Ransomware Recovery & SafeMode Setup", "Datacenter SAN Storage Architecture Design"]
        }
    elif "cisco" in corpus:
        return {
            "products": ["Cisco Catalyst Switches (9000 Series)", "Cisco Integrated Services Routers (ISR)", "Cisco Meraki Cloud-Managed Access Points", "Cisco Firepower Next-Gen Firewalls", "Webex Room Collaboration Hardware", "Cisco Nexus Data Center Switches"],
            "services": ["Cisco Smartnet SLA Support Contracts", "Network Architecture & Design Consultation", "Meraki Dashboard Management Service", "Network Security Hardening & Implementation"]
        }
    elif "fortinet" in corpus:
        return {
            "products": ["FortiGate Next-Generation Firewalls", "FortiAP Wireless Access Points", "FortiSwitch Secure Access Switches", "FortiClient Endpoint Security Client", "FortiAnalyzer centralized reporting", "FortiManager centralized firewall controller"],
            "services": ["FortiGuard Security Subscription SLA", "FortiCare Technical Outsource Support", "UTM Security Firewall Auditing", "Fortinet Zero Trust Implementation"]
        }
    elif "palo alto" in corpus or "panw" in corpus:
        return {
            "products": ["Palo Alto PA-Series Next-Gen Firewalls", "Prisma Access (SASE Security)", "Cortex XDR Endpoint Threat Detection", "Prisma Cloud Security Platform", "WildFire Malware Prevention System"],
            "services": ["PAN-OS Firewall Configuration Audit", "Incident Response & Threat Hunting Consultation", "SecOps SOC Managed Monitoring SLA", "Prisma Cloud Compliance Compliance Mapping"]
        }
    elif "microsoft" in corpus or "azure" in corpus:
        return {
            "products": ["Microsoft Azure Cloud Subscriptions", "Microsoft 365 Enterprise Licenses (E3/E5)", "Microsoft Windows Server 2025 Standard", "Microsoft SQL Server Database Licenses", "Microsoft Exchange Server Platform"],
            "services": ["Azure Cloud Migration & Modernization", "Active Directory Security Audits", "Microsoft 365 Managed Collaboration SLA", "SharePoint Intranet Design & Integration"]
        }
    elif "vmware" in corpus or "broadcom" in corpus:
        return {
            "products": ["VMware vSphere Enterprise Hypervisor", "VMware NSX Software-Defined Networking", "VMware vSAN Virtual Storage Solutions", "VMware Cloud Foundation (VCF) Suite", "VMware Horizon Virtual Desktop VDI"],
            "services": ["Hyperconverged Infrastructure Consultation", "vSphere Performance Tuning & Optimization", "Virtual Datacenter Disaster Recovery Plan", "NSX Micro-segmentation Audit"]
        }
    elif "sophos" in corpus:
        return {
            "products": ["Sophos Intercept X Endpoint Protection", "Sophos XGS Firewall Security Appliances", "Sophos RED (Remote Ethernet Devices)", "Sophos Email Security Gateway"],
            "services": ["Sophos Central Cloud Management SLA", "Sophos MDR (Managed Detection & Response)", "Endpoint Antivirus Auditing & Remediation", "Branch Network VPN Deployment"]
        }
    elif "dell" in corpus:
        return {
            "products": ["Dell PowerEdge Rack & Tower Servers", "Dell PowerStore / PowerScale Enterprise Storage", "Dell Latitude Business Laptops", "Dell OptiPlex Enterprise Desktops", "Dell Networking S-Series Switches"],
            "services": ["Dell ProSupport Plus SLA Support", "Server Room Rack Architecture Design", "SAN Storage Virtualization Configuration", "Enterprise Desktop Deployment & Lifecycle Management"]
        }
    elif "hp" in corpus or "hpe" in corpus:
        return {
            "products": ["HPE ProLiant Rack/Blade Servers", "Aruba CX Enterprise Switches", "Aruba Instant On Access Points", "HPE Alletra Storage Arrays", "HP LaserJet Pro Enterprise Printers"],
            "services": ["HPE Pointnext Hardware SLA Maintenance", "Aruba ClearPass Access Control Audit", "Enterprise Wireless Site Surveys", "Hybrid Server Infrastructure Optimization"]
        }
    elif "lenovo" in corpus:
        return {
            "products": ["Lenovo ThinkSystem Rack Servers", "Lenovo ThinkSystem DE/DM Storage Arrays", "Lenovo ThinkPad Executive Laptops", "Lenovo ThinkCentre Compact Desktops"],
            "services": ["Lenovo Premier SLA Support Contracts", "Server Room Power & Cooling Consulting", "Data Center Server Migration Services", "Enterprise VDI Implementation"]
        }
    elif "veeam" in corpus:
        return {
            "products": ["Veeam Backup & Replication Enterprise", "Veeam ONE Monitoring & Analytics Suite", "Veeam Backup for Microsoft 365", "Veeam Recovery Orchestrator"],
            "services": ["Disaster Recovery Architecture Plan", "Veeam Enterprise Backup Job Auditing", "Ransomware Immutability Hardening Services", "Offsite Cloud Backup Replication Setup"]
        }
    elif "nutanix" in corpus:
        return {
            "products": ["Nutanix Acropolis Software (AOS)", "Nutanix AHV Enterprise Hypervisor", "Nutanix Files (Unified Storage Solution)", "Nutanix Prism Central Controllers"],
            "services": ["Hyperconverged Infrastructure Design", "Nutanix Prism Management SLA Support", "Data Center Virtualization Audit", "AHV Migration & Deployment Services"]
        }
    elif "juniper" in corpus:
        return {
            "products": ["Juniper EX Series Ethernet Switches", "Juniper SRX Series Secure Gateways", "Juniper MX Series Universal Routing Platforms", "Juniper Mist AI Wireless Access Points"],
            "services": ["Junos OS Deployment & Configuration", "Mist AI WLAN Site Optimization SLA", "Juniper SRX Security Policy Audits", "Core Router Routing Protocol Implementation"]
        }
    elif "check point" in corpus or "checkpoint" in corpus:
        return {
            "products": ["Check Point Quantum Security Gateways", "Check Point CloudGuard Cloud Security", "Check Point Harmony Endpoint Security", "Check Point Horizon Unified Management"],
            "services": ["Quantum Firewall Rule Optimization SLA", "Check Point Cloud Security Architecture Design", "Remote Access VPN Enforcement Services", "Zero-day Threat Prevention Audits"]
        }
    elif "red hat" in corpus or "redhat" in corpus:
        return {
            "products": ["Red Hat Enterprise Linux (RHEL)", "Red Hat OpenShift Container Platform", "Red Hat Ansible Automation Platform", "Red Hat OpenStack Platform"],
            "services": ["Linux Server Security Patching Support", "Kubernetes OpenShift Orchestration Setup", "Ansible Playbook Automation Consulting", "System Virtualization Migration Services"]
        }
    elif "google" in corpus or "gcp" in corpus:
        return {
            "products": ["Google Cloud Platform (GCP) Compute", "Google Cloud Storage Packages", "Google Workspace Business Licenses", "Google BigQuery Analytics Engine"],
            "services": ["GCP Cloud Migration & Architecture Setup", "Google Workspace Tenant Hardening", "Data Warehouse Cloud ETL Consulting", "Kubernetes GKE Container Deployment Services"]
        }
    elif "apc" in corpus or "schneider" in corpus:
        return {
            "products": ["APC Smart-UPS Uninterruptible Power", "APC Symmetra modular UPS units", "APC NetShelter Server Racks", "APC NetBotz Environmental Sensors"],
            "services": ["Server Room Power Capacity Calculations", "APC Battery Replacement SLA Services", "Environmental Rack Monitoring Setup", "Datacenter Rack Cooling Assessments"]
        }
    
    return None

def fetch_oem_news_rss(oem_name):
    import xml.etree.ElementTree as ET
    import urllib.request
    import urllib.parse
    import ssl
    import re
    
    query = f'"{oem_name}" new products OR offerings OR services OR launch'
    encoded_query = urllib.parse.quote(query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-us&gl=US&ceid=US:en"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    articles = []
    try:
        req = urllib.request.Request(rss_url, headers=headers)
        context = ssl._create_unverified_context()
        with urllib.request.urlopen(req, timeout=8, context=context) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        for item in root.findall('.//item')[:5]:
            title = item.find('title')
            link = item.find('link')
            pub_date = item.find('pubDate')
            source = item.find('source')
            
            title_text = title.text if title is not None else ""
            link_url = link.text if link is not None else ""
            pub_date_text = pub_date.text if pub_date is not None else ""
            source_text = source.text if source is not None else ""
            
            description = item.find('description')
            snippet_text = ""
            if description is not None and description.text:
                clean_desc = re.sub(r'<[^>]+>', '', description.text)
                snippet_text = clean_desc[:250].strip()
                
            clean_title = title_text
            if " - " in title_text:
                parts = title_text.rsplit(" - ", 1)
                if len(parts) > 1:
                    clean_title = parts[0].strip()
                    
            if title_text and link_url:
                articles.append({
                    "oem_name": oem_name,
                    "title": clean_title,
                    "link": link_url,
                    "pub_date": pub_date_text,
                    "source": source_text,
                    "snippet": snippet_text
                })
    except Exception as e:
        print(f"Error fetching news for {oem_name}: {e}")
        
    return articles

def search_open_internet_offerings(company_name):
    """
    Fetches open-internet information for a company using Wikipedia API and Bing search
    to extract actual products and services from corporate summaries and industry corpus.
    """
    if not company_name:
        return {"products": [], "services": []}
        
    import urllib.parse
    
    clean_name = company_name.strip()
    corpus_parts = []
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/json,*/*;q=0.8'
    }
    
    # 1. Wikipedia Summary API (Fast, authoritative, high-uptime)
    try:
        wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(clean_name)}"
        w_resp = requests.get(wiki_url, headers=headers, timeout=4)
        if w_resp.status_code == 200:
            w_data = w_resp.json()
            extract = w_data.get('extract', '')
            desc = w_data.get('description', '')
            if extract:
                corpus_parts.append(extract)
            if desc:
                corpus_parts.append(desc)
    except Exception as e:
        pass
        
    # 2. Bing Web Search (Fast snippet corpus from open web)
    try:
        query = f"{clean_name} products solutions services overview"
        bing_url = f"https://www.bing.com/search?q={urllib.parse.quote_plus(query)}"
        b_resp = requests.get(bing_url, headers=headers, timeout=4)
        if b_resp.status_code == 200:
            b_soup = BeautifulSoup(b_resp.text, 'html.parser')
            for p in b_soup.find_all('p'):
                txt = p.get_text().strip()
                if len(txt) > 20:
                    corpus_parts.append(txt)
            for h in b_soup.find_all(['h2', 'h3']):
                txt = h.get_text().strip()
                if len(txt) > 10 and not any(skip in txt.lower() for skip in ['sign in', 'cookie', 'feedback', 'search']):
                    corpus_parts.append(txt)
    except Exception as e:
        pass

    # 3. DuckDuckGo HTML fallback
    if len(corpus_parts) < 2:
        try:
            ddg_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(clean_name + ' solutions products')}"
            d_resp = requests.get(ddg_url, headers=headers, timeout=3, verify=False)
            if d_resp.status_code == 200:
                d_soup = BeautifulSoup(d_resp.text, 'html.parser')
                snippets = [s.get_text() for s in d_soup.find_all(class_='result__snippet')]
                corpus_parts.extend(snippets)
        except Exception:
            pass
            
    full_corpus = " ".join(corpus_parts).lower()
    matched = match_industry_terms_from_corpus(full_corpus, clean_name)
    
    return {
        "products": list(dict.fromkeys(matched["products"]))[:8],
        "services": list(dict.fromkeys(matched["services"]))[:8]
    }

def match_industry_terms_from_corpus(corpus, company_name):
    """
    Matches industry-standard terms against a scraped corpus of search snippets.
    """
    products = []
    services = []
    
    term_mappings = {
        "products": [
            ("gpu", "High-Performance GPU & AI Accelerators"),
            ("graphics processing", "Discrete & Data Center Graphics Processors"),
            ("artificial intelligence", "Enterprise AI & Machine Learning Platforms"),
            ("deep learning", "Deep Learning Inference & Training Software"),
            ("firewall", "Next-Generation Firewall Security Gateway"),
            ("switch", "Enterprise Layer-3 Routing Switches"),
            ("router", "Core Network Access & WAN Routers"),
            ("access point", "Unified Cloud-Managed Access Points"),
            ("server", "High-Performance Server Nodes & Racks"),
            ("storage", "Unified SAN/NAS Storage Solutions"),
            ("hypervisor", "Virtualization Platform Hypervisor"),
            ("backup", "Enterprise Backup & Disaster Recovery Systems"),
            ("data protection", "Data Resilience & Immutable Backup Solutions"),
            ("ransomware", "Ransomware Detection & Rapid Recovery"),
            ("sase", "Secure Access Service Edge (SASE) Gateways"),
            ("cloud", "Hybrid Cloud & Virtualization Infrastructure"),
            ("compute", "Accelerated Computing & High-Performance Clusters"),
            ("ups", "Uninterruptible Power Supply (UPS) Modules"),
            ("sensor", "IoT/Environmental Security Sensors"),
            ("license", "Enterprise Software Licensing Modules"),
            ("database", "Managed High-Speed SQL Database Engines"),
            ("endpoint", "Endpoint Detection & Response (EDR) Protection"),
            ("identity", "Identity Access Management (IAM) Platforms"),
            ("monitoring", "Network Operations Monitoring Controllers"),
            ("collaboration", "Enterprise Unified Collaboration Hardware"),
            ("saas", "Cloud SaaS Subscription Platforms"),
            ("antivirus", "Centralized Host Antivirus Packages"),
            ("wlan", "Enterprise Wireless LAN Controllers"),
            ("cybersecurity", "Zero-Trust Cybersecurity Defense Suite"),
            ("workstation", "Professional Precision Engineering Workstations")
        ],
        "services": [
            ("support", "24/7 SLA Technical Outsource Support"),
            ("sla", "Annual Hardware Maintenance Support Contracts"),
            ("consult", "Enterprise Network Architecture Design Consulting"),
            ("migration", "Cloud Server Migration & Setup Services"),
            ("audit", "Security Audit & Vulnerability Assessments"),
            ("incident", "Incident Response & Cyber Threat Hunting"),
            ("soc", "Managed Security Operations (SOC) Monitoring"),
            ("managed", "Managed IT Helpdesk Outsource Support"),
            ("integration", "System Integration & Deployment Services"),
            ("hardening", "Firewall Rule Optimization & Hardening"),
            ("recovery", "Disaster Recovery Planning & Sizing Setup"),
            ("training", "Technical Product Training & Enablement"),
            ("wireless site survey", "Enterprise Wireless Site Survey & Planning"),
            ("patching", "Linux & Windows OS Patching Management"),
            ("implementation", "Zero-Trust Infrastructure Implementation"),
            ("optimization", "Workload Performance Tuning & Sizing Services"),
            ("deployment", "Full-Lifecycle Hardware & Software Deployment")
        ]
    }
    
    # Perform keyword matches
    for keyword, label in term_mappings["products"]:
        if keyword in corpus:
            products.append(label)
            
    for keyword, label in term_mappings["services"]:
        if keyword in corpus:
            services.append(label)
            
    # Default fallback based on company name
    if not products:
        products.append(f"{company_name or 'Enterprise'} Technology Solutions")
        products.append(f"{company_name or 'Enterprise'} Hardware & Software Modules")
    if not services:
        services.append(f"{company_name or 'Enterprise'} Consultation & Integration SLA")
        services.append(f"{company_name or 'Enterprise'} 24/7 Technical Support")
        
    return {
        "products": products,
        "services": services
    }

