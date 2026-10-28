import csv
import io
import sqlite3
from flask import Blueprint, render_template, request, flash, redirect, url_for, Response, current_app, session
from datetime import datetime

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
    
    # Run migrations if table exists but lacks columns
    try:
        cursor.execute('ALTER TABLE timesheets ADD COLUMN start_time TEXT')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE timesheets ADD COLUMN end_time TEXT')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE timesheets ADD COLUMN project_title TEXT')
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
            project_title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

def calculate_hours(start, end):
    try:
        fmt = '%H:%M'
        tdelta = datetime.strptime(end, fmt) - datetime.strptime(start, fmt)
        hours = tdelta.total_seconds() / 3600
        return round(hours, 2)
    except:
        return 0

@timesheets_bp.route('/timesheets')
@login_required
def employee_timesheets():
    user_id = session.get('user_id')
    sort = request.args.get('sort', 'project_asc')
    if sort == 'task_asc':
        order_clause = 'task ASC, date DESC'
    elif sort == 'date_desc':
        order_clause = 'date DESC, start_time ASC'
    elif sort == 'date_asc':
        order_clause = 'date ASC, start_time ASC'
    elif sort == 'time_asc':
        order_clause = 'start_time ASC, date DESC'
    else:  # project_asc (A to Z)
        order_clause = 'project_title ASC, date DESC, start_time ASC'

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f'SELECT * FROM timesheets WHERE user_id = ? ORDER BY {order_clause}', (user_id,))
    rows = cursor.fetchall()
    
    cursor.execute('SELECT DISTINCT project_title FROM timesheets WHERE user_id = ? AND project_title IS NOT NULL AND project_title != "" ORDER BY project_title ASC', (user_id,))
    projects = [r['project_title'] for r in cursor.fetchall()]
    conn.close()
    
    timesheets = []
    daily_summary = {}
    for r in rows:
        d = dict(r)
        d['hours_worked'] = calculate_hours(d['start_time'], d['end_time']) if d['start_time'] and d['end_time'] else 0
        timesheets.append(d)
        
        date = d['date']
        if date not in daily_summary:
            daily_summary[date] = {'productive': 0.0, 'break': 0.0, 'last_end': None}
        
        daily_summary[date]['productive'] += d['hours_worked']
        
        # Calculate break time
        if d['start_time'] and daily_summary[date]['last_end']:
            try:
                fmt = '%H:%M'
                tdelta = datetime.strptime(d['start_time'], fmt) - datetime.strptime(daily_summary[date]['last_end'], fmt)
                break_hours = tdelta.total_seconds() / 3600
                if break_hours > 0:
                    daily_summary[date]['break'] += break_hours
            except:
                pass
        
        if d['end_time']:
            daily_summary[date]['last_end'] = d['end_time']
            
    # Round summaries
    for d in daily_summary:
        daily_summary[d]['productive'] = round(daily_summary[d]['productive'], 2)
        daily_summary[d]['break'] = round(daily_summary[d]['break'], 2)

        # Fetch HRMS data
    conn = get_db()
    cursor = conn.cursor()
    today_str = datetime.now().date().isoformat()
    
    try:
        cursor.execute("SELECT * FROM attendance WHERE user_id = ? AND date = ?", (user_id, today_str))
        today_attendance = cursor.fetchone()
        
        cursor.execute("SELECT * FROM leaves WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        my_leaves = cursor.fetchall()
        
        cursor.execute("SELECT value FROM portal_settings WHERE key = 'office_lat'")
        lat_row = cursor.fetchone()
        cursor.execute("SELECT value FROM portal_settings WHERE key = 'office_lng'")
        lng_row = cursor.fetchone()
        cursor.execute("SELECT value FROM portal_settings WHERE key = 'office_radius'")
        rad_row = cursor.fetchone()
        office_lat = float(lat_row['value']) if lat_row else 40.758896
        office_lng = float(lng_row['value']) if lng_row else -73.985130
        try:
            office_radius = int(rad_row['value']) if rad_row and rad_row['value'] else 500
        except:
            office_radius = 500
    except Exception as e:
        today_attendance = None
        my_leaves = []
        office_lat = 40.758896
        office_lng = -73.985130
        office_radius = 500
        
    conn.close()

    return render_template('timesheets.html', timesheets=timesheets, projects=projects, daily_summary=daily_summary,
                           today_attendance=today_attendance, my_leaves=my_leaves, 
                           office_lat=office_lat, office_lng=office_lng, max_dist=office_radius)

@timesheets_bp.route('/timesheets/add', methods=['POST'])
@login_required
def add_timesheet():
    user_id = session.get('user_id')
    date = (request.form.get('date') or '').strip()
    task = (request.form.get('task') or '').strip()
    
    project_title = (request.form.get('project_title') or '').strip()
    if project_title == '__NEW__':
        project_title = (request.form.get('new_project_title') or '').strip()
        
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
    if not task and project_title:
        task = project_title
    if not project_title and task:
        project_title = task
    if not task:
        task = 'General Task'
    if not project_title:
        project_title = 'General'
        
    conn = get_db()
    cursor = conn.cursor()
    start_time = (request.form.get('start_time') or '').strip()
    end_time = (request.form.get('end_time') or '').strip()
    cursor.execute('INSERT INTO timesheets (user_id, date, start_time, end_time, task, project_title) VALUES (?, ?, ?, ?, ?, ?)',
                   (user_id, date, start_time, end_time, task, project_title))
    conn.commit()
    conn.close()
    flash('Timesheet entry added successfully.', 'success')
        
    return redirect(url_for('timesheets.employee_timesheets'))

@timesheets_bp.route('/timesheets/export')
@login_required
def export_timesheets():
    is_admin_export = request.args.get('admin') == 'true'
    user_id = session.get('user_id')
    conn = get_db()
    cursor = conn.cursor()
    
    if is_admin_export and session.get('role') == 'admin':
        cursor.execute('''
            SELECT t.date, t.start_time, t.end_time, t.project_title, t.task, u.username, t.created_at 
            FROM timesheets t 
            LEFT JOIN users u ON t.user_id = u.id 
            ORDER BY t.date DESC
        ''')
        rows = cursor.fetchall()
        conn.close()
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['User', 'Date', 'Start Time', 'End Time', 'Project Title', 'Task', 'Created At'])
        for row in rows:
            writer.writerow([row['username'], row['date'], row['start_time'], row['end_time'], row['project_title'], row['task'], row['created_at']])
            
        filename = "master_timesheets.csv"
    else:
        cursor.execute('SELECT date, start_time, end_time, project_title, task, created_at FROM timesheets WHERE user_id = ? ORDER BY date DESC', (user_id,))
        rows = cursor.fetchall()
        conn.close()
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Date', 'Start Time', 'End Time', 'Project Title', 'Task', 'Created At'])
        for row in rows:
            writer.writerow(row)
            
        filename = "my_timesheets.csv"
        
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename}"}
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
            if len(row) >= 5: # basic validation
                date, start_time, end_time = row[0], row[1], row[2]
                project_title = row[3] if len(row) > 5 else ''
                task = row[4] if len(row) > 5 else row[3]
                cursor.execute('INSERT INTO timesheets (user_id, date, start_time, end_time, project_title, task) VALUES (?, ?, ?, ?, ?, ?)',
                               (user_id, date, start_time, end_time, project_title, task))
        conn.commit()
        conn.close()
        flash('Timesheets imported successfully.', 'success')
    else:
        flash('Only CSV files are supported for now.', 'danger')
        
    return redirect(url_for('timesheets.employee_timesheets'))



