import sqlite3
conn = sqlite3.connect('oem_tracker.db')
conn.execute("INSERT OR IGNORE INTO portal_settings (key, value) VALUES ('session_timeout_minutes', '600')")
conn.commit()
conn.close()
print("Updated DB with session_timeout_minutes")
