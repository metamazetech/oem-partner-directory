import csv
import io
import sqlite3
from flask import Blueprint, render_template, request, flash, redirect, url_for, Response, current_app, session

timesheets_bp = Blueprint('timesheets', __name__)

import database
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        if session.get('role') != 'admin':
            return "Admin access required.", 403
        return f(*args, **kwargs)
    return decorated_function

def get_db():
    return database.get_db_connection()

def init_db(conn):
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
        
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS timesheets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            task TEXT NOT NULL,
            productivity TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

@timesheets_bp.route('/timesheets')
@login_required
def employee_timesheets():
    user_id = session.get('user_id')  # Defaulting to 1 for demonstration
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM timesheets WHERE user_id = ? ORDER BY date DESC', (user_id,))
    timesheets = cursor.fetchall()
    conn.close()
    return render_template('timesheets.html', timesheets=timesheets)

@timesheets_bp.route('/timesheets/add', methods=['POST'])
@login_required
def add_timesheet():
    user_id = session.get('user_id')
    date = request.form.get('date')
    task = request.form.get('task')
    productivity = request.form.get('productivity')
    
    if date and task:
        conn = get_db()
        cursor = conn.cursor()
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        cursor.execute('INSERT INTO timesheets (user_id, date, start_time, end_time, task, productivity) VALUES (?, ?, ?, ?, ?, ?)',
                       (user_id, date, start_time, end_time, task, productivity))
        conn.commit()
        conn.close()
        flash('Timesheet entry added successfully.', 'success')
    else:
        flash('Date and Task are required.', 'danger')
        
    return redirect(url_for('timesheets.employee_timesheets'))

@timesheets_bp.route('/timesheets/export')
@login_required
def export_timesheets():
    user_id = session.get('user_id')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT date, start_time, end_time, task, productivity, created_at FROM timesheets WHERE user_id = ? ORDER BY date DESC', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Start Time', 'End Time', 'Task', 'Productivity', 'Created At'])
    for row in rows:
        writer.writerow(row)
        
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=timesheets.csv"}
    )

@timesheets_bp.route('/timesheets/import', methods=['POST'])
@login_required
def import_timesheets():
    user_id = session.get('user_id')
    file = request.files.get('file')
    if not file:
        flash('No file selected.', 'danger')
        return redirect(url_for('timesheets.employee_timesheets'))
        
    if file.filename.endswith('.csv'):
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.reader(stream)
        next(csv_input, None)  # Skip header
        
        conn = get_db()
        cursor = conn.cursor()
        for row in csv_input:
            if len(row) >= 5:
                date, start_time, end_time, task, productivity = row[0], row[1], row[2], row[3], row[4]
                cursor.execute('INSERT INTO timesheets (user_id, date, start_time, end_time, task, productivity) VALUES (?, ?, ?, ?, ?, ?)',
                               (user_id, date, start_time, end_time, task, productivity))
        conn.commit()
        conn.close()
        flash('Timesheets imported successfully.', 'success')
    else:
        flash('Only CSV files are supported for now.', 'danger')
        
    return redirect(url_for('timesheets.employee_timesheets'))

@timesheets_bp.route('/admin/timesheets')
@admin_required
def admin_timesheets():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM timesheets ORDER BY date DESC, user_id ASC')
    timesheets = cursor.fetchall()
    conn.close()
    return render_template('admin_timesheets.html', timesheets=timesheets)