@timesheets_bp.route('/timesheets/edit', methods=['POST'])
@timesheets_bp.route('/timesheets/edit/<int:entry_id>', methods=['GET', 'POST'])
@timesheets_bp.route('/timesheet/edit/<int:entry_id>', methods=['GET', 'POST'])
@login_required
def edit_timesheet(entry_id=None):
    if request.method == 'GET':
        return redirect(url_for('timesheets.employee_timesheets'))
        
    if entry_id is None:
        raw_id = request.form.get('id') or request.form.get('entry_id')
        if not raw_id:
            flash('Invalid or missing timesheet entry ID.', 'error')
            return redirect(url_for('timesheets.employee_timesheets'))
        try:
            entry_id = int(raw_id)
        except ValueError:
            flash('Invalid timesheet ID format.', 'error')
            return redirect(url_for('timesheets.employee_timesheets'))

    user_id = session.get('user_id')
    is_admin = session.get('role') == 'admin'
    date = (request.form.get('date') or '').strip()
    task = (request.form.get('task') or '').strip()
    project_title = (request.form.get('project_title') or '').strip()
    start_time = (request.form.get('start_time') or '').strip()
    end_time = (request.form.get('end_time') or '').strip()
    
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
    if not task and project_title:
        task = project_title
    if not project_title and task:
        project_title = task
    if not task:
        task = 'General Task'
    if not project_title:
        project_title = 'General'
        
    conn = get_db()
    cursor = conn.cursor()
    if is_admin:
        cursor.execute('''
            UPDATE timesheets 
            SET date = ?, start_time = ?, end_time = ?, project_title = ?, task = ? 
            WHERE id = ?
        ''', (date, start_time, end_time, project_title, task, entry_id))
    else:
        cursor.execute('''
            UPDATE timesheets 
            SET date = ?, start_time = ?, end_time = ?, project_title = ?, task = ? 
            WHERE id = ? AND user_id = ?
        ''', (date, start_time, end_time, project_title, task, entry_id, user_id))
    conn.commit()
    conn.close()
    flash('Timesheet entry updated successfully.', 'success')
    return redirect(url_for('timesheets.employee_timesheets'))

@timesheets_bp.route('/timesheets/delete/<int:entry_id>', methods=['POST'])
@login_required
def delete_timesheet(entry_id):
    user_id = session.get('user_id')
    is_admin = session.get('role') == 'admin'
    conn = get_db()
    cursor = conn.cursor()
    if is_admin:
        cursor.execute('DELETE FROM timesheets WHERE id = ?', (entry_id,))
    else:
        cursor.execute('DELETE FROM timesheets WHERE id = ? AND user_id = ?', (entry_id, user_id))
    conn.commit()
    conn.close()
    flash('Timesheet entry deleted.', 'success')
    return redirect(url_for('timesheets.employee_timesheets'))
