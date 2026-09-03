import sqlite3
try:
    conn = sqlite3.connect('oem_tracker.db')
    conn.row_factory = sqlite3.Row
    val = conn.execute("SELECT value FROM portal_settings WHERE key = 'session_timeout_minutes'").fetchone()
    print('Timeout from DB:', dict(val) if val else None)
except Exception as e:
    print('Error:', e)
