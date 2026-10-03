with open('timesheets.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_create = '''        CREATE TABLE IF NOT EXISTS timesheets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            task TEXT NOT NULL,
            productivity TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )'''

new_create = '''        CREATE TABLE IF NOT EXISTS timesheets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            task TEXT NOT NULL,
            productivity TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )'''

content = content.replace(old_create, new_create)

# Add migration logic to init_db
old_init = '''def init_db(conn):
    cursor = conn.cursor()
    cursor.execute(\'\'\'
        CREATE TABLE IF NOT EXISTS timesheets ('''

new_init = '''def init_db(conn):
    cursor = conn.cursor()
    
    # Run migration if table exists but lacks columns
    try:
        cursor.execute('ALTER TABLE timesheets ADD COLUMN start_time TEXT')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE timesheets ADD COLUMN end_time TEXT')
    except sqlite3.OperationalError:
        pass
        
    cursor.execute(\'\'\'
        CREATE TABLE IF NOT EXISTS timesheets ('''

content = content.replace(old_init, new_init)

with open('timesheets.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Patched timesheets.py')
