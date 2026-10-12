from flask import Blueprint, request, jsonify, render_template, session, send_from_directory
import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import datetime

chat_bp = Blueprint('chat', __name__, template_folder='templates')

UPLOAD_FOLDER = 'uploads/chat'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

import database

def get_db():
    return database.get_db_connection()

def init_db(conn):
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER,
            message TEXT,
            file_path TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

@chat_bp.route('/chat')
def chat_ui():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username FROM users WHERE id != ? ORDER BY username ASC', (user_id,))
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return render_template('chat.html', users=users)

@chat_bp.route('/chat/messages', methods=['GET'])
def get_messages():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify([])
        
    receiver_id = request.args.get('receiver_id')
    
    conn = get_db()
    cursor = conn.cursor()
    
    if receiver_id and receiver_id != 'global':
        # 1-on-1 chat
        cursor.execute('''
            SELECT c.*, u.username as sender_name 
            FROM chat_messages c
            LEFT JOIN users u ON c.sender_id = u.id
            WHERE (c.sender_id = ? AND c.receiver_id = ?) 
               OR (c.sender_id = ? AND c.receiver_id = ?)
            ORDER BY c.timestamp ASC
        ''', (user_id, receiver_id, receiver_id, user_id))
    else:
        # Global room
        cursor.execute('''
            SELECT c.*, u.username as sender_name 
            FROM chat_messages c
            LEFT JOIN users u ON c.sender_id = u.id
            WHERE c.receiver_id IS NULL OR c.receiver_id = ''
            ORDER BY c.timestamp ASC
        ''')
        
    messages = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(messages)

@chat_bp.route('/chat/send', methods=['POST'])
def send_message():
    sender_id = session.get('user_id', 1)
    receiver_id = request.form.get('receiver_id')
    if receiver_id == 'global' or receiver_id == 'null' or receiver_id == '':
        receiver_id = None
    message = request.form.get('message', '')
    
    file_path = None
    if 'file' in request.files:
        file = request.files['file']
        if file.filename != '':
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"{timestamp}_{filename}"
            full_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(full_path)
            file_path = full_path

    if not message and not file_path:
        return jsonify({'error': 'No message or file provided'}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO chat_messages (sender_id, receiver_id, message, file_path)
        VALUES (?, ?, ?, ?)
    ''', (sender_id, receiver_id if receiver_id else None, message, file_path))
    conn.commit()
    
    return jsonify({'success': True})

@chat_bp.route('/chat/admin')
def admin_chat():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.*, s.username as sender_name, r.username as receiver_name 
        FROM chat_messages c
        LEFT JOIN users s ON c.sender_id = s.id
        LEFT JOIN users r ON c.receiver_id = r.id
        ORDER BY c.timestamp DESC
    ''')
    rows = cursor.fetchall()
    conn.close()
    
    # Group by date
    grouped_messages = {}
    for r in rows:
        d = dict(r)
        date_str = d['timestamp'].split(' ')[0] if ' ' in d['timestamp'] else d['timestamp'].split('T')[0] if 'T' in d['timestamp'] else 'Unknown Date'
        if date_str not in grouped_messages:
            grouped_messages[date_str] = []
        grouped_messages[date_str].append(d)
        
    return render_template('admin_chat.html', grouped_messages=grouped_messages)

@chat_bp.route('/chat/download/<path:filename>')
def download_file(filename):
    return send_from_directory(os.path.abspath(UPLOAD_FOLDER), filename)

import io
import csv
from flask import Response

@chat_bp.route('/chat/admin/export')
def export_chat():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.timestamp, s.username as sender_name, r.username as receiver_name, c.message, c.file_path
        FROM chat_messages c
        LEFT JOIN users s ON c.sender_id = s.id
        LEFT JOIN users r ON c.receiver_id = r.id
        ORDER BY c.timestamp ASC
    ''')
    rows = cursor.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Timestamp', 'Sender', 'Receiver', 'Message', 'File Attachment'])
    
    for row in rows:
        rec = row['receiver_name'] or 'Global Team Room'
        writer.writerow([row['timestamp'], row['sender_name'], rec, row['message'], row['file_path']])
        
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=chat_logs.csv"}
    )

@chat_bp.route('/chat/notifications')
def get_notifications():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify([])
    since = request.args.get('since')
    if not since:
        return jsonify([])
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.*, u.username as sender_name 
        FROM chat_messages c 
        LEFT JOIN users u ON c.sender_id = u.id
        WHERE (c.receiver_id = ? OR (c.receiver_id IS NULL OR c.receiver_id = '')) 
        AND c.sender_id != ? 
        AND c.timestamp > ?
        ORDER BY c.timestamp ASC
    ''', (user_id, user_id, since))
    
    msgs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(msgs)
