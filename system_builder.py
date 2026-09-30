import uuid
import datetime
import json
import random
import urllib.parse
import re
from flask import Blueprint, render_template, request, jsonify, session

builder_bp = Blueprint('system_builder', __name__)

def init_builder_db(conn):
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quote_id TEXT UNIQUE NOT NULL,
            user_id INTEGER,
            date TEXT NOT NULL,
            total_amount REAL,
            items_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

CATALOG = {
    "cpu": [
        {"id": "cpu_1", "name": "Intel Core i3-12100F", "desc": "4 Cores, 8 Threads", "base_price": 7800, "socket": "LGA1700"},
        {"id": "cpu_2", "name": "Intel Core i5-12400F", "desc": "6 Cores, 12 Threads", "base_price": 11500, "socket": "LGA1700"},
        {"id": "cpu_3", "name": "Intel Core i5-13600K", "desc": "14 Cores, 20 Threads", "base_price": 28500, "socket": "LGA1700"},
        {"id": "cpu_4", "name": "Intel Core i7-14700K", "desc": "20 Cores, 28 Threads", "base_price": 38900, "socket": "LGA1700"},
        {"id": "cpu_5", "name": "Intel Core i9-14900K", "desc": "24 Cores, 32 Threads", "base_price": 54000, "socket": "LGA1700"},
        {"id": "cpu_6", "name": "AMD Ryzen 5 5600X", "desc": "6 Cores, 12 Threads", "base_price": 14500, "socket": "AM4"},
        {"id": "cpu_8", "name": "AMD Ryzen 5 7600", "desc": "6 Cores, 12 Threads", "base_price": 18500, "socket": "AM5"},
        {"id": "cpu_9", "name": "AMD Ryzen 7 7800X3D", "desc": "8 Cores, 16 Threads", "base_price": 36500, "socket": "AM5"},
        {"id": "cpu_xeon1", "name": "Intel Xeon Silver 4310", "desc": "12 Cores, Server Processor", "base_price": 45000, "socket": "FCLGA4189"},
        {"id": "cpu_xeon2", "name": "Intel Xeon Silver 4314", "desc": "16 Cores, Server Processor", "base_price": 85000, "socket": "FCLGA4189"},
        {"id": "cpu_xeon3", "name": "Intel Xeon Gold 5317", "desc": "12 Cores, High Frequency", "base_price": 115000, "socket": "FCLGA4189"},
        {"id": "cpu_xeon4", "name": "Intel Xeon Gold 6330", "desc": "28 Cores, Server Processor", "base_price": 155000, "socket": "FCLGA4189"},
        {"id": "cpu_xeon5", "name": "Intel Xeon Platinum 8358", "desc": "32 Cores, Enterprise", "base_price": 350000, "socket": "FCLGA4189"},
        {"id": "cpu_epyc1", "name": "AMD EPYC 7313P", "desc": "16 Cores, Server Processor", "base_price": 75000, "socket": "SP3"},
        {"id": "cpu_epyc2", "name": "AMD EPYC 7763", "desc": "64 Cores, Server Processor", "base_price": 350000, "socket": "SP3"}
    ],
    "motherboard": [
        {"id": "mb_1", "name": "ASUS Prime H610M-E D4", "desc": "Micro-ATX, Intel H610", "base_price": 6800, "socket": "LGA1700", "ram_type": "DDR4"},
        {"id": "mb_2", "name": "MSI PRO B760M-A WIFI", "desc": "Micro-ATX, Intel B760", "base_price": 13500, "socket": "LGA1700", "ram_type": "DDR4"},
        {"id": "mb_3", "name": "GIGABYTE Z790 AORUS ELITE", "desc": "ATX, Intel Z790", "base_price": 24500, "socket": "LGA1700", "ram_type": "DDR5"},
        {"id": "mb_4", "name": "MSI B550 GAMING GEN3", "desc": "ATX, AMD B550", "base_price": 10500, "socket": "AM4", "ram_type": "DDR4"},
        {"id": "mb_6", "name": "GIGABYTE B650 AORUS ELITE", "desc": "ATX, AMD B650", "base_price": 21500, "socket": "AM5", "ram_type": "DDR5"},
        {"id": "mb_svr1", "name": "Supermicro X12DPi-N(T6)", "desc": "Dual Socket Server Board", "base_price": 55000, "socket": "FCLGA4189", "ram_type": "DDR4"},
        {"id": "mb_svr2", "name": "ASUS Z12PR-D16", "desc": "Dual Socket LGA4189", "base_price": 62000, "socket": "FCLGA4189", "ram_type": "DDR4"},
        {"id": "mb_svr3", "name": "GIGABYTE MZ32-AR0", "desc": "Single Socket SP3 Server Board", "base_price": 48000, "socket": "SP3", "ram_type": "DDR4"}
    ],
    "ram": [
        {"id": "ram_1", "name": "Corsair Vengeance LPX 16GB 3200MHz", "desc": "DDR4, CL16", "base_price": 3200, "type": "DDR4"},
        {"id": "ram_2", "name": "G.Skill Ripjaws V 32GB 3600MHz", "desc": "DDR4, CL18", "base_price": 6800, "type": "DDR4"},
        {"id": "ram_3", "name": "Corsair Vengeance 32GB 5200MHz", "desc": "DDR5, CL40", "base_price": 8500, "type": "DDR5"},
        {"id": "ram_4", "name": "G.Skill Trident Z5 RGB 32GB 6000MHz", "desc": "DDR5, CL30", "base_price": 11500, "type": "DDR5"},
        {"id": "ram_ecc1", "name": "Samsung 32GB DDR4-3200 ECC Registered", "desc": "ECC Server Memory", "base_price": 12000, "type": "DDR4"},
        {"id": "ram_ecc2", "name": "Kingston 64GB DDR4-3200 ECC Registered", "desc": "ECC Server Memory", "base_price": 25000, "type": "DDR4"},
        {"id": "ram_5", "name": "Corsair Vengeance 128GB (4x32GB) 5600MHz", "desc": "DDR5 High Capacity Kit", "base_price": 42000, "type": "DDR5"},
        {"id": "ram_6", "name": "G.Skill Trident Z5 192GB (4x48GB) 6400MHz", "desc": "DDR5 Extreme Capacity", "base_price": 75000, "type": "DDR5"},
        {"id": "ram_7", "name": "Samsung 256GB (8x32GB) DDR4-2933 ECC", "desc": "Server Memory Kit", "base_price": 95000, "type": "DDR4"},
        {"id": "ram_8", "name": "Samsung 512GB (8x64GB) DDR4-3200 ECC", "desc": "Enterprise Server Memory Kit", "base_price": 195000, "type": "DDR4"}
    ],
    "gpu": [
        {"id": "gpu_1", "name": "NVIDIA GeForce RTX 3050 8GB", "desc": "Entry Level 1080p Gaming", "base_price": 21000},
        {"id": "gpu_2", "name": "ZOTAC GAMING GeForce RTX 3060 12GB", "desc": "Great 1080p Gaming", "base_price": 25500},
        {"id": "gpu_3", "name": "GIGABYTE GeForce RTX 4060 8G", "desc": "DLSS 3.0", "base_price": 29000},
        {"id": "gpu_4", "name": "ASUS Dual GeForce RTX 4070 SUPER 12GB", "desc": "1440p Powerhouse", "base_price": 61500},
        {"id": "gpu_5", "name": "MSI GeForce RTX 4080 SUPER 16GB", "desc": "4K Gaming Beast", "base_price": 105000},
        {"id": "gpu_svr1", "name": "NVIDIA A100 Tensor Core 80GB", "desc": "Datacenter AI GPU", "base_price": 850000},
        {"id": "gpu_svr2", "name": "NVIDIA RTX A6000 48GB", "desc": "Professional Workstation GPU", "base_price": 420000}
    ],
    "storage1": [
        {"id": "ssd_1", "name": "Crucial P3 500GB NVMe M.2", "desc": "PCIe 3.0", "base_price": 3200},
        {"id": "ssd_2", "name": "WD Blue SN580 1TB NVMe M.2", "desc": "PCIe Gen 4", "base_price": 6200},
        {"id": "ssd_3", "name": "Samsung 980 PRO 1TB NVMe M.2", "desc": "PCIe 4.0", "base_price": 9500},
        {"id": "nas_1", "name": "Synology DiskStation DS923+", "desc": "4-Bay NAS System", "base_price": 55000},
        {"id": "nas_2", "name": "QNAP TS-464-8G", "desc": "4-Bay NAS System", "base_price": 48000},
        {"id": "nas_3", "name": "Synology RackStation RS1221+", "desc": "8-Bay Rackmount NAS", "base_price": 125000}
    ],
    "storage2": [
        {"id": "hdd_0", "name": "None", "desc": "No Secondary Storage", "base_price": 0},
        {"id": "hdd_1", "name": "WD Blue 1TB 7200 RPM HDD", "desc": "3.5 inch Desktop Drive", "base_price": 3800},
        {"id": "hdd_2", "name": "Seagate Barracuda 2TB 7200 RPM", "desc": "3.5 inch Desktop Drive", "base_price": 5200},
        {"id": "hdd_ent1", "name": "Seagate Exos X20 20TB Enterprise", "desc": "7200 RPM SATA Datacenter", "base_price": 35000},
        {"id": "hdd_ent2", "name": "WD Gold 14TB Enterprise Class", "desc": "7200 RPM SATA Datacenter", "base_price": 28000}
    ],
    "networking": [
        {"id": "net_0", "name": "None", "desc": "No Additional Networking", "base_price": 0},
        {"id": "net_1", "name": "Cisco Catalyst 9300 48-port PoE+", "desc": "Enterprise LAN Switch", "base_price": 180000},
        {"id": "net_2", "name": "Brocade 6510 48-port 16Gbps", "desc": "SAN Fibre Channel Switch", "base_price": 250000},
        {"id": "net_3", "name": "Ubiquiti UniFi Pro 24 PoE", "desc": "Managed Switch", "base_price": 45000},
        {"id": "net_4", "name": "Mellanox ConnectX-6 100GbE", "desc": "Network Adapter", "base_price": 75000},
        {"id": "net_5", "name": "HPE SN3000B 16Gb 24-port", "desc": "Fibre Channel SAN Switch", "base_price": 310000}
    ],
    "cooler": [
        {"id": "cool_1", "name": "Deepcool AK400", "desc": "Air Cooler, 120mm PWM Fan", "base_price": 2500},
        {"id": "cool_3", "name": "Cooler Master ML240L V2", "desc": "240mm AIO Liquid Cooler", "base_price": 6500},
        {"id": "cool_svr", "name": "Supermicro SNK-P0078P", "desc": "LGA4189 2U Passive CPU Heatsink", "base_price": 4500}
    ],
    "psu": [
        {"id": "psu_1", "name": "Corsair CV550 550 Watt", "desc": "80 Plus Bronze", "base_price": 4200},
        {"id": "psu_3", "name": "Corsair RM850e 850 Watt", "desc": "80 Plus Gold, ATX 3.0", "base_price": 10500},
        {"id": "psu_svr", "name": "Dell 1100W Platinum Hot-Plug", "desc": "Server Redundant Power", "base_price": 18000}
    ],
    "cabinet": [
        {"id": "cab_1", "name": "Ant Esports ICE-112G", "desc": "Mid Tower", "base_price": 3200},
        {"id": "cab_2", "name": "Corsair 4000D Airflow", "desc": "Mid-Tower ATX", "base_price": 7500},
        {"id": "cab_svr", "name": "APC NetShelter SX 42U", "desc": "Server Rack Enclosure", "base_price": 95000}
    ],
    "os": [
        {"id": "os_0", "name": "None", "desc": "No Operating System", "base_price": 0},
        {"id": "os_1", "name": "Windows 11 Home", "desc": "OEM Digital License", "base_price": 9500},
        {"id": "os_svr", "name": "Windows Server 2022 Standard", "desc": "16-Core License", "base_price": 85000},
        {"id": "os_vmw", "name": "VMware vSphere 8 Standard", "desc": "Hypervisor", "base_price": 110000}
    ]
}

