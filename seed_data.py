import json
import database

def seed_demo_data():
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    # Check if we already have contacts
    cursor.execute('SELECT COUNT(*) FROM contacts')
    count = cursor.fetchone()[0]
    if count > 0:
        print("Database already contains data. Skipping seeding.")
        conn.close()
        return
        
    # Get the default admin user we seeded
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    admin_id = cursor.fetchone()[0]
    
    # 1. Cisco Systems (OEM)
    cisco_products = [
        "Cisco Catalyst 9300 Switches",
        "Cisco Meraki MR46 Access Points",
        "Cisco Firepower 2100 Firewall",
        "Webex Room Kit Mini"
    ]
    cisco_services = [
        "Cisco SmartNet Support Service",
        "Enterprise Network Design Consulting",
        "Meraki Cloud License Management"
    ]
    
    cursor.execute('''
    INSERT INTO contacts (
        name, company_name, type, designation, email, phone, website, address,
        fetched_products, fetched_services, custom_products, custom_services, created_by
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        "Rahul Sharma", "Cisco Systems", "OEM", "Senior Channel Manager", 
        "rahul.sharma@cisco.com", "+91 98112 34567", "https://www.cisco.com",
        "Cisco Systems India, Prestige Cessna Business Park, Bengaluru, Karnataka 560103",
        json.dumps(cisco_products), json.dumps(cisco_services), 
        json.dumps(["Cisco Catalyst Center Deployment Spec"]), json.dumps(["Custom SLA Support Tier"]),
        admin_id
    ))
    cisco_id = cursor.lastrowid
    
    # 2. Redington India (Distributor)
    redington_products = [
        "Fortinet FortiGate 60F Firewalls",
        "Dell PowerEdge R750 Servers",
        "HP ProBook Laptops",
        "Microsoft 365 Business Standard Licenses"
    ]
    redington_services = [
        "Value Added Distribution Services",
        "Pre-Sales Configuration Assistance",
        "RMA & Logistics Support"
    ]
    
    cursor.execute('''
    INSERT INTO contacts (
        name, company_name, type, designation, email, phone, website, address,
        fetched_products, fetched_services, custom_products, custom_services, created_by
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        "Priya Patel", "Redington India", "Distributor", "Business Head - Enterprise", 
        "priya.patel@redingtongroup.com", "+91 99223 88440", "https://redingtongroup.com",
        "Redington Tower, Inner Ring Road, Guindy, Chennai, Tamil Nadu 600032",
        json.dumps(redington_products), json.dumps(redington_services),
        json.dumps([]), json.dumps(["Pre-staging & Integration Lab"]),
        admin_id
    ))
    redington_id = cursor.lastrowid
    
    # 3. Add initial Interactions
    cursor.execute('''
    INSERT INTO interactions (contact_id, user_id, interaction_date, type, summary, next_steps)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        cisco_id, admin_id, "2026-06-25", "Meeting",
        "QBR meeting held at Cisco Bangalore office. Discussed partner tier promotion and special discount pricing (SPA) for upcoming government network modernization RFPs.",
        "Submit partner registration form for the modernization bid by July 5th."
    ))
    
    cursor.execute('''
    INSERT INTO interactions (contact_id, user_id, interaction_date, type, summary, next_steps)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        cisco_id, admin_id, "2026-06-29", "Call",
        "Quick phone catch up with Rahul regarding the Catalyst 9300 shipping delays. He confirmed they can prioritize pre-sales demo stock for our proof-of-concept next week.",
        "Rahul to send shipping details. Pre-sales engineers to prepare POC room."
    ))
    
    cursor.execute('''
    INSERT INTO interactions (contact_id, user_id, interaction_date, type, summary, next_steps)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        redington_id, admin_id, "2026-06-28", "Email",
        "Sent pricing request for 50x FortiGate 60F firewalls for the new bank branches roll-out. Asked Priya for bulk distribution quote.",
        "Awaiting Priya's quotation sheets (expected by June 30th)."
    ))
    
    # 4. Add system log
    cursor.execute('''
    INSERT INTO audit_logs (user_id, action, details)
    VALUES (?, ?, ?)
    ''', (admin_id, "SYSTEM_SEED", "Demo data (Cisco, Redington, Interactions) successfully seeded."))
    
    conn.commit()
    conn.close()
    print("Demo data seeded successfully.")

if __name__ == '__main__':
    seed_demo_data()
