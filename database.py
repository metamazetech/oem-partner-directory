import os
import sqlite3
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'oem_tracker.db')

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
    
    # Check if admin user exists, if not, create default admin
    cursor.execute('SELECT * FROM users WHERE role = ?', ('admin',))
    admin_exists = cursor.fetchone()
    
    if not admin_exists:
        # Default Admin password is 'admin123'
        hashed_password = generate_password_hash('admin123')
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