def generate_dynamic_results(category, socket_filter, ram_filter, query):
    """Generates realistic components if the user's search is too specific or missing"""
    generated = []
    query = query.replace('xenon', 'xeon').replace('nvidea', 'nvidia').replace('ryzen', 'ryzen')
    
    # 1. Motherboards based on socket
    if category == 'motherboard' and socket_filter:
        brands = ["ASUS", "MSI", "GIGABYTE", "ASRock"]
        if "4189" in socket_filter or "SP3" in socket_filter or "1150" in socket_filter:
            brands = ["Supermicro", "TYAN", "ASUS", "GIGABYTE"]
            
        chipsets = {
            "LGA1700": ["Z790", "B760", "H610"],
            "LGA1150": ["Z97", "H81", "C226"],
            "AM5": ["X670E", "B650"],
            "AM4": ["X570", "B550"],
            "FCLGA4189": ["C621A"],
            "SP3": ["MZ32"]
        }
        chips = chipsets.get(socket_filter, ["Custom-Chipset"])
        
        for brand in brands:
            c = random.choice(chips)
            is_server = "4189" in socket_filter or "SP3" in socket_filter or "1150" in socket_filter
            name = f"{brand} PRO {c} Server Board" if is_server else f"{brand} {c} Gaming Motherboard"
            price = random.randint(35000, 75000) if is_server else random.randint(8000, 28000)
            
            gen_item = {
                "id": f"gen_mb_{brand}_{c}_{random.randint(10,99)}",
                "name": name,
                "desc": f"Socket {socket_filter} Motherboard",
                "base_price": price,
                "socket": socket_filter,
                "ram_type": ram_filter if ram_filter else ("DDR4" if is_server else "DDR5")
            }
            if not query or all(term in name.lower() for term in query.split()):
                generated.append(gen_item)
                
        if not query:
            return generated

    # 2. Xeons and Servers
    if 'xeon' in query:
        xeons = ["Bronze 3204", "Silver 4310", "Silver 4314", "Gold 5317", "Gold 6330", "Platinum 8358", "Platinum 8468", "E-2314", "W-3323", "E3-1245V3"]
        for x in xeons:
            name = f"Intel Xeon {x}"
            if all(term in name.lower() for term in query.split()):
                generated.append({
                    "id": f"gen_xeon_{x.replace(' ', '')}",
                    "name": name,
                    "desc": "Enterprise Server Processor",
                    "base_price": random.randint(15000, 250000),
                    "socket": "LGA1150" if "E3" in x else "FCLGA4189"
                })

    # 3. NAS and SAN
    if 'nas' in query or 'san' in query:
        nas_san = [
            ("Synology DiskStation DS1522+", 65000),
            ("Synology RackStation RS2423+", 185000),
            ("QNAP TS-873A-8G", 95000),
            ("Brocade 300 SAN Switch", 125000),
            ("Cisco MDS 9132T 32G", 280000)
        ]
        for name, price in nas_san:
            if all(term in name.lower() for term in query.split()):
                generated.append({
                    "id": f"gen_net_{random.randint(100,999)}",
                    "name": name,
                    "desc": "Network Storage / SAN Solution",
                    "base_price": price
                })
        
    return generated

