import sqlite3
import os

DB_PATH = 'oem_tracker.db'

tables_to_drop = [
    'project_activity_log',
    'project_reminders',
    'project_discussions',
    'project_files',
    'project_expenses',
    'task_timers',
    'task_comments',
    'task_checklists',
    'task_followers',
    'task_assignees',
    'tasks',
    'milestones',
    'projects',
    'invoices'
]

def drop_tables():
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        for table in tables_to_drop:
            cur.execute(f"DROP TABLE IF EXISTS {table}")
        conn.commit()
        print("Dropped PM tables successfully.")
    except Exception as e:
        print("Error dropping tables:", e)
    finally:
        conn.close()

if __name__ == '__main__':
    drop_tables()
