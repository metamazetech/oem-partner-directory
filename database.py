import os
import sqlite3
from werkzeug.security import generate_password_hash

DB_PATH = os.environ.get('DATABASE_PATH', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'oem_tracker.db'))

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create Users Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL, -- 'admin' or 'user'
        status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
        allowed_groups TEXT NOT NULL DEFAULT 'All', -- comma-separated allowed groups or 'All'
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create Contacts Table (OEMs & Distributors)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        company_name TEXT NOT NULL,
        type TEXT NOT NULL, -- 'OEM' or 'Distributor'
        group_name TEXT, -- 'Camera', 'Networking', 'Server/Storage', etc.
        designation TEXT,
        email TEXT,
        phone TEXT,
        website TEXT,
        address TEXT,
        visiting_card_front TEXT, -- relative path to image file
        visiting_card_back TEXT, -- relative path to image file
        company_logo TEXT, -- relative path to fetched logo image
        fetched_products TEXT, -- JSON string
        fetched_services TEXT, -- JSON string
        custom_products TEXT, -- JSON string
        custom_services TEXT, -- JSON string
        contact_persons TEXT, -- JSON string of multiple contact profiles
        created_by INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
    )
    ''')
    
    # Run migration to add contact_persons if existing database doesn't have it
    cursor.execute("PRAGMA table_info(contacts)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'contact_persons' not in columns:
        cursor.execute("ALTER TABLE contacts ADD COLUMN contact_persons TEXT")
        print("Database migrated: contact_persons column added.")
    if 'group_name' not in columns:
        cursor.execute("ALTER TABLE contacts ADD COLUMN group_name TEXT")
        print("Database migrated: group_name column added to contacts.")
    if 'company_logo' not in columns:
        cursor.execute("ALTER TABLE contacts ADD COLUMN company_logo TEXT")
        print("Database migrated: company_logo column added to contacts.")
        
    # Create dynamic OEM Categories / Groups table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS oem_groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        icon TEXT DEFAULT '📁',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create Portal Settings table for Whitelabel customization
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS portal_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE NOT NULL,
        value TEXT,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Pre-seed default settings individually
    cursor.execute("INSERT OR IGNORE INTO portal_settings (key, value) VALUES (?, ?)", ('portal_name', 'OEM Directory'))
    cursor.execute("INSERT OR IGNORE INTO portal_settings (key, value) VALUES (?, ?)", ('portal_logo', ''))
    cursor.execute("INSERT OR IGNORE INTO portal_settings (key, value) VALUES (?, ?)", ('favicon', ''))
    cursor.execute("INSERT OR IGNORE INTO portal_settings (key, value) VALUES (?, ?)", ('forgot_password_enabled', 'true'))
    
    # Pre-seed default groups if empty
    cursor.execute("SELECT COUNT(*) FROM oem_groups")
    if cursor.fetchone()[0] == 0:
        default_groups = [
            ('Networking', '🌐'),
            ('Camera', '📷'),
            ('Server/Storage', '💾'),
            ('Software/Cloud', '☁️'),
            ('Other', '📂')
        ]
        cursor.executemany("INSERT INTO oem_groups (name, icon) VALUES (?, ?)", default_groups)
        print("Pre-seeded default OEM groups/categories.")
        
    cursor.execute("PRAGMA table_info(users)")
    user_columns = [col[1] for col in cursor.fetchall()]
    if 'allowed_groups' not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN allowed_groups TEXT DEFAULT 'All'")
        print("Database migrated: allowed_groups column added to users.")
    if 'theme' not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN theme TEXT DEFAULT 'theme-slate-dark'")
        print("Database migrated: theme column added to users.")
    if 'dashboard_layout' not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN dashboard_layout TEXT DEFAULT '{}'")
        print("Database migrated: dashboard_layout column added to users.")
    
    # Create Interactions Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS interactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contact_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        interaction_date TEXT NOT NULL,
        type TEXT NOT NULL, -- 'Call', 'Meeting', 'Email', 'Presentation', 'Other'
        summary TEXT NOT NULL,
        next_steps TEXT,
        followup_date TEXT, -- Date for follow-up reminder
        followup_status TEXT DEFAULT 'pending', -- 'pending', 'completed'
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')
    
    # Run migration for interactions table
    cursor.execute("PRAGMA table_info(interactions)")
    int_columns = [col[1] for col in cursor.fetchall()]
    if 'followup_date' not in int_columns:
        cursor.execute("ALTER TABLE interactions ADD COLUMN followup_date TEXT")
        print("Database migrated: followup_date added to interactions.")
    if 'followup_status' not in int_columns:
        cursor.execute("ALTER TABLE interactions ADD COLUMN followup_status TEXT DEFAULT 'pending'")
        print("Database migrated: followup_status added to interactions.")
    
    # Create Audit Logs Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        details TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    )
    ''')
    
    # Create OEM News Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS oem_news (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        oem_name TEXT NOT NULL,
        title TEXT NOT NULL,
        link TEXT UNIQUE NOT NULL,
        pub_date TEXT,
        source TEXT,
        snippet TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create Master RFPs Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS rfps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rfp_number TEXT NOT NULL UNIQUE,
        title TEXT,
        opportunity_from TEXT,
        customer_name TEXT,
        opportunity_date TEXT,
        opportunity_type TEXT,
        source TEXT,
        opportunity_owner TEXT,
        pre_bid_date TEXT,
        submission_date TEXT,
        contact_name TEXT,
        contact_address TEXT,
        contact_email TEXT,
        contact_phone TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        created_by INTEGER,
        FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
    )
    ''')

    # Create RFP BoQ Items Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS rfp_boq_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rfp_id INTEGER NOT NULL,
        item_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        FOREIGN KEY (rfp_id) REFERENCES rfps(id) ON DELETE CASCADE
    )
    ''')

    # Create RFP BoQ OEM Mappings Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS rfp_boq_oem_mappings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        boq_item_id INTEGER NOT NULL,
        oem_name TEXT NOT NULL,
        offering_details TEXT,
        remarks TEXT,
        FOREIGN KEY (boq_item_id) REFERENCES rfp_boq_items(id) ON DELETE CASCADE
    )
    ''')

    # Create RFP Document Checklist Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS rfp_checklist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rfp_id INTEGER NOT NULL,
        doc_name TEXT NOT NULL,
        doc_description TEXT,
        status TEXT DEFAULT 'Not Received',
        oem_name TEXT,
        format_file TEXT,
        uploaded_file TEXT,
        remarks TEXT,
        FOREIGN KEY (rfp_id) REFERENCES rfps(id) ON DELETE CASCADE
    )
    ''')

    # Create RFP Uploaded Documents Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS rfp_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rfp_id INTEGER NOT NULL,
        filename TEXT NOT NULL,
        original_name TEXT NOT NULL,
        doc_type TEXT,
        file_size INTEGER,
        uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (rfp_id) REFERENCES rfps(id) ON DELETE CASCADE
    )
    ''')

    # Create RFP Reminders Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS rfp_reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rfp_id INTEGER NOT NULL,
        reminder_date TEXT NOT NULL,
        task_description TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        created_by INTEGER,
        FOREIGN KEY (rfp_id) REFERENCES rfps(id) ON DELETE CASCADE,
        FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
    )
    ''')

    # Create RFP Interactions Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS rfp_interactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rfp_id INTEGER NOT NULL,
        section TEXT NOT NULL, -- 'boq' or 'checklist'
        user_id INTEGER NOT NULL,
        interaction_date TEXT NOT NULL,
        type TEXT NOT NULL,
        summary TEXT NOT NULL,
        next_steps TEXT,
        followup_date TEXT,
        followup_status TEXT DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (rfp_id) REFERENCES rfps(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')
    
    # Add remarks column safety migration block
    try:
        cursor.execute("ALTER TABLE rfp_boq_oem_mappings ADD COLUMN remarks TEXT")
    except sqlite3.OperationalError:
        pass

    # Add rfps columns safety migration block
    for col in [('title', 'TEXT'), ('opportunity_from', 'TEXT'), ('customer_name', 'TEXT'),
                ('opportunity_date', 'TEXT'), ('opportunity_type', 'TEXT'),
                ('source', 'TEXT'), ('opportunity_owner', 'TEXT')]:
        try:
            cursor.execute(f"ALTER TABLE rfps ADD COLUMN {col[0]} {col[1]}")
        except sqlite3.OperationalError:
            pass

    # Add rfp_checklist columns safety migration block
    for col in [('oem_name', 'TEXT'), ('format_file', 'TEXT'), ('uploaded_file', 'TEXT'), ('remarks', 'TEXT')]:
        try:
            cursor.execute(f"ALTER TABLE rfp_checklist ADD COLUMN {col[0]} {col[1]}")
        except sqlite3.OperationalError:
            pass
        
    # Check if admin user exists, if not, create default admin
    cursor.execute('SELECT * FROM users WHERE role = ?', ('admin',))
    admin_exists = cursor.fetchone()
    
    if not admin_exists:
        # Default Admin password is '@Admin#99!Directory'
        hashed_password = generate_password_hash('@Admin#99!Directory')
        cursor.execute('''
        INSERT INTO users (username, email, password_hash, role, status)
        VALUES (?, ?, ?, ?, ?)
        ''', ('admin', 'admin@presales-tracker.local', hashed_password, 'admin', 'approved'))
        
        # Log default admin creation
        cursor.execute('''
        INSERT INTO audit_logs (action, details)
        VALUES (?, ?)
        ''', ('SYSTEM_INITIALIZATION', 'Default administrator account auto-seeded.'))
        
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

if __name__ == '__main__':
    init_db()