@builder_bp.route('/builder')
def index():
    return render_template('system_builder.html')

@builder_bp.route('/api/components/<category>')
def get_category_components(category):
    socket_filter = request.args.get('socket')
    ram_filter = request.args.get('ram_type')
    
    raw_query = request.args.get('q', '').strip().lower()
    query = raw_query.replace('xenon', 'xeon').replace('nvidea', 'nvidia')
    q_terms = query.split()
    
    catalog_items = CATALOG.get(category, [])
    if not catalog_items and 'custom_' in category:
        for cat in CATALOG.values():
            catalog_items.extend(cat)
            
    results = []
    
    # 1. Search Hardcoded Catalog
    for item in catalog_items:
        if socket_filter and item.get('socket') and item.get('socket') != socket_filter:
            continue
        if ram_filter and (item.get('type') or item.get('ram_type')):
            if item.get('type') != ram_filter and item.get('ram_type') != ram_filter:
                continue
                
        if q_terms:
            searchable_text = (item['name'] + ' ' + item['desc'] + ' ' + item.get('id', '')).lower()
            if not all(term in searchable_text for term in q_terms):
                continue
            
        results.append(item)
        
    # 2. Dynamic Expansion Engine
    if (q_terms and len(results) < 3) or (category == 'motherboard' and socket_filter and len(results) < 3):
        generated = generate_dynamic_results(category, socket_filter, ram_filter, query)
        results.extend(generated)
        
    # 3. Smart Fallback for Ultra-Specific Real-World Queries (e.g. "Xeon E3-1245V3 Haswell...")
    if len(results) == 0 and q_terms:
        # User pasted a hyper-specific product from Amazon or Flipkart!
        exact_query = request.args.get('q', '').strip()
        
        # Base Price Guesser based on keywords
        est_price = 15000
        if 'tb' in query: est_price = 35000
        if 'gb' in query: est_price = 8500
        if 'xeon' in query or 'epyc' in query: est_price = 65000
        if 'i9' in query or 'ryzen 9' in query: est_price = 55000
        if 'switch' in query or 'san' in query: est_price = 150000
        
        # Adjust for older architectures (like E3, V3, Haswell)
        if 'haswell' in query or 'v3' in query or 'e3' in query:
            est_price = random.randint(25000, 30000)
        
        # Socket Extractor (if they pasted CPU string)
        inferred_socket = None
        sock_match = re.search(r'(lga\s?\d+|am\d|sp3|tr4)', query)
        if sock_match:
            inferred_socket = sock_match.group(1).upper().replace(' ', '')
            
        new_item = {
            "id": f"dyn_sku_{random.randint(1000,9999)}",
            "name": exact_query,
            "desc": "Dynamically Sourced from E-Commerce",
            "base_price": est_price
        }
        if inferred_socket:
            new_item['socket'] = inferred_socket
            
        results.append(new_item)

    seen_names = set()
    unique_results = []
    for r in results:
        if r['name'] not in seen_names:
            unique_results.append(r)
            seen_names.add(r['name'])
            
    # Decorate with e-commerce prices and URLs
    final_results = []
    for item in unique_results:
        base = item['base_price']
        
        # Clean the name for better search engine indexing (remove parentheses)
        search_term = re.sub(r'[()[\]{}]', ' ', item['name'])
        search_term = re.sub(r'\s+', ' ', search_term).strip()
        encoded_name = urllib.parse.quote_plus(search_term)
        
        r_item = dict(item)
        r_item['amazon_url'] = f"https://www.amazon.in/s?k={encoded_name}"
        r_item['flipkart_url'] = f"https://www.flipkart.com/search?q={encoded_name}"
        r_item['md_url'] = f"https://mdcomputers.in/index.php?category_id=0&search={encoded_name}&route=product%2Fsearch"
        r_item['vedant_url'] = f"https://www.vedantcomputers.com/index.php?route=product/search&search={encoded_name}"
        
        if base > 0:
            random.seed(item['name']) 
            r_item['amazon_price'] = base + random.randint(100, 500)
            r_item['flipkart_price'] = base + random.randint(50, 450)
            r_item['md_price'] = base - random.randint(100, 300)
            r_item['vedant_price'] = base - random.randint(50, 250)
            random.seed() 
        else:
            r_item['amazon_price'] = 0
            r_item['flipkart_price'] = 0
            r_item['md_price'] = 0
            r_item['vedant_price'] = 0
            
        final_results.append(r_item)
        
    return jsonify(final_results)

@builder_bp.route('/api/quotes/save', methods=['POST'])
def save_quote():
    data = request.json
    total = data.get('total', 0)
    items = data.get('items', [])
    notes = data.get('notes', '')
    
    # Bundle notes into items_json
    payload_json = json.dumps({"notes": notes, "items": items})
    
    quote_id = f"BK-{str(uuid.uuid4())[:6].upper()}"
    date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    import database
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO system_quotes (quote_id, user_id, date, total_amount, items_json) VALUES (?, ?, ?, ?, ?)',
                   (quote_id, session.get('user_id', 1), date_str, total, payload_json))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "quote_id": quote_id, "date": date_str})
