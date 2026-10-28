import sqlite3
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, Response, current_app
from datetime import datetime, date
import csv
import io
import math
import database

hrms = Blueprint('hrms', __name__)

MAX_DISTANCE_METERS = 100

def get_db_connection():
    return database.get_db_connection()

def get_office_location(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM portal_settings WHERE key = 'office_lat'")
    lat_row = cursor.fetchone()
    cursor.execute("SELECT value FROM portal_settings WHERE key = 'office_lng'")
    lng_row = cursor.fetchone()
    
    lat = float(lat_row['value']) if lat_row else 40.758896
    lng = float(lng_row['value']) if lng_row else -73.985130
    return lat, lng

def get_office_radius(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM portal_settings WHERE key = 'office_radius'")
    row = cursor.fetchone()
    try:
        return int(row['value']) if row and row['value'] else 500
    except:
        return 500

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # radius of Earth in meters
    phi_1 = math.radians(lat1)
    phi_2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi_1) * math.cos(phi_2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def init_db(conn):
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            punch_in TEXT,
            punch_out TEXT,
            location_lat REAL,
            location_lng REAL,
            status TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leaves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            reason TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL
        )
    ''')
    conn.commit()

@hrms.route('/attendance', methods=['GET', 'POST'])
def attendance_dashboard():
    if 'user_id' not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    conn = get_db_connection()
    today_str = date.today().isoformat()
    office_lat, office_lng = get_office_location(conn)
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'punch':
            lat = request.form.get('lat', type=float)
            lng = request.form.get('lng', type=float)
            if lat is None or lng is None:
                flash("Location not provided. Please enable GPS.", "danger")
            else:
                max_dist = get_office_radius(conn)
                dist = haversine(office_lat, office_lng, lat, lng)
                if dist > max_dist:
                    flash(f"You are {int(dist)}m away. Must be within {max_dist}m to punch.", "danger")
                else:
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM attendance WHERE user_id = ? AND date = ?", (user_id, today_str))
                    record = cursor.fetchone()
                    now_str = datetime.now().strftime('%H:%M:%S')
                    
                    if not record:
                        cursor.execute("INSERT INTO attendance (user_id, date, punch_in, location_lat, location_lng, status) VALUES (?, ?, ?, ?, ?, ?)",
                                       (user_id, today_str, now_str, lat, lng, "Present"))
                        flash("Punched IN successfully.", "success")
                    elif not record['punch_out']:
                        cursor.execute("UPDATE attendance SET punch_out = ? WHERE id = ?", (now_str, record['id']))
                        flash("Punched OUT successfully.", "success")
                    else:
                        flash("Already punched out for today.", "info")
                    conn.commit()
                    
        elif action == 'leave':
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            reason = request.form.get('reason')
            if start_date and end_date and reason:
                created_at = datetime.now().isoformat()
                conn.execute("INSERT INTO leaves (user_id, start_date, end_date, reason, created_at) VALUES (?, ?, ?, ?, ?)",
                             (user_id, start_date, end_date, reason, created_at))
                conn.commit()
                flash("Leave requested successfully.", "success")
            else:
                flash("All fields are required for leave request.", "danger")
                
        return redirect(url_for('timesheets.employee_timesheets'))
        
    # GET method
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM attendance WHERE user_id = ? AND date = ?", (user_id, today_str))
    today_attendance = cursor.fetchone()
    
    cursor.execute("SELECT * FROM attendance WHERE user_id = ? ORDER BY date DESC LIMIT 30", (user_id,))
    recent_attendance = cursor.fetchall()
    
    cursor.execute("SELECT * FROM leaves WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    my_leaves = cursor.fetchall()
    
    office_radius = get_office_radius(conn)
    conn.close()
    
    return render_template('attendance.html', 
                           today_attendance=today_attendance, 
                           recent_attendance=recent_attendance,
                           my_leaves=my_leaves,
                           office_lat=office_lat,
                           office_lng=office_lng,
                           max_dist=office_radius)


@hrms.route('/admin/attendance', methods=['GET', 'POST'])
def admin_attendance():
    if session.get('role') != 'admin':
        flash("Admin access required.", "danger")
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action in ('approve', 'deny'):
            leave_id = request.form.get('leave_id')
            status = 'approved' if action == 'approve' else 'denied'
            conn.execute("UPDATE leaves SET status = ? WHERE id = ?", (status, leave_id))
            conn.commit()
            flash(f"Leave {status}.", "success")
        elif action == 'update_location':
            lat = request.form.get('office_lat')
            lng = request.form.get('office_lng')
            radius = request.form.get('office_radius', '500')
            if lat and lng:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM portal_settings WHERE key = 'office_lat'")
                if cursor.fetchone():
                    cursor.execute("UPDATE portal_settings SET value = ? WHERE key = 'office_lat'", (lat,))
                else:
                    cursor.execute("INSERT INTO portal_settings (key, value) VALUES ('office_lat', ?)", (lat,))
                    
                cursor.execute("SELECT id FROM portal_settings WHERE key = 'office_lng'")
                if cursor.fetchone():
                    cursor.execute("UPDATE portal_settings SET value = ? WHERE key = 'office_lng'", (lng,))
                else:
                    cursor.execute("INSERT INTO portal_settings (key, value) VALUES ('office_lng', ?)", (lng,))

                cursor.execute("SELECT id FROM portal_settings WHERE key = 'office_radius'")
                if cursor.fetchone():
                    cursor.execute("UPDATE portal_settings SET value = ? WHERE key = 'office_radius'", (radius,))
                else:
                    cursor.execute("INSERT INTO portal_settings (key, value) VALUES ('office_radius', ?)", (radius,))
                conn.commit()
                flash("Office location & geofence radius updated successfully.", "success")
                
        elif action == 'download_csv':
            cursor = conn.cursor()
            cursor.execute("SELECT a.id, u.username, a.date, a.punch_in, a.punch_out, a.status FROM attendance a LEFT JOIN users u ON a.user_id = u.id")
            records = cursor.fetchall()
            
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['ID', 'Username', 'Date', 'Punch In', 'Punch Out', 'Status'])
            for row in records:
                writer.writerow([row['id'], row['username'], row['date'], row['punch_in'], row['punch_out'], row['status']])
            
            response = Response(output.getvalue(), mimetype="text/csv")
            response.headers["Content-Disposition"] = "attachment; filename=attendance_report.csv"
            return response
            
        return redirect(url_for('hrms.admin_attendance'))
        
    # GET method
    cursor = conn.cursor()
    cursor.execute("SELECT l.id, u.username, l.start_date, l.end_date, l.reason, l.status, l.created_at FROM leaves l LEFT JOIN users u ON l.user_id = u.id ORDER BY l.created_at DESC")
    all_leaves = cursor.fetchall()
    
    cursor.execute("SELECT a.id, u.username, a.date, a.punch_in, a.punch_out, a.status FROM attendance a LEFT JOIN users u ON a.user_id = u.id ORDER BY a.date DESC LIMIT 100")
    all_attendance = cursor.fetchall()
    
    office_lat, office_lng = get_office_location(conn)
    office_radius = get_office_radius(conn)
    
    conn.close()
    
    return render_template('admin_attendance.html', 
                           all_leaves=all_leaves, 
                           all_attendance=all_attendance,
                           office_lat=office_lat,
                           office_lng=office_lng,
                           office_radius=office_radius)
