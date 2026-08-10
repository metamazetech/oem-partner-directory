import os
import json
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

# Import local database operations
import database
from scraper import scrape_oem_website

app = Flask(__name__)
app.secret_key = 'presales_oem_distributor_tracker_secret_key_1928'

# Global sync state for non-blocking asynchronous master refresh
import threading
master_sync_lock = threading.Lock()
master_sync_in_progress = False

@app.template_filter('from_json')
def from_json(s):
    if not s:
        return []
    try:
        return json.loads(s)
    except Exception:
        return []

@app.template_filter('to_digits')
def to_digits(s):
    if not s:
        return ""
    # Extract only digits and if it's a mobile number (e.g. starts with +91 or 91), strip leading zeros
    digits = "".join(c for c in s if c.isdigit())
    # If it's a local number without country code, you might want to allow it, but wa.me requires country code.
    # We will just yield all digits.
    return digits

# Configuration for visiting card uploads
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 40 * 1024 * 1024 # 40MB limit

@app.errorhandler(413)
def request_entity_too_large(error):
    flash("File size exceeds 40 MB limit.", "error")
    return redirect(request.referrer or url_for('rfps_list'))

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def download_company_logo(website, contact_id, company_name=None):
    import urllib.request
    from urllib.parse import urlparse
    import socket
    
    domain = None
    if website:
        try:
            url = website.strip().lower()
            if not url.startswith('http://') and not url.startswith('https://'):
                url = 'https://' + url
            parsed = urlparse(url)
            domain = parsed.netloc
            if domain.startswith('www.'):
                domain = domain[4:]
        except Exception:
            pass
            
    # Guess domain from company_name if domain is still empty/invalid
    if not domain and company_name:
        # Strip common suffixes and spaces
        clean_name = company_name.strip().lower()
        clean_name = "".join(c for c in clean_name if c.isalnum() or c in ['-'])
        
        # strip common endings
        for suffix in ['ltd', 'inc', 'corp', 'limited', 'systems', 'india', 'tech', 'technologies', 'group', 'solutions']:
            if clean_name.endswith(suffix):
                clean_name = clean_name[:-len(suffix)].strip('-')
        
        if clean_name:
            domain = clean_name + ".com"

    if not domain:
        return None
        
    filename = f"logo_{contact_id}.png"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    # List of public logo/favicon API services
    sources = [
        f"https://logo.clearbit.com/{domain}",
        f"https://www.google.com/s2/favicons?sz=128&domain={domain}",
        f"https://icons.duckduckgo.com/ip3/{domain}.ico"
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    # Try sequentially
    import requests
    for logo_url in sources:
        try:
            response = requests.get(logo_url, headers=headers, timeout=5, verify=False)
            if response.status_code == 200 and len(response.content) > 150:
                with open(filepath, 'wb') as out_file:
                    out_file.write(response.content)
                return filename
        except Exception as e:
            print(f"Requests failed to fetch logo from {logo_url}: {e}")
            
        try:
            import ssl
            context = ssl._create_unverified_context()
            req = urllib.request.Request(logo_url, headers=headers)
            with urllib.request.urlopen(req, timeout=4, context=context) as urllib_resp:
                content = urllib_resp.read()
                if urllib_resp.status == 200 and len(content) > 150:
                    with open(filepath, 'wb') as out_file:
                        out_file.write(content)
                    return filename
        except Exception as e2:
            print(f"Urllib fallback failed to fetch logo from {logo_url}: {e2}")
            
    return None

# Helper decorator/checker to verify login
def is_logged_in():
    return 'user_id' in session

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            flash('Please log in first.', 'error')
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Access denied. Administrator privileges required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Log system actions to audit trail
def log_audit(action, details, user_id=None):
    if user_id is None:
        try:
            user_id = session.get('user_id')
        except RuntimeError:
            user_id = None
            
    conn = database.get_db_connection()
    conn.execute('''
    INSERT INTO audit_logs (user_id, action, details)
    VALUES (?, ?, ?)
    ''', (user_id, action, details))
    conn.commit()
    conn.close()

# Template context processor to inject dynamic OEM groups & portal settings in all pages
@app.context_processor
def inject_global_data():
    conn = database.get_db_connection()
    groups = conn.execute('SELECT * FROM oem_groups ORDER BY name ASC').fetchall()
    settings_rows = conn.execute('SELECT key, value FROM portal_settings').fetchall()
    
    settings = {row['key']: row['value'] for row in settings_rows}
    settings.setdefault('portal_name', 'OEM Directory')
    settings.setdefault('portal_logo', '')
    settings.setdefault('favicon', '')
    
    # Safety fallback: clear database setting if brand image file is missing on disk
    upload_folder = app.config.get('UPLOAD_FOLDER')
    db_changed = False
    
    for key in ('portal_logo', 'favicon'):
        val = settings.get(key)
        if val:
            file_path = os.path.join(upload_folder, val)
            if not os.path.exists(file_path):
                settings[key] = ''
                conn.execute('DELETE FROM portal_settings WHERE key = ?', (key,))
                db_changed = True
                
    if db_changed:
        conn.commit()
        
    conn.close()
    return dict(oem_groups=groups, portal_settings=settings)


# Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_logged_in():
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        
        conn = database.get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            if user['status'] == 'pending':
                flash('Your account registration is pending admin approval.', 'error')
                return redirect(url_for('login'))
            elif user['status'] == 'rejected':
                flash('Your account registration has been rejected. Contact admin.', 'error')
                return redirect(url_for('login'))
                
            # Log session details
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['theme'] = user['theme'] or 'theme-slate-dark'
            session['dashboard_layout'] = user['dashboard_layout'] or '{}'
            
            # Write audit log
            log_audit('USER_LOGIN', f"User {username} successfully logged in.")
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')
            
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username'].strip()
    email = request.form['email'].strip()
    password = request.form['password']
    role = 'viewer' # Force all user registration requests to view-only (viewer) by default
    
    if not username or not email or not password:
        flash('All fields are required.', 'error')
        return redirect(url_for('login'))
        
    strong, pwd_err = is_password_strong(password)
    if not strong:
        flash(pwd_err, 'error')
        return redirect(url_for('login'))
        
    conn = database.get_db_connection()
    # Check if username or email exists
    existing = conn.execute('SELECT * FROM users WHERE username = ? OR email = ?', (username, email)).fetchone()
    if existing:
        conn.close()
        flash('Username or Email already registered.', 'error')
        return redirect(url_for('login'))
        
    hashed_pwd = generate_password_hash(password)
    # New registers default to 'pending' approval
    conn.execute('''
    INSERT INTO users (username, email, password_hash, role, status)
    VALUES (?, ?, ?, ?, 'pending')
    ''', (username, email, hashed_pwd, role))
    conn.commit()
    conn.close()
    
    # Log registration request
    conn = database.get_db_connection()
    conn.execute('''
    INSERT INTO audit_logs (action, details)
    VALUES ('USER_REGISTRATION_REQUEST', ?)
    ''', (f"New user registration request: {username} ({role})",))
    conn.commit()
    conn.close()
    
    flash('Registration request submitted! Please notify your administrator to approve your account.', 'success')
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    try:
        if is_logged_in() and 'username' in session:
            log_audit('USER_LOGOUT', f"User {session.get('username')} logged out.")
    except Exception as e:
        print(f"Error logging logout: {e}")
    session.clear()
    return redirect(url_for('login'))

@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    email = request.form.get('email', '').strip()
    
    # Query matching user record
    conn = database.get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    
    if not user:
        # Prevent username enumeration
        flash('If the email is registered on our directory, password recovery details have been sent.', 'success')
        return redirect(url_for('login'))
        
    # Query email connection configurations from database
    conn = database.get_db_connection()
    email_settings = conn.execute("SELECT key, value FROM portal_settings WHERE key LIKE 'email_%'").fetchall()
    portal_name_row = conn.execute("SELECT value FROM portal_settings WHERE key = 'portal_name'").fetchone()
    conn.close()
    
    portal_name = portal_name_row['value'] if portal_name_row else 'OEM Directory'
    settings = {r['key']: r['value'] for r in email_settings}
    
    server = settings.get('email_server')
    port = settings.get('email_port', '465')
    ssl_enc = settings.get('email_ssl', 'true')
    username = settings.get('email_username')
    password = settings.get('email_password')
    protocol = settings.get('email_service_type', 'smtp')
    
    if not server:
        # Log request and warn about missing email server configuration
        log_audit('PASSWORD_RESET_REQUEST', f"User {user['username']} ({email}) requested password reset. Recovery mail not sent (server not configured).")
        flash("Password recovery request submitted successfully. (Alert email pending administrator connectivity setup).", 'success')
        return redirect(url_for('login'))
        
    # Generate new temporary password
    import secrets
    import string
    temp_pwd = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
    
    # Attempt actual email dispatch
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    try:
        msg = MIMEMultipart()
        msg['From'] = username if username else 'it@metamaze.co.in'
        msg['To'] = email
        msg['Subject'] = f"{portal_name} - Password Recovery Details"
        
        body = f"""Dear User,

A password reset request was received for your account on the {portal_name}.

Your temporary password is: {temp_pwd}

Please log in using your username '{user['username']}' and this temporary password, then change your password inside your personalization preferences page immediately.

Best regards,
{portal_name} Support Team
"""
        msg.attach(MIMEText(body, 'plain'))
        
        if app.config.get('TESTING'):
            # Bypass socket connections during automated unit tests
            pass
        else:
            port_val = int(port) if port else 465
            if ssl_enc == 'true' or port_val == 465:
                smtp = smtplib.SMTP_SSL(server, port_val, timeout=10)
            else:
                smtp = smtplib.SMTP(server, port_val, timeout=10)
                try:
                    smtp.starttls()
                except Exception:
                    pass
                    
            if username and password:
                smtp.login(username, password)
                
            smtp.sendmail(msg['From'], [email], msg.as_string())
            smtp.quit()
        
        # Update user record in database with new temporary password
        hashed = generate_password_hash(temp_pwd)
        conn = database.get_db_connection()
        conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (hashed, user['id']))
        conn.commit()
        conn.close()
        
        log_audit('PASSWORD_RESET_REQUEST', f"Dispatched temporary password reset credentials to {email} via SMTP ({server})")
        flash("Password recovery details sent to your email address.", 'success')
        
    except Exception as e:
        log_audit('PASSWORD_RESET_FAILURE', f"Failed to dispatch recovery email to {email}: {e}")
        flash(f"⚠️ Mail Server Connection Error: {e}. Please contact your administrator.", "danger")
        
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    # Lazy-cron nightly automated news sync check (once per calendar day)
    try:
        import datetime
        import threading
        conn = database.get_db_connection()
        last_fetch_row = conn.execute("SELECT value FROM portal_settings WHERE key = 'last_news_fetch'").fetchone()
        today_str = datetime.date.today().strftime('%Y-%m-%d')
        
        needs_fetch = False
        if not last_fetch_row:
            needs_fetch = True
        else:
            if last_fetch_row['value'] != today_str:
                needs_fetch = True
                
        if needs_fetch:
            conn.execute("INSERT OR REPLACE INTO portal_settings (key, value) VALUES ('last_news_fetch', ?)", (today_str,))
            conn.commit()
            
            # Kick off news fetch background thread
            t = threading.Thread(target=run_oem_news_fetch_thread, args=(session.get('user_id'), session.get('username')))
            t.daemon = True
            t.start()
    except Exception as e:
        print(f"Error checking daily automated news sync: {e}")
    finally:
        try: conn.close()
        except: pass

    conn = database.get_db_connection()
    
    # Fetch user's role and group permissions
    user = conn.execute('SELECT role, allowed_groups FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    role = user['role'] if user else 'viewer'
    allowed_groups = user['allowed_groups'] if user else 'All'
    
    # Fetch all partners with creator names
    all_contacts = conn.execute('''
        SELECT c.*, u.username as created_by_name 
        FROM contacts c 
        LEFT JOIN users u ON c.created_by = u.id 
        ORDER BY c.company_name ASC
    ''').fetchall()
    
    # Filter contacts by allowed groups
    contacts_rows = []
    if allowed_groups.lower() != 'all':
        groups_list = [g.strip().lower() for g in allowed_groups.split(',')]
        for c in all_contacts:
            g = (c['group_name'] or '').strip().lower()
            if g in groups_list:
                contacts_rows.append(c)
    else:
        contacts_rows = list(all_contacts)
        
    # Compute directory statistics
    total = len(contacts_rows)
    oems = sum(1 for c in contacts_rows if c['type'] == 'OEM')
    distributors = sum(1 for c in contacts_rows if c['type'] == 'Distributor')
    
    # Fetch pending follow-up task reminders
    all_reminders = conn.execute('''
        SELECT i.id, i.followup_date, i.next_steps as task, c.company_name, c.group_name, c.id as contact_id, u.username as assigned_to
        FROM interactions i
        JOIN contacts c ON i.contact_id = c.id
        JOIN users u ON i.user_id = u.id
        WHERE i.followup_date IS NOT NULL AND i.followup_date != '' AND i.followup_status = 'pending'
        ORDER BY i.followup_date ASC
    ''').fetchall()
    
    # Filter reminders by allowed groups
    if allowed_groups.lower() != 'all':
        groups_list = [g.strip().lower() for g in allowed_groups.split(',')]
        reminders = [r for r in all_reminders if (r['group_name'] or '').strip().lower() in groups_list]
    else:
        reminders = list(all_reminders)
        
    # Total interactions count (for stats bar)
    interactions_count = conn.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
    
    # Query pending RFP reminders & RFP interaction follow-up tasks
    rfp_reminders = conn.execute('''
        SELECT r.id, r.reminder_date, r.task_description, r.status, f.rfp_number, f.id as rfp_id, 'manual_reminder' as source
        FROM rfp_reminders r
        JOIN rfps f ON r.rfp_id = f.id
        WHERE r.status = 'pending'
        UNION ALL
        SELECT i.id, i.followup_date as reminder_date, ('[' || UPPER(i.section) || '] ' || i.next_steps) as task_description, i.followup_status as status, f.rfp_number, f.id as rfp_id, 'interaction_followup' as source
        FROM rfp_interactions i
        JOIN rfps f ON i.rfp_id = f.id
        WHERE i.followup_status = 'pending' AND i.followup_date IS NOT NULL AND i.followup_date != ''
        ORDER BY reminder_date ASC
    ''').fetchall()
    
    conn.close()
    
    stats = {
        'total': total,
        'oems': oems,
        'distributors': distributors,
        'interactions': interactions_count
    }
    
    # Get current date ISO string for overdue calculations
    from datetime import date
    today_str = date.today().isoformat()
    
    return render_template('dashboard.html', contacts=contacts_rows, stats=stats, reminders=reminders, rfp_reminders=rfp_reminders, today_str=today_str, user_role=role)

@app.route('/contact/add', methods=['POST'])
@login_required
def add_contact():
    if session.get('role') == 'viewer':
        flash('Access Denied: View-only users cannot add partners.', 'error')
        return redirect(url_for('dashboard'))
        
    company_name = request.form['company_name'].strip()
    type_ = request.form['type']
    group_name = request.form.get('group_name', '').strip()
    website = request.form.get('website', '').strip()
    address = request.form.get('address', '').strip()
    
    # Handle multiple contact persons
    names = request.form.getlist('contact_name[]')
    designations = request.form.getlist('contact_designation[]')
    emails = request.form.getlist('contact_email[]')
    phones = request.form.getlist('contact_phone[]')
    
    contacts_list = []
    for n, d, e, p in zip(names, designations, emails, phones):
        n_str = n.strip()
        if n_str:
            contacts_list.append({
                "name": n_str,
                "designation": d.strip(),
                "email": e.strip(),
                "phone": p.strip()
            })
            
    if not contacts_list:
        # Fallback to single primary name field if submitted
        primary_name = request.form.get('name', '').strip()
        if primary_name:
            contacts_list.append({
                "name": primary_name,
                "designation": request.form.get('designation', '').strip(),
                "email": request.form.get('email', '').strip(),
                "phone": request.form.get('phone', '').strip()
            })
            
    if not company_name or not contacts_list:
        flash('Company Name and at least one Contact Person are required.', 'error')
        return redirect(url_for('dashboard'))
        
    primary_contact = contacts_list[0]
    
    # Process optional visiting card image uploads
    visiting_card_front = None
    visiting_card_back = None
    
    # Generate unique suffix to avoid file collisions
    file_prefix = uuid.uuid4().hex[:10]
    
    if 'visiting_card_front' in request.files:
        file = request.files['visiting_card_front']
        if file and file.filename != '' and allowed_file(file.filename):
            filename = f"front_{file_prefix}_{secure_filename(file.filename)}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            visiting_card_front = filename
            
    if 'visiting_card_back' in request.files:
        file = request.files['visiting_card_back']
        if file and file.filename != '' and allowed_file(file.filename):
            filename = f"back_{file_prefix}_{secure_filename(file.filename)}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            visiting_card_back = filename
            
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO contacts (company_name, name, type, group_name, designation, email, phone, website, address, visiting_card_front, visiting_card_back, contact_persons, created_by)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        company_name, 
        primary_contact["name"], 
        type_, 
        group_name,
        primary_contact["designation"], 
        primary_contact["email"], 
        primary_contact["phone"], 
        website, 
        address, 
        visiting_card_front,
        visiting_card_back,
        json.dumps(contacts_list), 
        session['user_id']
    ))
    contact_id = cursor.lastrowid
    
    # Try fetching company logo from Clearbit
    logo_filename = download_company_logo(website, contact_id, company_name)
    if logo_filename:
        cursor.execute("UPDATE contacts SET company_logo = ? WHERE id = ?", (logo_filename, contact_id))
        
    conn.commit()
    conn.close()
    
    log_audit('CONTACT_ADD', f"Added contact: {company_name} (ID: {contact_id})")
    flash(f"Vendor partner '{company_name}' successfully added.", 'success')
    return redirect(url_for('contact_detail', contact_id=contact_id))

@app.route('/contact/<int:contact_id>')
@login_required
def contact_detail(contact_id):
    conn = database.get_db_connection()
    contact = conn.execute('SELECT * FROM contacts WHERE id = ?', (contact_id,)).fetchone()
    
    if not contact:
        conn.close()
        flash('Contact not found.', 'error')
        return redirect(url_for('dashboard'))
        
    # Fetch relationship interaction history
    interactions = conn.execute('''
        SELECT i.*, u.username 
        FROM interactions i 
        JOIN users u ON i.user_id = u.id 
        WHERE i.contact_id = ? 
        ORDER BY i.interaction_date DESC, i.id DESC
    ''', (contact_id,)).fetchall()
    
    conn.close()
    
    # Parse JSON portfolios
    fetched_products = json.loads(contact['fetched_products']) if contact['fetched_products'] else []
    fetched_services = json.loads(contact['fetched_services']) if contact['fetched_services'] else []
    custom_products = json.loads(contact['custom_products']) if contact['custom_products'] else []
    custom_services = json.loads(contact['custom_services']) if contact['custom_services'] else []
    
    # Load multiple contact persons
    try:
        contact_persons = json.loads(contact['contact_persons']) if contact['contact_persons'] else []
    except Exception:
        contact_persons = []
        
    if not contact_persons:
        contact_persons = [{
            "name": contact['name'] or "",
            "designation": contact['designation'] or "",
            "email": contact['email'] or "",
            "phone": contact['phone'] or ""
        }]
        
    return render_template(
        'contact_detail.html', 
        contact=contact, 
        interactions=interactions,
        fetched_products=fetched_products,
        fetched_services=fetched_services,
        custom_products=custom_products,
        custom_services=custom_services,
        contact_persons=contact_persons
    )

@app.route('/contact/<int:contact_id>/edit', methods=['POST'])
@login_required
def edit_contact(contact_id):
    if session.get('role') == 'viewer':
        flash('Access Denied: View-only users cannot edit details.', 'error')
        return redirect(url_for('contact_detail', contact_id=contact_id))
        
    company_name = request.form['company_name'].strip()
    type_ = request.form['type']
    group_name = request.form.get('group_name', '').strip()
    website = request.form.get('website', '').strip()
    address = request.form.get('address', '').strip()
    
    # Handle multiple contact persons
    names = request.form.getlist('contact_name[]')
    designations = request.form.getlist('contact_designation[]')
    emails = request.form.getlist('contact_email[]')
    phones = request.form.getlist('contact_phone[]')
    
    contacts_list = []
    for n, d, e, p in zip(names, designations, emails, phones):
        n_str = n.strip()
        if n_str:
            contacts_list.append({
                "name": n_str,
                "designation": d.strip(),
                "email": e.strip(),
                "phone": p.strip()
            })
            
    if not contacts_list:
        primary_name = request.form.get('name', '').strip()
        if primary_name:
            contacts_list.append({
                "name": primary_name,
                "designation": request.form.get('designation', '').strip(),
                "email": request.form.get('email', '').strip(),
                "phone": request.form.get('phone', '').strip()
            })
            
    if not company_name or not contacts_list:
        flash('Company Name and at least one Contact Person are required.', 'error')
        return redirect(url_for('contact_detail', contact_id=contact_id))
        
    primary_contact = contacts_list[0]
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE contacts 
    SET company_name = ?, name = ?, type = ?, group_name = ?, designation = ?, email = ?, phone = ?, website = ?, address = ?, contact_persons = ?, updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    ''', (company_name, primary_contact["name"], type_, group_name, primary_contact["designation"], primary_contact["email"], primary_contact["phone"], website, address, json.dumps(contacts_list), contact_id))
    
    # Try fetching company logo on edit
    logo_filename = download_company_logo(website, contact_id, company_name)
    if logo_filename:
        cursor.execute("UPDATE contacts SET company_logo = ? WHERE id = ?", (logo_filename, contact_id))
        
    conn.commit()
    conn.close()
    
    log_audit('CONTACT_EDIT', f"Edited details for contact ID: {contact_id}")
    flash('Partner profile updated successfully.', 'success')
    return redirect(url_for('contact_detail', contact_id=contact_id))

@app.route('/contact/<int:contact_id>/delete', methods=['POST'])
@login_required
def delete_contact(contact_id):
    if session.get('role') != 'admin':
        flash('Access Denied: Only administrators can delete partners.', 'error')
        return redirect(url_for('contact_detail', contact_id=contact_id))
        
    conn = database.get_db_connection()
    contact = conn.execute('SELECT company_name FROM contacts WHERE id = ?', (contact_id,)).fetchone()
    if contact:
        # Delete contact image files if they exist
        c_full = conn.execute('SELECT visiting_card_front, visiting_card_back FROM contacts WHERE id = ?', (contact_id,)).fetchone()
        for side in ['visiting_card_front', 'visiting_card_back']:
            if c_full[side]:
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], c_full[side])
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except Exception:
                        pass
                        
        conn.execute('DELETE FROM contacts WHERE id = ?', (contact_id,))
        # SQLite Foreign Key cascading will delete interactions
        conn.commit()
        log_audit('CONTACT_DELETE', f"Deleted contact {contact['company_name']} (ID: {contact_id})")
        flash(f"Vendor partner '{contact['company_name']}' deleted.", 'success')
    conn.close()
    return redirect(url_for('dashboard'))

# Serving files from upload folder
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    # Allow whitelabel branding assets (logo, favicon) without login
    if filename.startswith('portal_logo_') or filename.startswith('favicon_'):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
        
    # Other files (visiting cards etc.) require active login session
    if not is_logged_in():
        return redirect(url_for('login'))
        
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Upload Visiting Card image
@app.route('/contact/<int:contact_id>/upload-card/<side>', methods=['POST'])
@login_required
def upload_card(contact_id, side):
    if side not in ['front', 'back']:
        flash('Invalid card side parameter.', 'error')
        return redirect(url_for('contact_detail', contact_id=contact_id))
        
    if 'card_image' not in request.files:
        flash('No file part selected.', 'error')
        return redirect(url_for('contact_detail', contact_id=contact_id))
        
    file = request.files['card_image']
    if file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('contact_detail', contact_id=contact_id))
        
    if file and allowed_file(file.filename):
        # Generate clean name: card_<id>_<side>_<uuid>.<ext>
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"card_{contact_id}_{side}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Delete old file if present
        conn = database.get_db_connection()
        col = 'visiting_card_front' if side == 'front' else 'visiting_card_back'
        old_record = conn.execute('SELECT {} FROM contacts WHERE id = ?'.format(col), (contact_id,)).fetchone()
        if old_record and old_record[col]:
            old_filepath = os.path.join(app.config['UPLOAD_FOLDER'], old_record[col])
            if os.path.exists(old_filepath):
                try:
                    os.remove(old_filepath)
                except Exception:
                    pass
                    
        # Save new file
        file.save(filepath)
        
        # Update db record
        conn.execute('UPDATE contacts SET {} = ? WHERE id = ?'.format(col), (filename, contact_id))
        conn.commit()
        conn.close()
        
        log_audit('VISITING_CARD_UPLOAD', f"Uploaded visiting card ({side}) for contact ID: {contact_id}")
        flash(f"Visiting card {side} view uploaded successfully.", 'success')
    else:
        flash('Allowed image types: PNG, JPG, JPEG, GIF, WEBP.', 'error')
        
    return redirect(url_for('contact_detail', contact_id=contact_id))

# Trigger AJAX Web Scrape
@app.route('/contact/<int:contact_id>/scrape', methods=['POST'])
@login_required
def scrape_website(contact_id):
    if session.get('role') == 'viewer':
        return jsonify({"status": "error", "message": "Access Denied: View-only users cannot trigger scraping."}), 403
        
    conn = database.get_db_connection()
    contact = conn.execute('SELECT website, company_name FROM contacts WHERE id = ?', (contact_id,)).fetchone()
    
    if not contact or not contact['website']:
        conn.close()
        return jsonify({"status": "error", "message": "Website URL not configured."}), 400
        
    website = contact['website']
    
    # Run the web scraper
    scrape_data = scrape_oem_website(website, contact['company_name'])
    
    # Save scraped results if status is success or partial
    if scrape_data['status'] in ['success', 'partial']:
        conn.execute('''
        UPDATE contacts 
        SET fetched_products = ?, fetched_services = ?
        WHERE id = ?
        ''', (
            json.dumps(scrape_data['products']), 
            json.dumps(scrape_data['services']), 
            contact_id
        ))
        conn.commit()
        log_audit('PORTFOLIO_AUTO_SCRAPE', f"Triggered web scrape for {contact['company_name']}. Status: {scrape_data['status']}")
        
    conn.close()
    return jsonify(scrape_data)

# Add Custom Portfolio Item (Product or Service)
@app.route('/contact/<int:contact_id>/custom-item', methods=['POST'])
@login_required
def add_custom_item(contact_id):
    if session.get('role') == 'viewer':
        return jsonify({"status": "error", "message": "Access Denied: View-only users cannot add items."}), 403
        
    data = request.get_json()
    item_type = data.get('type') # 'product' or 'service'
    value = data.get('value', '').strip()
    
    if item_type not in ['product', 'service'] or not value:
        return jsonify({"status": "error", "message": "Invalid type or empty value."}), 400
        
    conn = database.get_db_connection()
    contact = conn.execute('SELECT custom_products, custom_services FROM contacts WHERE id = ?', (contact_id,)).fetchone()
    
    if not contact:
        conn.close()
        return jsonify({"status": "error", "message": "Contact not found."}), 404
        
    col = 'custom_products' if item_type == 'product' else 'custom_services'
    current_items = json.loads(contact[col]) if contact[col] else []
    
    if value not in current_items:
        current_items.append(value)
        conn.execute('UPDATE contacts SET {} = ? WHERE id = ?'.format(col), (json.dumps(current_items), contact_id))
        conn.commit()
        log_audit('PORTFOLIO_CUSTOM_ADD', f"Added custom {item_type} to contact ID: {contact_id}")
        
    conn.close()
    return jsonify({"status": "success", "items": current_items})

# Delete Custom Portfolio Item
@app.route('/contact/<int:contact_id>/custom-item/delete', methods=['POST'])
@login_required
def delete_custom_item(contact_id):
    data = request.get_json()
    item_type = data.get('type') # 'product' or 'service'
    value = data.get('value', '').strip()
    
    if item_type not in ['product', 'service'] or not value:
        return jsonify({"status": "error", "message": "Invalid type or empty value."}), 400
        
    conn = database.get_db_connection()
    contact = conn.execute('SELECT custom_products, custom_services FROM contacts WHERE id = ?', (contact_id,)).fetchone()
    
    if not contact:
        conn.close()
        return jsonify({"status": "error", "message": "Contact not found."}), 404
        
    col = 'custom_products' if item_type == 'product' else 'custom_services'
    current_items = json.loads(contact[col]) if contact[col] else []
    
    if value in current_items:
        current_items.remove(value)
        conn.execute('UPDATE contacts SET {} = ? WHERE id = ?'.format(col), (json.dumps(current_items), contact_id))
        conn.commit()
        log_audit('PORTFOLIO_CUSTOM_DELETE', f"Deleted custom {item_type} from contact ID: {contact_id}")
        
    conn.close()
    return jsonify({"status": "success", "items": current_items})

# Unified Portfolio Item Deletion
@app.route('/contact/<int:contact_id>/portfolio/delete', methods=['POST'])
@login_required
def delete_portfolio_item(contact_id):
    if session.get('role') != 'admin':
        return jsonify({"status": "error", "message": "Access Denied: Only administrators can delete items."}), 403
        
    data = request.get_json()
    item_type = data.get('type') # 'product' or 'service'
    source = data.get('source') # 'fetched' or 'custom'
    value = data.get('value', '').strip()
    
    if item_type not in ['product', 'service'] or source not in ['fetched', 'custom'] or not value:
        return jsonify({"status": "error", "message": "Invalid parameters."}), 400
        
    conn = database.get_db_connection()
    contact = conn.execute('SELECT fetched_products, fetched_services, custom_products, custom_services FROM contacts WHERE id = ?', (contact_id,)).fetchone()
    
    if not contact:
        conn.close()
        return jsonify({"status": "error", "message": "Contact not found."}), 404
        
    if source == 'fetched':
        col = 'fetched_products' if item_type == 'product' else 'fetched_services'
    else:
        col = 'custom_products' if item_type == 'product' else 'custom_services'
        
    current_items = json.loads(contact[col]) if contact[col] else []
    
    if value in current_items:
        current_items.remove(value)
        conn.execute('UPDATE contacts SET {} = ? WHERE id = ?'.format(col), (json.dumps(current_items), contact_id))
        conn.commit()
        log_audit('PORTFOLIO_DELETE', f"Deleted {source} {item_type}: {value} (contact ID: {contact_id})")
        
    conn.close()
    return jsonify({"status": "success", "items": current_items})

# VCF Contact Card Download Endpoint
@app.route('/contact/<int:contact_id>/vcf/<int:person_index>')
@login_required
def download_vcf(contact_id, person_index):
    conn = database.get_db_connection()
    contact = conn.execute('SELECT company_name, name, designation, email, phone, website, address, contact_persons FROM contacts WHERE id = ?', (contact_id,)).fetchone()
    conn.close()
    
    if not contact:
        flash('Contact not found.', 'error')
        return redirect(url_for('dashboard'))
        
    try:
        persons = json.loads(contact['contact_persons']) if contact['contact_persons'] else []
    except Exception:
        persons = []
        
    if not persons:
        persons = [{
            "name": contact['name'] or "",
            "designation": contact['designation'] or "",
            "email": contact['email'] or "",
            "phone": contact['phone'] or ""
        }]
        
    if person_index < 0 or person_index >= len(persons):
        flash('Contact person index not found.', 'error')
        return redirect(url_for('contact_detail', contact_id=contact_id))
        
    person = persons[person_index]
    
    vcard = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"FN:{person['name']}",
        f"ORG:{contact['company_name']}",
    ]
    if person['designation']:
        vcard.append(f"TITLE:{person['designation']}")
    if person['email']:
        vcard.append(f"EMAIL;TYPE=PREF,INTERNET:{person['email']}")
    if person['phone']:
        vcard.append(f"TEL;TYPE=CELL,VOICE:{person['phone']}")
    if contact['address']:
        addr = contact['address'].replace('\n', ' ').replace(',', '\\,')
        vcard.append(f"ADR;TYPE=WORK:;;{addr};;;;")
    if contact['website']:
        vcard.append(f"URL:{contact['website']}")
        
    vcard.append("END:VCARD")
    vcard_str = "\n".join(vcard)
    
    from flask import Response
    filename = secure_filename(f"{person['name']}_{contact['company_name']}.vcf")
    return Response(
        vcard_str,
        mimetype="text/vcard",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )

# Log relationship interaction details
@app.route('/contact/<int:contact_id>/interaction', methods=['POST'])
@login_required
def add_interaction(contact_id):
    if session.get('role') == 'viewer':
        flash('Access Denied: View-only users cannot log interactions.', 'error')
        return redirect(url_for('contact_detail', contact_id=contact_id))
        
    interaction_date = request.form['interaction_date'].strip()
    summary = request.form['summary'].strip()
    next_steps = request.form.get('next_steps', '').strip()
    followup_date = request.form.get('followup_date', '').strip()
    
    # Handle multiple select interaction types (checkboxes)
    types_list = request.form.getlist('type[]')
    types_str = ", ".join(types_list) if types_list else "Other"
    
    if not interaction_date or not summary:
        flash('Date and Discussion Summary are required.', 'error')
        return redirect(url_for('contact_detail', contact_id=contact_id))
        
    conn = database.get_db_connection()
    conn.execute('''
    INSERT INTO interactions (contact_id, user_id, interaction_date, type, summary, next_steps, followup_date, followup_status)
    VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
    ''', (contact_id, session['user_id'], interaction_date, types_str, summary, next_steps, followup_date if followup_date else None))
    conn.commit()
    conn.close()
    
    log_audit('INTERACTION_ADD', f"Logged interaction ({types_str}) for contact ID: {contact_id}")
    flash('Relationship interaction successfully logged.', 'success')
    return redirect(url_for('contact_detail', contact_id=contact_id))

# Complete Follow-up Task
@app.route('/interaction/<int:interaction_id>/followup/complete', methods=['POST'])
@login_required
def complete_followup(interaction_id):
    conn = database.get_db_connection()
    row = conn.execute('SELECT contact_id FROM interactions WHERE id = ?', (interaction_id,)).fetchone()
    if row:
        conn.execute("UPDATE interactions SET followup_status = 'completed' WHERE id = ?", (interaction_id,))
        conn.commit()
        log_audit('FOLLOWUP_COMPLETE', f"Completed follow-up task on interaction ID: {interaction_id}")
        flash('Follow-up task marked as completed.', 'success')
    conn.close()
    redirect_url = request.referrer or url_for('dashboard')
    return redirect(redirect_url)

# Delete relationship interaction details
@app.route('/contact/<int:contact_id>/interaction/<int:interaction_id>/delete', methods=['POST'])
@login_required
def delete_interaction(contact_id, interaction_id):
    conn = database.get_db_connection()
    conn.execute('DELETE FROM interactions WHERE id = ? AND contact_id = ?', (interaction_id, contact_id))
    conn.commit()
    conn.close()
    
    log_audit('INTERACTION_DELETE', f"Deleted interaction log ID: {interaction_id}")
    flash('Interaction log deleted.', 'success')
    return redirect(url_for('contact_detail', contact_id=contact_id))

# Edit relationship interaction details (Admin Only)
@app.route('/contact/<int:contact_id>/interaction/<int:interaction_id>/edit', methods=['POST'])
@login_required
def edit_interaction(contact_id, interaction_id):
    if session.get('role') != 'admin':
        flash('Permission denied. Only admins can edit interaction logs.', 'error')
        return redirect(url_for('contact_detail', contact_id=contact_id))
        
    interaction_date = request.form['interaction_date'].strip()
    summary = request.form['summary'].strip()
    next_steps = request.form.get('next_steps', '').strip()
    followup_date = request.form.get('followup_date', '').strip()
    
    types_list = request.form.getlist('type[]')
    types_str = ", ".join(types_list) if types_list else "Other"
    
    if not interaction_date or not summary:
        flash('Date and Discussion Summary are required.', 'error')
        return redirect(url_for('contact_detail', contact_id=contact_id))
        
    conn = database.get_db_connection()
    conn.execute('''
    UPDATE interactions
    SET interaction_date = ?, type = ?, summary = ?, next_steps = ?, followup_date = ?
    WHERE id = ? AND contact_id = ?
    ''', (interaction_date, types_str, summary, next_steps, followup_date if followup_date else None, interaction_id, contact_id))
    conn.commit()
    conn.close()
    
    log_audit('INTERACTION_EDIT', f"Edited interaction ID: {interaction_id} for contact ID: {contact_id}")
    flash('Interaction log entry successfully updated.', 'success')
    return redirect(url_for('contact_detail', contact_id=contact_id))

# Admin Panel Panel Operations
@app.route('/admin')
@admin_required
def admin_panel():
    conn = database.get_db_connection()
    # Fetch all users
    users = conn.execute('SELECT id, username, email, role, status, allowed_groups, created_at FROM users ORDER BY username ASC').fetchall()
    # Fetch all audit logs with operator names
    audit_logs = conn.execute('''
        SELECT a.*, u.username 
        FROM audit_logs a 
        LEFT JOIN users u ON a.user_id = u.id 
        ORDER BY a.created_at DESC, a.id DESC
        LIMIT 100
    ''').fetchall()
    conn.close()
    return render_template('admin.html', users=users, audit_logs=audit_logs)

@app.route('/admin/approve/<int:user_id>', methods=['POST'])
@admin_required
def approve_user(user_id):
    conn = database.get_db_connection()
    user = conn.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
    if user:
        conn.execute("UPDATE users SET status = 'approved' WHERE id = ?", (user_id,))
        conn.commit()
        log_audit('USER_APPROVE', f"Approved login access for team member: {user['username']}")
        flash(f"Approved team access for '{user['username']}'.", 'success')
    conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/admin/reject/<int:user_id>', methods=['POST'])
@admin_required
def reject_user(user_id):
    conn = database.get_db_connection()
    user = conn.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
    if user:
        conn.execute("UPDATE users SET status = 'rejected' WHERE id = ?", (user_id,))
        conn.commit()
        log_audit('USER_REJECT', f"Rejected login access for team member: {user['username']}")
        flash(f"Rejected team access for '{user['username']}'.", 'success')
    conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    conn = database.get_db_connection()
    user = conn.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
    if user:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        log_audit('USER_DELETE', f"Deleted team user: {user['username']}")
    flash(f"Deleted user account '{user['username']}'.", 'success')
    return redirect(url_for('admin_panel'))

# Admin Create approved user account directly
@app.route('/admin/user/create', methods=['POST'])
@admin_required
def admin_create_user():
    username = request.form['username'].strip().lower()
    email = request.form['email'].strip().lower()
    password = request.form['password']
    role = request.form['role']
    
    if not username or not email or not password or not role:
        flash('All fields are required.', 'error')
        return redirect(url_for('admin_panel'))
        
    strong, pwd_err = is_password_strong(password)
    if not strong:
        flash(pwd_err, 'error')
        return redirect(url_for('admin_panel'))
        
    from werkzeug.security import generate_password_hash
    hashed_pw = generate_password_hash(password)
    
    conn = database.get_db_connection()
    existing = conn.execute('SELECT id FROM users WHERE username = ? OR email = ?', (username, email)).fetchone()
    if existing:
        conn.close()
        flash('Username or email already registered.', 'error')
        return redirect(url_for('admin_panel'))
        
    conn.execute('''
    INSERT INTO users (username, email, password_hash, role, status)
    VALUES (?, ?, ?, ?, 'approved')
    ''', (username, email, hashed_pw, role))
    conn.commit()
    conn.close()
    
    log_audit('USER_CREATE_ADMIN', f"Admin created approved account: {username} ({role})")
    flash(f"User account '{username}' successfully created as {role}.", 'success')
    return redirect(url_for('admin_panel'))

# Admin Update team member role and allowed groups
@app.route('/admin/user/<int:user_id>/update', methods=['POST'])
@admin_required
def update_user(user_id):
    role = request.form['role']
    allowed_groups = request.form.get('allowed_groups', 'All').strip()
    
    if not role:
        flash('Role is required.', 'error')
        return redirect(url_for('admin_panel'))
        
    conn = database.get_db_connection()
    conn.execute('UPDATE users SET role = ?, allowed_groups = ? WHERE id = ?', (role, allowed_groups, user_id))
    conn.commit()
    conn.close()
    
    log_audit('USER_UPDATE', f"Updated role/groups for user ID: {user_id} (Role: {role}, Groups: {allowed_groups})")
    flash('User privileges updated successfully.', 'success')
    return redirect(url_for('admin_panel'))

# OEM Categories Management endpoints (Admin Only)
@app.route('/admin/category/add', methods=['POST'])
@admin_required
def admin_add_category():
    name = request.form.get('name', '').strip()
    icon = request.form.get('icon', '📁').strip()
    
    # Handle custom icon file upload if present
    if 'icon_svg' in request.files:
        file = request.files['icon_svg']
        if file and file.filename != '':
            ext = os.path.splitext(file.filename)[1].lower()
            if ext in ['.svg', '.png', '.jpg', '.jpeg']:
                import uuid
                filename = f"cat_icon_{uuid.uuid4().hex[:8]}{ext}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                icon = filename
            
    if not name:
        flash('Category Name is required.', 'error')
        return redirect(url_for('admin_panel'))
        
    conn = database.get_db_connection()
    try:
        conn.execute('INSERT INTO oem_groups (name, icon) VALUES (?, ?)', (name, icon))
        conn.commit()
        log_audit('CATEGORY_ADD', f"Added OEM category: {name} (Icon: {icon})")
        flash(f"OEM Category '{name}' successfully added.", 'success')
    except Exception as e:
        flash(f"Error adding category. It might already exist.", 'error')
    finally:
        conn.close()
        
    return redirect(url_for('admin_panel'))

@app.route('/admin/category/<int:group_id>/delete', methods=['POST'])
@admin_required
def admin_delete_category(group_id):
    conn = database.get_db_connection()
    group = conn.execute('SELECT name FROM oem_groups WHERE id = ?', (group_id,)).fetchone()
    
    if not group:
        conn.close()
        flash('Category not found.', 'error')
        return redirect(url_for('admin_panel'))
        
    category_name = group['name']
    
    if category_name.lower() == 'other':
        conn.close()
        flash("Access Denied: The 'Other' category is a core system fallback and cannot be deleted.", 'error')
        return redirect(url_for('admin_panel'))
        
    conn.execute('DELETE FROM oem_groups WHERE id = ?', (group_id,))
    # Update all contacts under this category to "Other"
    conn.execute("UPDATE contacts SET group_name = 'Other' WHERE group_name = ?", (category_name,))
    conn.commit()
    conn.close()
    
    log_audit('CATEGORY_DELETE', f"Deleted OEM category: {category_name}")
    flash(f"OEM Category '{category_name}' deleted. Associated partners have been moved to 'Other'.", 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/category/<int:group_id>/update-icon', methods=['POST'])
@admin_required
def admin_update_category_icon(group_id):
    icon = request.form.get('icon', '📁').strip()
    
    # Handle custom icon file upload if present
    if 'icon_svg' in request.files:
        file = request.files['icon_svg']
        if file and file.filename != '':
            ext = os.path.splitext(file.filename)[1].lower()
            if ext in ['.svg', '.png', '.jpg', '.jpeg']:
                import uuid
                filename = f"cat_icon_{uuid.uuid4().hex[:8]}{ext}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                icon = filename
            
    conn = database.get_db_connection()
    group = conn.execute('SELECT name FROM oem_groups WHERE id = ?', (group_id,)).fetchone()
    if not group:
        conn.close()
        flash('Category not found.', 'error')
        return redirect(url_for('admin_panel'))
        
    conn.execute('UPDATE oem_groups SET icon = ? WHERE id = ?', (icon, group_id))
    conn.commit()
    conn.close()
    
    log_audit('CATEGORY_ICON_UPDATE', f"Updated icon for category: {group['name']}")
    flash(f"Icon for category '{group['name']}' updated successfully.", 'success')
    return redirect(url_for('admin_panel'))

# Export Partners to CSV (Respecting allowed groups)
@app.route('/export/csv')
@login_required
def export_csv():
    if session.get('role') == 'viewer':
        return jsonify({"status": "error", "message": "Access Denied: View-only users cannot export CSV data."}), 403
        
    conn = database.get_db_connection()
    user = conn.execute('SELECT role, allowed_groups FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    allowed_groups = user['allowed_groups'] if user else 'All'
    
    all_contacts = conn.execute('SELECT * FROM contacts ORDER BY company_name ASC').fetchall()
    
    # Filter by allowed_groups
    if allowed_groups.lower() != 'all':
        groups_list = [g.strip().lower() for g in allowed_groups.split(',')]
        contacts_rows = [c for c in all_contacts if (c['group_name'] or '').strip().lower() in groups_list]
    else:
        contacts_rows = list(all_contacts)
        
    conn.close()
    
    # Audit log tracking for exports
    log_audit('CSV_EXPORT', f"Exported partner directory as CSV (Total rows: {len(contacts_rows)}).")
    
    import csv
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    
    # CSV Headers
    writer.writerow([
        'Company Name', 'Type', 'OEM Group', 'Website', 'Address', 
        'Primary Contact Name', 'Primary Designation', 'Primary Email', 'Primary Phone'
    ])
    
    for c in contacts_rows:
        name = c['name']
        desig = c['designation']
        email = c['email']
        phone = c['phone']
        try:
            persons = json.loads(c['contact_persons']) if c['contact_persons'] else []
            if persons:
                name = persons[0].get('name', name)
                desig = persons[0].get('designation', desig)
                email = persons[0].get('email', email)
                phone = persons[0].get('phone', phone)
        except Exception:
            pass
            
        writer.writerow([
            c['company_name'], c['type'], c['group_name'] or '', c['website'] or '', c['address'] or '',
            name or '', desig or '', email or '', phone or ''
        ])
        
    output.seek(0)
    from flask import Response
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=partners_export.csv"}
    )

# Download CSV Import Template
@app.route('/import/template')
@login_required
def download_import_template():
    import csv
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        'Company Name', 'Type', 'OEM Group', 'Website', 'Address', 
        'Primary Contact Name', 'Primary Designation', 'Primary Email', 'Primary Phone'
    ])
    
    writer.writerow([
        'Cisco Systems', 'OEM', 'Networking', 'https://www.cisco.com', 'San Jose, CA',
        'Rahul Sharma', 'Channel Manager', 'rahul@cisco.com', '+91 98765 43210'
    ])
    
    output.seek(0)
    from flask import Response
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=partners_import_template.csv"}
    )

# Batch Upload/Import Partners from CSV
@app.route('/import/csv', methods=['POST'])
@login_required
def import_csv():
    if session.get('role') == 'viewer':
        return jsonify({"status": "error", "message": "Access Denied: View-only users cannot import CSV data."}), 403
        
    if 'csv_file' not in request.files:
        return jsonify({"status": "error", "message": "Import Failed: No file part was uploaded."}), 400
        
    file = request.files['csv_file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "Import Failed: No selected file."}), 400
        
    if not file.filename.endswith('.csv'):
        return jsonify({"status": "error", "message": "Import Failed: Invalid file extension. Only CSV (.csv) files are supported."}), 400
        
    import csv
    import io
    
    try:
        # Decode using errors="replace" to skip junk characters and prevent crashes
        file_bytes = file.read()
        file_decoded = file_bytes.decode("utf-8-sig", errors="replace")
        stream = io.StringIO(file_decoded, newline=None)
        csv_reader = csv.reader(stream)
    except Exception as e:
        return jsonify({"status": "error", "message": f"CSV Reading Error: Failed to parse character stream. Detail: {str(e)}"}), 400
        
    try:
        headers = [h.strip() for h in next(csv_reader)]
    except StopIteration:
        return jsonify({"status": "error", "message": "Import Failed: The uploaded CSV file is empty."}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f"CSV Reading Error: Failed to parse the header row. Detail: {str(e)}"}), 400
        
    # Header validations
    expected_headers = ['Company Name', 'Type', 'OEM Group', 'Website', 'Address', 
                        'Primary Contact Name', 'Primary Designation', 'Primary Email', 'Primary Phone']
                        
    # Verify critical columns are present
    missing_headers = [h for h in expected_headers[:6] if h not in headers]
    if missing_headers:
        return jsonify({
            "status": "error", 
            "message": f"CSV Column Mismatch: Missing expected headers: {', '.join(missing_headers)}. Please download the template for the correct column format."
        }), 400
        
    conn = database.get_db_connection()
    imported_count = 0
    skipped_count = 0
    warnings = []
    
    row_idx = 1
    try:
        for row in csv_reader:
            row_idx += 1
            if not row:
                continue
                
            # Pad row with blank items if missing columns to prevent index crashes
            if len(row) < 9:
                row = row + [''] * (9 - len(row))
                warnings.append(f"Row {row_idx}: Contained less than 9 columns. Missing columns were auto-padded.")
                
            company_name = row[0].strip()
            type_ = row[1].strip()
            group_name = row[2].strip()
            website = row[3].strip()
            address = row[4].strip()
            name = row[5].strip()
            desig = row[6].strip()
            email = row[7].strip()
            phone = row[8].strip()
            
            # Handle blank items and assign placeholders with warnings
            if not company_name:
                company_name = f"Unnamed Partner {row_idx}"
                warnings.append(f"Row {row_idx}: 'Company Name' was blank, imported as '{company_name}'.")
            if not name:
                name = "Primary Contact"
                warnings.append(f"Row {row_idx} ({company_name}): 'Primary Contact Name' was blank, imported as '{name}'.")
                
            if type_ not in ['OEM', 'Distributor']:
                type_ = 'OEM'
                
            if not group_name:
                group_name = 'Other'
                
            # Check if group exists, if not, dynamically create it
            group_check = conn.execute('SELECT name FROM oem_groups WHERE LOWER(name) = LOWER(?)', (group_name,)).fetchone()
            if not group_check:
                conn.execute('INSERT INTO oem_groups (name, icon) VALUES (?, ?)', (group_name, '📁'))
                warnings.append(f"Row {row_idx}: Category '{group_name}' did not exist in the system and was dynamically created.")
            else:
                group_name = group_check['name']
                
            # Check duplicate / merge contact persons
            existing = conn.execute('SELECT id, contact_persons, name, designation, email, phone FROM contacts WHERE company_name = ?', (company_name,)).fetchone()
            if existing:
                existing_id = existing['id']
                existing_persons_json = existing['contact_persons']
                
                # Parse existing contact persons list
                existing_persons = []
                if existing_persons_json:
                    try:
                        existing_persons = json.loads(existing_persons_json)
                    except Exception:
                        pass
                
                # If existing list is empty, initialize it with the main primary contact info
                if not existing_persons:
                    existing_persons = [{
                        "name": existing['name'],
                        "designation": existing['designation'],
                        "email": existing['email'],
                        "phone": existing['phone']
                    }]
                
                # Check if this new contact person already exists in the list to avoid duplicate entries
                already_exists = False
                for p in existing_persons:
                    if p.get('name', '').lower() == name.lower() and p.get('email', '').lower() == email.lower():
                        already_exists = True
                        break
                
                if not already_exists:
                    existing_persons.append({
                        "name": name,
                        "designation": desig,
                        "email": email,
                        "phone": phone
                    })
                    conn.execute('UPDATE contacts SET contact_persons = ? WHERE id = ?', (json.dumps(existing_persons), existing_id))
                    imported_count += 1
                else:
                    skipped_count += 1
                continue
                
            contact_persons = [{
                "name": name,
                "designation": desig,
                "email": email,
                "phone": phone
            }]
            
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO contacts (company_name, name, type, group_name, designation, email, phone, website, address, contact_persons, fetched_products, fetched_services, custom_products, custom_services, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '[]', '[]', '[]', '[]', ?)
            ''', (
                company_name, name, type_, group_name, desig, email, phone, website, address,
                json.dumps(contact_persons), session['user_id']
            ))
            contact_id = cursor.lastrowid
            
            # Try fetching logo
            logo_filename = download_company_logo(website, contact_id, company_name)
            if logo_filename:
                cursor.execute("UPDATE contacts SET company_logo = ? WHERE id = ?", (logo_filename, contact_id))
                
            imported_count += 1
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"status": "error", "message": f"Database write error at row {row_idx}: {str(e)}. Import aborted."}), 500
        
    conn.close()
    
    try:
        log_audit('CSV_IMPORT', f"Imported {imported_count} partners, skipped {skipped_count} rows with {len(warnings)} notifications.")
    except Exception as e:
        print(f"Failed to log audit event: {e}")
        
    return jsonify({
        "status": "success", 
        "message": f"Successfully imported {imported_count} vendor partners. Skipped {skipped_count} duplicate records.",
        "warnings": warnings
    })

def is_password_strong(password):
    import re
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character."
    return True, ""

def clean_junk_chars(text):
    if not text:
        return ""
    import re
    # Strip non-ASCII control characters and corrupt unicode bytes
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]', '', text)
    # Collapse double spacing
    cleaned = " ".join(cleaned.split())
    return cleaned

@app.route('/user/preferences', methods=['POST'])
@login_required
def save_preferences():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No data received"}), 400
        
    theme = data.get('theme', 'theme-slate-dark')
    columns = data.get('columns', '2')
    show_stats = data.get('showStats', True)
    show_reminders = data.get('showReminders', True)
    
    curr_pwd = data.get('curr_password', '').strip()
    new_pwd = data.get('new_password', '').strip()
    
    conn = database.get_db_connection()
    
    # Handle password change if requested
    if new_pwd:
        if not curr_pwd:
            conn.close()
            return jsonify({"status": "error", "message": "Current password is required to change password."}), 400
            
        user = conn.execute("SELECT password_hash FROM users WHERE id = ?", (session['user_id'],)).fetchone()
        if not user or not check_password_hash(user['password_hash'], curr_pwd):
            conn.close()
            return jsonify({"status": "error", "message": "Incorrect current password."}), 400
            
        strong, pwd_err = is_password_strong(new_pwd)
        if not strong:
            conn.close()
            return jsonify({"status": "error", "message": pwd_err}), 400
            
        hashed = generate_password_hash(new_pwd)
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed, session['user_id']))
        
    import json
    layout_data = {
        "columns": columns,
        "showStats": show_stats,
        "showReminders": show_reminders
    }
    layout_str = json.dumps(layout_data)
    
    conn.execute('UPDATE users SET theme = ?, dashboard_layout = ? WHERE id = ?', (theme, layout_str, session['user_id']))
    conn.commit()
    conn.close()
    
    if new_pwd:
        try:
            log_audit('PASSWORD_CHANGE', f"User {session['username']} successfully changed account password.")
        except Exception as e:
            print(f"Failed to log password change audit: {e}")
            
    session['theme'] = theme
    session['dashboard_layout'] = layout_str
    
    return jsonify({"status": "success", "message": "Preferences saved successfully!"})

@app.route('/contact/<int:contact_id>/fetch-logo', methods=['POST'])
@login_required
def fetch_logo_endpoint(contact_id):
    if session.get('role') == 'viewer':
        return jsonify({"status": "error", "message": "Access Denied: View-only users cannot fetch logos."}), 403
        
    conn = database.get_db_connection()
    contact = conn.execute("SELECT company_name, website FROM contacts WHERE id = ?", (contact_id,)).fetchone()
    if not contact:
        conn.close()
        return jsonify({"status": "error", "message": "Partner profile not found."}), 404
        
    logo_filename = download_company_logo(contact['website'], contact_id, contact['company_name'])
    if logo_filename:
        conn.execute("UPDATE contacts SET company_logo = ? WHERE id = ?", (logo_filename, contact_id))
        conn.commit()
        conn.close()
        log_audit('LOGO_FETCH', f"Successfully fetched logo for '{contact['company_name']}' from the Internet.")
        return jsonify({"status": "success", "logo_url": url_for('uploaded_file', filename=logo_filename)})
    else:
        conn.close()
        return jsonify({"status": "error", "message": "Could not locate logo on the Internet."}), 400

@app.route('/contact/<int:contact_id>/refresh-web', methods=['POST'])
@login_required
def refresh_web_scrapes(contact_id):
    if session.get('role') == 'viewer':
        return jsonify({"status": "error", "message": "Access Denied: View-only users cannot refresh content."}), 403
        
    conn = database.get_db_connection()
    contact = conn.execute('SELECT * FROM contacts WHERE id = ?', (contact_id,)).fetchone()
    if not contact:
        conn.close()
        return jsonify({"status": "error", "message": "Partner profile not found."}), 404
        
    # Clean existing fields from junk characters
    cleaned_company = clean_junk_chars(contact['company_name'])
    cleaned_name = clean_junk_chars(contact['name'])
    cleaned_desig = clean_junk_chars(contact['designation'])
    cleaned_email = clean_junk_chars(contact['email'])
    cleaned_phone = clean_junk_chars(contact['phone'])
    cleaned_website = clean_junk_chars(contact['website'])
    cleaned_address = clean_junk_chars(contact['address'])
    
    # Parse and clean dynamic contact_persons list
    contact_persons = []
    try:
        if contact['contact_persons']:
            persons = json.loads(contact['contact_persons'])
            for p in persons:
                contact_persons.append({
                    "name": clean_junk_chars(p.get('name', '')),
                    "designation": clean_junk_chars(p.get('designation', '')),
                    "email": clean_junk_chars(p.get('email', '')),
                    "phone": clean_junk_chars(p.get('phone', ''))
                })
    except Exception:
        pass
        
    if not contact_persons:
        contact_persons = [{
            "name": cleaned_name,
            "designation": cleaned_desig,
            "email": cleaned_email,
            "phone": cleaned_phone
        }]
        
    # 2. Trigger web scraper to fetch products/services
    scraped_products = []
    scraped_services = []
    
    if cleaned_website:
        try:
            from scraper import scrape_oem_website
            scraped = scrape_oem_website(cleaned_website, cleaned_company)
            if scraped:
                scraped_products = scraped.get('products', [])
                scraped_services = scraped.get('services', [])
        except Exception as e:
            print(f"Scraper error during refresh: {e}")
            
    # Update SQLite record
    conn.execute('''
    UPDATE contacts
    SET company_name = ?, name = ?, designation = ?, email = ?, phone = ?, website = ?, address = ?, 
        contact_persons = ?, fetched_products = ?, fetched_services = ?, updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    ''', (
        cleaned_company,
        cleaned_name,
        cleaned_desig,
        cleaned_email,
        cleaned_phone,
        cleaned_website,
        cleaned_address,
        json.dumps(contact_persons),
        json.dumps(scraped_products),
        json.dumps(scraped_services),
        contact_id
    ))
    
    # Re-fetch company logo if missing or domain resolved
    logo_filename = download_company_logo(cleaned_website, contact_id, cleaned_company)
    if logo_filename:
        conn.execute("UPDATE contacts SET company_logo = ? WHERE id = ?", (logo_filename, contact_id))
        
    conn.commit()
    conn.close()
    
    log_audit('CONTACT_REFRESH', f"Refreshed, cleaned and synchronized vendor: {cleaned_company}")
    return jsonify({
        "status": "success", 
        "message": f"Successfully stripped junk characters, refreshed company logo, and synchronized products/services from '{cleaned_company}' website!"
    })

@app.route('/contact/<int:contact_id>/upload-card/delete', methods=['POST'])
@login_required
def delete_visiting_card(contact_id):
    if session.get('role') == 'viewer':
        flash('Access Denied: View-only users cannot delete visiting cards.', 'error')
        return redirect(url_for('contact_detail', contact_id=contact_id))
        
    side = request.args.get('side', 'front').strip().lower()
    if side not in ['front', 'back']:
        side = 'front'
        
    conn = database.get_db_connection()
    contact = conn.execute('SELECT company_name, visiting_card_front, visiting_card_back FROM contacts WHERE id = ?', (contact_id,)).fetchone()
    
    if not contact:
        conn.close()
        flash('Partner profile not found.', 'error')
        return redirect(url_for('dashboard'))
        
    filename = contact['visiting_card_front'] if side == 'front' else contact['visiting_card_back']
    
    if filename:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                print(f"Deleted card image: {filepath}")
            except Exception as e:
                print(f"Error removing card file: {e}")
                
        if side == 'front':
            conn.execute("UPDATE contacts SET visiting_card_front = NULL WHERE id = ?", (contact_id,))
        else:
            conn.execute("UPDATE contacts SET visiting_card_back = NULL WHERE id = ?", (contact_id,))
            
        conn.commit()
        log_audit('CARD_DELETE', f"Deleted {side} visiting card photo for partner: {contact['company_name']}")
        flash(f"Successfully deleted {side} side visiting card image.", 'success')
    else:
        flash(f"No {side} side visiting card image to remove.", 'error')
        
    conn.close()
    return redirect(url_for('contact_detail', contact_id=contact_id))

def run_master_sync_thread(user_id, username):
    global master_sync_in_progress
    
    # We create database connections independently within the thread context
    conn = database.get_db_connection()
    contacts = conn.execute('SELECT id, company_name, website FROM contacts').fetchall()
    conn.close()
    
    total = len(contacts)
    refreshed_count = 0
    errors = []
    
    from scraper import scrape_oem_website
    
    try:
        log_audit('PORTFOLIO_MASTER_REFRESH_START', f"Background master sync initiated by {username} for all {total} partners.", user_id=user_id)
    except Exception as e:
        print(f"Audit log starting error: {e}")
        
    for idx, c in enumerate(contacts):
        contact_id = c['id']
        company_name = c['company_name']
        website = c['website']
        
        try:
            conn = database.get_db_connection()
            contact = conn.execute('SELECT * FROM contacts WHERE id = ?', (contact_id,)).fetchone()
            
            # Clean fields
            cleaned_company = clean_junk_chars(contact['company_name'])
            cleaned_name = clean_junk_chars(contact['name'])
            cleaned_desig = clean_junk_chars(contact['designation'])
            cleaned_email = clean_junk_chars(contact['email'])
            cleaned_phone = clean_junk_chars(contact['phone'])
            cleaned_website = clean_junk_chars(contact['website'])
            cleaned_address = clean_junk_chars(contact['address'])
            
            # Parse contact persons
            contact_persons = []
            if contact['contact_persons']:
                try:
                    persons = json.loads(contact['contact_persons'])
                    for p in persons:
                        contact_persons.append({
                            "name": clean_junk_chars(p.get('name', '')),
                            "designation": clean_junk_chars(p.get('designation', '')),
                            "email": clean_junk_chars(p.get('email', '')),
                            "phone": clean_junk_chars(p.get('phone', ''))
                        })
                except Exception:
                    pass
            if not contact_persons:
                contact_persons = [{
                    "name": cleaned_name,
                    "designation": cleaned_desig,
                    "email": cleaned_email,
                    "phone": cleaned_phone
                }]
                
            scraped_products = []
            scraped_services = []
            if cleaned_website:
                scraped = scrape_oem_website(cleaned_website, cleaned_company)
                if scraped:
                    scraped_products = scraped.get('products', [])
                    scraped_services = scraped.get('services', [])
            
            conn.execute('''
            UPDATE contacts
            SET company_name = ?, name = ?, designation = ?, email = ?, phone = ?, website = ?, address = ?, 
                contact_persons = ?, fetched_products = ?, fetched_services = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            ''', (
                cleaned_company,
                cleaned_name,
                cleaned_desig,
                cleaned_email,
                cleaned_phone,
                cleaned_website,
                cleaned_address,
                json.dumps(contact_persons),
                json.dumps(scraped_products),
                json.dumps(scraped_services),
                contact_id
            ))
            
            # Re-fetch company logo if missing
            logo_filename = download_company_logo(cleaned_website, contact_id, cleaned_company)
            if logo_filename:
                conn.execute("UPDATE contacts SET company_logo = ? WHERE id = ?", (logo_filename, contact_id))
                
            conn.commit()
            conn.close()
            refreshed_count += 1
            
            # Log progress increments in audit trail
            try:
                log_audit('PORTFOLIO_MASTER_REFRESH_PROGRESS', f"Syncing catalog: ({refreshed_count}/{total}) Completed '{company_name}' successfully.", user_id=user_id)
            except Exception:
                pass
                
        except Exception as e:
            if conn:
                try: conn.close()
                except: pass
            errors.append(f"{company_name}: {e}")
            
    with master_sync_lock:
        master_sync_in_progress = False
        
    try:
        log_audit('PORTFOLIO_MASTER_REFRESH_COMPLETE', f"Master sync completed successfully. Synchronized {refreshed_count}/{total} partners. Failed rows: {len(errors)}.", user_id=user_id)
    except Exception as e:
        print(f"Audit log completion error: {e}")

@app.route('/admin/refresh-all-contacts', methods=['POST'])
@admin_required
def admin_refresh_all_contacts():
    global master_sync_in_progress
    
    with master_sync_lock:
        if master_sync_in_progress:
            flash("A master catalog synchronization is already running in the background.", "warning")
            return redirect(url_for('admin_panel'))
        master_sync_in_progress = True
        
    if app.config.get('TESTING'):
        # In tests, run synchronously to prevent SQLite permission/lock issues
        run_master_sync_thread(session.get('user_id'), session.get('username'))
    else:
        # Kick off background synchronization thread
        t = threading.Thread(target=run_master_sync_thread, args=(session.get('user_id'), session.get('username')))
        t.daemon = True
        t.start()
    
    flash("Master synchronization successfully initiated in the background! Please monitor the Audit Trail logs below for real-time progress.", "success")
    return redirect(url_for('admin_panel'))

@app.route('/admin/backup/download')
@admin_required
def download_master_backup():
    import zipfile
    import io
    import traceback
    
    try:
        temp_zip_path = os.path.join(app.config['UPLOAD_FOLDER'], 'oem_portal_master_backup.zip')
        
        # Determine zip compression method
        try:
            import zlib
            compress_method = zipfile.ZIP_DEFLATED
        except ImportError:
            compress_method = zipfile.ZIP_STORED
            
        with zipfile.ZipFile(temp_zip_path, 'w', compress_method) as zipf:
            # Add database
            db_path = database.DB_PATH
            if os.path.exists(db_path):
                try:
                    zipf.write(db_path, arcname='oem_tracker.db')
                except Exception as db_err:
                    print(f"Backup warning: could not write db to zip: {db_err}")
                
            # Add uploads files
            upload_folder = app.config['UPLOAD_FOLDER']
            if os.path.exists(upload_folder):
                for root, dirs, files in os.walk(upload_folder):
                    for file in files:
                        if file in ['.gitkeep', 'temp_restore.zip', 'oem_portal_master_backup.zip']:
                            continue
                        filepath = os.path.join(root, file)
                        arcname = os.path.join('uploads', file)
                        try:
                            zipf.write(filepath, arcname=arcname)
                        except Exception as file_err:
                            print(f"Backup warning: could not write file {file} to zip: {file_err}")
                            
        from flask import send_file
        try:
            return send_file(
                temp_zip_path,
                mimetype='application/zip',
                as_attachment=True,
                download_name='oem_portal_master_backup.zip'
            )
        except TypeError:
            return send_file(
                temp_zip_path,
                mimetype='application/zip',
                as_attachment=True,
                attachment_filename='oem_portal_master_backup.zip'
            )
    except Exception as e:
        err_msg = traceback.format_exc()
        log_audit('BACKUP_FAILED', f"Master backup generation failed: {str(e)}")
        flash(f"Backup Generation Failed: {str(e)}", 'error')
        print(f"Backup error trace: {err_msg}")
        return redirect(url_for('admin_panel'))

@app.route('/admin/restore', methods=['POST'])
@admin_required
def restore_master_backup():
    if 'backup_file' not in request.files:
        flash('No file uploaded.', 'error')
        return redirect(url_for('admin_panel'))
        
    file = request.files['backup_file']
    if file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('admin_panel'))
        
    if not file.filename.endswith('.zip'):
        flash('Invalid file format. Please upload a .zip backup file.', 'error')
        return redirect(url_for('admin_panel'))
        
    import zipfile
    import shutil
    
    temp_zip_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_restore.zip')
    file.save(temp_zip_path)
    
    try:
        with zipfile.ZipFile(temp_zip_path, 'r') as zipf:
            namelist = zipf.namelist()
            if 'oem_tracker.db' not in namelist:
                flash('Invalid backup file: missing oem_tracker.db', 'error')
                return redirect(url_for('admin_panel'))
                
            # Copy current database to backup first
            shutil.copy(database.DB_PATH, database.DB_PATH + '.bak')
            
            # Read from zip and write directly to absolute DB_PATH
            db_data = zipf.read('oem_tracker.db')
            with open(database.DB_PATH, 'wb') as db_out:
                db_out.write(db_data)
            
            # Extract uploads absolutely to UPLOAD_FOLDER
            for name in namelist:
                if name.startswith('uploads/') and not name.endswith('/'):
                    filename = os.path.basename(name)
                    if filename:
                        target_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file_data = zipf.read(name)
                        with open(target_path, 'wb') as out_file:
                            out_file.write(file_data)
                    
        if os.path.exists(temp_zip_path):
            os.remove(temp_zip_path)
            
        log_audit('PORTAL_RESTORE', f"Admin {session['username']} successfully restored a master backup.")
        flash('Portal master backup successfully restored! Database and uploaded cards/logos updated.', 'success')
        
    except Exception as e:
        # Revert
        if os.path.exists(database.DB_PATH + '.bak'):
            shutil.copy(database.DB_PATH + '.bak', database.DB_PATH)
        flash(f"Restore failed: {e}", 'error')
    finally:
        if os.path.exists(temp_zip_path):
            try: os.remove(temp_zip_path)
            except: pass
        if os.path.exists(database.DB_PATH + '.bak'):
            try: os.remove(database.DB_PATH + '.bak')
            except: pass
            
    return redirect(url_for('admin_panel'))

@app.route('/admin/settings/update', methods=['POST'])
@admin_required
def update_settings():
    portal_name = request.form.get('portal_name', '').strip()
    
    conn = database.get_db_connection()
    
    if portal_name:
        conn.execute('INSERT OR REPLACE INTO portal_settings (key, value) VALUES (?, ?)', ('portal_name', portal_name))
        
    # Handle logo file upload
    if 'portal_logo' in request.files:
        file = request.files['portal_logo']
        if file and file.filename != '' and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"portal_logo_{uuid.uuid4().hex[:6]}.{ext}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            conn.execute('INSERT OR REPLACE INTO portal_settings (key, value) VALUES (?, ?)', ('portal_logo', filename))
            
    # Handle favicon file upload
    if 'favicon' in request.files:
        file = request.files['favicon']
        if file and file.filename != '' and (allowed_file(file.filename) or file.filename.endswith('.ico')):
            ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'ico'
            filename = f"favicon_{uuid.uuid4().hex[:6]}.{ext}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            conn.execute('INSERT OR REPLACE INTO portal_settings (key, value) VALUES (?, ?)', ('favicon', filename))
            
    conn.commit()
    conn.close()
    
    log_audit('SETTINGS_WHITELABEL', f"Updated portal whitelabel branding: Name: '{portal_name}'")
    flash('Portal whitelabel configurations saved successfully.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/email-settings/update', methods=['POST'])
@admin_required
def update_email_settings():
    conn = database.get_db_connection()
    
    # Retrieve form settings
    forgot = request.form.get('forgot_password_enabled')
    service = request.form.get('email_service_type', 'smtp')
    server = request.form.get('email_server', '').strip()
    port = request.form.get('email_port', '587').strip()
    ssl_enc = request.form.get('email_ssl')
    username = request.form.get('email_username', '').strip()
    password = request.form.get('email_password', '').strip()
    
    # Convert checkbox states
    forgot_str = 'true' if forgot == 'true' else 'false'
    ssl_str = 'true' if ssl_enc == 'true' else 'false'
    
    # Insert settings keys
    conn.execute('INSERT OR REPLACE INTO portal_settings (key, value) VALUES (?, ?)', ('forgot_password_enabled', forgot_str))
    conn.execute('INSERT OR REPLACE INTO portal_settings (key, value) VALUES (?, ?)', ('email_service_type', service))
    conn.execute('INSERT OR REPLACE INTO portal_settings (key, value) VALUES (?, ?)', ('email_server', server))
    conn.execute('INSERT OR REPLACE INTO portal_settings (key, value) VALUES (?, ?)', ('email_port', port))
    conn.execute('INSERT OR REPLACE INTO portal_settings (key, value) VALUES (?, ?)', ('email_ssl', ssl_str))
    conn.execute('INSERT OR REPLACE INTO portal_settings (key, value) VALUES (?, ?)', ('email_username', username))
    
    if password:
        conn.execute('INSERT OR REPLACE INTO portal_settings (key, value) VALUES (?, ?)', ('email_password', password))
        
    conn.commit()
    conn.close()
    
    log_audit('SETTINGS_EMAIL', f"Updated email connectivity & passwords services settings.")
    flash('Email connection and password configurations saved successfully.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/reset-portal', methods=['POST'])
@admin_required
def reset_portal():
    conn = database.get_db_connection()
    try:
        # Disable foreign keys temporarily to clear tables cleanly without constraint halts
        conn.execute('PRAGMA foreign_keys = OFF')
        
        # Clear transaction tables
        conn.execute('DELETE FROM contacts')
        conn.execute('DELETE FROM interactions')
        conn.execute('DELETE FROM oem_groups')
        conn.execute('DELETE FROM audit_logs')
        
        # Re-enable foreign keys
        conn.execute('PRAGMA foreign_keys = ON')
        
        # Identify whitelabel identity assets to preserve
        whitelabel_files = []
        settings_rows = conn.execute("SELECT value FROM portal_settings WHERE key IN ('portal_logo', 'favicon')").fetchall()
        for r in settings_rows:
            if r['value']:
                whitelabel_files.append(r['value'])
        
        # Prune uploads directory (preserving logo and favicon files)
        upload_folder = app.config['UPLOAD_FOLDER']
        if os.path.exists(upload_folder):
            for filename in os.listdir(upload_folder):
                if filename in whitelabel_files:
                    continue  # Keep whitelabel assets
                file_path = os.path.join(upload_folder, filename)
                if os.path.isfile(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"Error removing upload file {filename}: {e}")
                        
        conn.commit()
        log_audit('PORTAL_RESET', f"Admin {session['username']} executed full database and uploads reset.")
        flash('Portal database has been successfully reset to empty factory state.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Reset error: {e}', 'error')
    finally:
        conn.close()
        
    return redirect(url_for('admin_panel'))

@app.route('/admin/logs/export/text')
@admin_required
def export_logs_text():
    conn = database.get_db_connection()
    logs = conn.execute('SELECT * FROM audit_logs ORDER BY created_at DESC').fetchall()
    conn.close()
    
    output = []
    for log in logs:
        output.append(f"[{log['created_at']}] [{log['username'] or 'SYSTEM'}] [{log['action']}] {log['details']}")
        
    from flask import Response
    return Response(
        "\n".join(output),
        mimetype="text/plain",
        headers={"Content-disposition": "attachment; filename=system_audit_logs.txt"}
    )

@app.route('/admin/logs/export/csv')
@admin_required
def export_logs_csv():
    import csv
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['Timestamp', 'Operator', 'Action Type', 'Log Details'])
    
    conn = database.get_db_connection()
    logs = conn.execute('SELECT * FROM audit_logs ORDER BY created_at DESC').fetchall()
    conn.close()
    
    for log in logs:
        writer.writerow([log['created_at'], log['username'] or 'SYSTEM', log['action'], log['details']])
        
    output.seek(0)
    from flask import Response
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=system_audit_logs.csv"}
    )

@app.route('/scan-card', methods=['POST'])
@login_required
def scan_card():
    if 'card_image' not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded"}), 400
        
    file = request.files['card_image']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No file selected"}), 400
        
    # Save file temporarily
    import uuid
    temp_filename = f"scan_{uuid.uuid4().hex}_{file.filename}"
    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
    file.save(temp_path)
    
    parsed_data = {
        "company_name": "",
        "name": "",
        "designation": "",
        "email": "",
        "phone": "",
        "website": "",
        "address": ""
    }
    
    detected_qr = False
    qr_text = ""
    
    # 1. Try to decode QR Code via OpenCV
    try:
        import cv2
        cv_img = cv2.imread(temp_path)
        if cv_img is not None:
            detector = cv2.QRCodeDetector()
            val, pts, straight_qrcode = detector.detectAndDecode(cv_img)
            if val:
                detected_qr = True
                qr_text = val
    except Exception as e:
        print(f"OpenCV QR detection error: {e}")
        
    if detected_qr:
        # Parse QR text (could be vCard or raw text)
        parsed_data = parse_qr_contact_info(qr_text)
        try:
            os.remove(temp_path)
        except Exception:
            pass
        return jsonify({"status": "success", "source": "qrcode", "data": parsed_data})
        
    # 2. Run High-Accuracy server-side OCR via Pytesseract
    ocr_text = ""
    try:
        from PIL import Image, ImageEnhance
        import pytesseract
        
        # Pre-process image
        img = Image.open(temp_path)
        img = img.convert('L') # Grayscale
        img = img.resize((img.width * 2, img.height * 2), Image.Resampling.LANCZOS)
        img = ImageEnhance.Contrast(img).enhance(2.5)
        img = ImageEnhance.Sharpness(img).enhance(2.0)
        
        # Run OCR
        ocr_text = pytesseract.image_to_string(img)
    except Exception as e:
        print(f"Server-side Tesseract OCR failed: {e}")
        try:
            os.remove(temp_path)
        except Exception:
            pass
        # Return fallback signal to client to run client-side Tesseract.js
        return jsonify({"status": "fallback", "message": "Server-side OCR library not available. Falling back to client-side OCR."})

    try:
        os.remove(temp_path)
    except Exception:
        pass

    # 3. Parse OCR text using advanced regex and NLP heuristics
    parsed_data = parse_raw_ocr_text(ocr_text)
    return jsonify({"status": "success", "source": "ocr", "data": parsed_data})

def parse_qr_contact_info(text):
    data = {
        "company_name": "",
        "name": "",
        "designation": "",
        "email": "",
        "phone": "",
        "website": "",
        "address": ""
    }
    if not text:
        return data
        
    # Check if VCard format
    if "BEGIN:VCARD" in text.upper():
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line.upper().startswith("FN:"):
                data["name"] = line[3:].strip()
            elif line.upper().startswith("N:") and not data["name"]:
                parts = line[2:].split(';')
                first_name = parts[1].strip() if len(parts) > 1 else ""
                last_name = parts[0].strip() if len(parts) > 0 else ""
                data["name"] = f"{first_name} {last_name}".strip()
            elif line.upper().startswith("ORG:"):
                data["company_name"] = line[4:].replace(';', ' ').strip()
            elif line.upper().startswith("TITLE:"):
                data["designation"] = line[6:].strip()
            elif "EMAIL" in line.upper():
                parts = line.split(':')
                if len(parts) > 1:
                    data["email"] = parts[-1].strip()
            elif "TEL" in line.upper():
                parts = line.split(':')
                if len(parts) > 1:
                    data["phone"] = parts[-1].strip()
            elif "URL" in line.upper():
                parts = line.split(':')
                if len(parts) > 1:
                    data["website"] = ":".join(parts[1:]).strip()
            elif "ADR" in line.upper():
                parts = line.split(':')
                if len(parts) > 1:
                    data["address"] = parts[-1].replace(';', ' ').strip()
    else:
        # Simple text parse
        data = parse_raw_ocr_text(text)
        
    return data

def parse_raw_ocr_text(text):
    import re
    data = {
        "company_name": "",
        "name": "",
        "designation": "",
        "email": "",
        "phone": "",
        "website": "",
        "address": ""
    }
    if not text:
        return data
        
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # 1. Extract Email
    email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
    emails = []
    for line in lines:
        match = re.search(email_pattern, line)
        if match:
            emails.append(match.group(0))
    if emails:
        data["email"] = emails[0]
        
    # 2. Extract Website
    web_pattern = r'(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+)'
    websites = []
    for line in lines:
        if "@" in line:
            continue
        match = re.search(web_pattern, line)
        if match:
            url = match.group(0)
            if not url.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.pdf')):
                websites.append(url)
    if websites:
        data["website"] = websites[0]
        
    # 3. Extract Phone
    phone_pattern = r'\+?\d[\d-\s()]{7,}\d'
    phones = []
    for line in lines:
        match = re.search(phone_pattern, line)
        if match:
            clean_digits = re.sub(r'\D', '', match.group(0))
            if 8 <= len(clean_digits) <= 15:
                phones.append(match.group(0))
    if phones:
        data["phone"] = phones[0]
        
    # 4. Extract Name and Designation Heuristics
    name_candidates = []
    for i, line in enumerate(lines[:5]):
        if "@" in line or any(kw in line.lower() for kw in ['.com', '.in', '.org', '.net', 'www.', 'http', '+', 'tel', 'phone', 'mobile', 'email', 'fax', 'web']):
            continue
        words = line.split()
        if 2 <= len(words) <= 3:
            if all(w[0].isupper() for w in words if w[0].isalpha()):
                name_candidates.append((i, line))
                
    if name_candidates:
        idx, name = name_candidates[0]
        data["name"] = name
        if idx + 1 < len(lines):
            next_line = lines[idx + 1]
            if not any(kw in next_line.lower() for kw in ['.com', '.in', 'www.', '+', 'tel', 'phone', 'email']):
                data["designation"] = next_line
                
    # 5. Extract Company Name
    company_candidates = []
    for i, line in enumerate(lines[:3]):
        if line == data["name"] or line == data["designation"]:
            continue
        if "@" in line or any(kw in line.lower() for kw in ['.com', '.in', 'www.', 'http', 'tel', 'phone', 'email']):
            continue
        company_candidates.append(line)
    if company_candidates:
        data["company_name"] = company_candidates[0]
        
    # 6. Extract Address
    address_keywords = ['street', 'road', 'floor', 'building', 'city', 'state', 'zip', 'india', 'usa', 'office', 'plot', 'sector', 'block', 'bazaar', 'nagar', 'gali', 'cantt', 'phase']
    address_lines = []
    for line in lines:
        if any(kw in line.lower() for kw in address_keywords):
            if line == data["company_name"] or line == data["name"] or line == data["designation"]:
                continue
            address_lines.append(line)
    if address_lines:
        data["address"] = ", ".join(address_lines)
        
    return data

@app.route('/admin/clear-logs', methods=['POST'])
@admin_required
def clear_logs():
    clear_from = request.form.get('clear_from', '').strip()
    clear_to = request.form.get('clear_to', '').strip()
    
    conn = database.get_db_connection()
    if clear_from and clear_to:
        conn.execute("DELETE FROM audit_logs WHERE created_at >= ? AND created_at <= ?", 
                     (f"{clear_from} 00:00:00", f"{clear_to} 23:59:59"))
        log_audit('LOGS_CLEAR', f"Erasure of audit logs executed from {clear_from} to {clear_to}")
        flash(f"Audit logs from {clear_from} to {clear_to} successfully erased.", 'success')
    else:
        conn.execute("DELETE FROM audit_logs")
        conn.execute("INSERT INTO audit_logs (action, details) VALUES (?, ?)", 
                     ('LOGS_CLEAR', f"All audit logs cleared by administrator {session['username']}."))
        flash("All system audit logs successfully erased.", 'success')
        
    conn.commit()
    conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/rfps')
@login_required
def rfps_list():
    search_query = request.args.get('search', '').strip()
    conn = database.get_db_connection()
    
    if search_query:
        search_pattern = f"%{search_query}%"
        rfps = conn.execute("""
            SELECT DISTINCT r.* 
            FROM rfps r
            LEFT JOIN rfp_boq_items b ON r.id = b.rfp_id
            LEFT JOIN rfp_checklist c ON r.id = c.rfp_id
            LEFT JOIN rfp_documents d ON r.id = d.rfp_id
            WHERE r.rfp_number LIKE ?
               OR r.contact_name LIKE ?
               OR r.contact_email LIKE ?
               OR r.contact_phone LIKE ?
               OR r.contact_address LIKE ?
               OR b.item_name LIKE ?
               OR c.doc_name LIKE ?
               OR d.original_name LIKE ?
            ORDER BY r.id DESC
        """, (search_pattern,) * 8).fetchall()
    else:
        rfps = conn.execute("SELECT * FROM rfps ORDER BY id DESC").fetchall()
        
    conn.close()
    return render_template('rfps.html', rfps=rfps, search_query=search_query)

@app.route('/rfps/create', methods=['POST'])
@login_required
def rfp_create():
    rfp_number = request.form.get('rfp_number', '').strip()
    pre_bid_date = request.form.get('pre_bid_date', '').strip()
    submission_date = request.form.get('submission_date', '').strip()
    contact_name = request.form.get('contact_name', '').strip()
    contact_address = request.form.get('contact_address', '').strip()
    contact_email = request.form.get('contact_email', '').strip()
    contact_phone = request.form.get('contact_phone', '').strip()
    
    if not rfp_number:
        flash("RFP Number is required.", "error")
        return redirect(url_for('rfps_list'))
        
    conn = database.get_db_connection()
    try:
        # Check duplicate
        existing = conn.execute("SELECT id FROM rfps WHERE rfp_number = ?", (rfp_number,)).fetchone()
        if existing:
            flash(f"RFP Number '{rfp_number}' already exists.", "error")
            return redirect(url_for('rfps_list'))
            
        cursor = conn.execute("""
            INSERT INTO rfps (rfp_number, pre_bid_date, submission_date, contact_name, contact_address, contact_email, contact_phone, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (rfp_number, pre_bid_date, submission_date, contact_name, contact_address, contact_email, contact_phone, session['user_id']))
        rfp_id = cursor.lastrowid
        
        # Pre-seed default document checklist
        default_checklist = [
            ("RFP Document", "Original RFP document containing scope and guidelines"),
            ("Technical Bid", "Prepared technical compliance and response sheets"),
            ("Financial Bid", "Commercial quote and price schedule document"),
            ("OEM Authorization Letter (MAF)", "Manufacturer Authorization Form credentials"),
            ("Tender Fee Receipt", "Receipt of payment for tender document purchase")
        ]
        for name, desc in default_checklist:
            conn.execute("""
                INSERT INTO rfp_checklist (rfp_id, doc_name, doc_description, status)
                VALUES (?, ?, ?, 'Not Received')
            """, (rfp_id, name, desc))
            
        conn.commit()
        log_audit('RFP_CREATE', f"Created RFP: {rfp_number}")
        flash(f"RFP '{rfp_number}' successfully created and checklist initialized.", "success")
        return redirect(url_for('rfp_detail', rfp_id=rfp_id))
    except Exception as e:
        flash(f"Error creating RFP: {e}", "error")
        return redirect(url_for('rfps_list'))
    finally:
        conn.close()

@app.route('/rfps/<int:rfp_id>')
@login_required
def rfp_detail(rfp_id):
    conn = database.get_db_connection()
    rfp = conn.execute("SELECT * FROM rfps WHERE id = ?", (rfp_id,)).fetchone()
    if not rfp:
        conn.close()
        flash("RFP not found.", "error")
        return redirect(url_for('rfps_list'))
        
    # Fetch checklist
    checklist = conn.execute("SELECT * FROM rfp_checklist WHERE rfp_id = ? ORDER BY id ASC", (rfp_id,)).fetchall()
    
    # Fetch documents
    documents = conn.execute("SELECT * FROM rfp_documents WHERE rfp_id = ? ORDER BY id DESC", (rfp_id,)).fetchall()
    
    # Fetch directory OEMs for BoQ column selector
    oems_rows = conn.execute("SELECT DISTINCT company_name FROM contacts WHERE type = 'OEM' ORDER BY company_name").fetchall()
    directory_oems = [r['company_name'] for r in oems_rows if r['company_name']]
    
    # Fetch BoQ matrix
    items_rows = conn.execute("SELECT * FROM rfp_boq_items WHERE rfp_id = ? ORDER BY id ASC", (rfp_id,)).fetchall()
    boq_matrix = []
    oems_mapped_set = set()
    
    for item in items_rows:
        mappings = conn.execute("SELECT oem_name, offering_details, remarks FROM rfp_boq_oem_mappings WHERE boq_item_id = ?", (item['id'],)).fetchall()
        mapping_dict = {}
        for m in mappings:
            mapping_dict[m['oem_name']] = {
                'model': m['offering_details'] or "",
                'remarks': m['remarks'] or ""
            }
            oems_mapped_set.add(m['oem_name'])
            
        boq_matrix.append({
            'id': item['id'],
            'item_name': item['item_name'],
            'quantity': item['quantity'],
            'mappings': mapping_dict
        })
        
    oems_mapped = sorted(list(oems_mapped_set))
    
    # Query RFP reminders
    rfp_reminders = conn.execute("SELECT * FROM rfp_reminders WHERE rfp_id = ? ORDER BY reminder_date ASC", (rfp_id,)).fetchall()
    
    # Query RFP interactions
    interactions_rows = conn.execute('''
        SELECT i.*, u.username 
        FROM rfp_interactions i
        JOIN users u ON i.user_id = u.id
        WHERE i.rfp_id = ?
        ORDER BY i.interaction_date DESC, i.id DESC
    ''', (rfp_id,)).fetchall()
    
    boq_interactions = [dict(row) for row in interactions_rows if row['section'] == 'boq']
    checklist_interactions = [dict(row) for row in interactions_rows if row['section'] == 'checklist']
    
    conn.close()
    
    return render_template(
        'rfp_detail.html',
        rfp=rfp,
        checklist=checklist,
        documents=documents,
        directory_oems=directory_oems,
        boq_matrix=boq_matrix,
        oems_mapped=oems_mapped,
        rfp_reminders=rfp_reminders,
        boq_interactions=boq_interactions,
        checklist_interactions=checklist_interactions
    )

# ----------------------------------------------------
# RFP Reminders & Follow-ups Routes
# ----------------------------------------------------
@app.route('/rfps/<int:rfp_id>/reminders/add', methods=['POST'])
@login_required
def rfp_reminder_add(rfp_id):
    reminder_date = request.form.get('reminder_date', '').strip()
    task_description = request.form.get('task_description', '').strip()
    
    if not reminder_date or not task_description:
        flash("Date and task description are required.", "error")
        return redirect(url_for('rfp_detail', rfp_id=rfp_id))
        
    conn = database.get_db_connection()
    try:
        conn.execute("""
            INSERT INTO rfp_reminders (rfp_id, reminder_date, task_description, status, created_by)
            VALUES (?, ?, ?, 'pending', ?)
        """, (rfp_id, reminder_date, task_description, session['user_id']))
        conn.commit()
        log_audit('RFP_REMINDER_CREATE', f"Added reminder for RFP ID: {rfp_id}")
        flash("Reminder successfully scheduled.", "success")
    except Exception as e:
        flash(f"Error adding reminder: {e}", "error")
    finally:
        conn.close()
    return redirect(url_for('rfp_detail', rfp_id=rfp_id))

@app.route('/rfps/<int:rfp_id>/reminders/<int:reminder_id>/toggle', methods=['POST'])
@login_required
def rfp_reminder_toggle(rfp_id, reminder_id):
    conn = database.get_db_connection()
    try:
        current = conn.execute("SELECT status FROM rfp_reminders WHERE id = ? AND rfp_id = ?", (reminder_id, rfp_id)).fetchone()
        if current:
            new_status = 'completed' if current['status'] == 'pending' else 'pending'
            conn.execute("UPDATE rfp_reminders SET status = ? WHERE id = ?", (new_status, reminder_id))
            conn.commit()
            log_audit('RFP_REMINDER_TOGGLE', f"Toggled reminder ID {reminder_id} to {new_status}")
            flash(f"Reminder status updated to {new_status}.", "success")
        else:
            flash("Reminder not found.", "error")
    except Exception as e:
        flash(f"Error updating status: {e}", "error")
    finally:
        conn.close()
    return redirect(url_for('rfp_detail', rfp_id=rfp_id))

@app.route('/rfps/<int:rfp_id>/reminders/<int:reminder_id>/delete', methods=['POST'])
@login_required
def rfp_reminder_delete(rfp_id, reminder_id):
    conn = database.get_db_connection()
    try:
        conn.execute("DELETE FROM rfp_reminders WHERE id = ? AND rfp_id = ?", (reminder_id, rfp_id))
        conn.commit()
        log_audit('RFP_REMINDER_DELETE', f"Deleted reminder ID {reminder_id}")
        flash("Reminder deleted successfully.", "success")
    except Exception as e:
        flash(f"Error deleting reminder: {e}", "error")
    finally:
        conn.close()
    return redirect(url_for('rfp_detail', rfp_id=rfp_id))

@app.route('/rfps/reminders/<int:reminder_id>/complete', methods=['POST'])
@login_required
def rfp_reminder_complete_dashboard(reminder_id):
    source = request.args.get('source', 'manual_reminder')
    conn = database.get_db_connection()
    try:
        if source == 'interaction_followup':
            conn.execute("UPDATE rfp_interactions SET followup_status = 'completed' WHERE id = ?", (reminder_id,))
        else:
            conn.execute("UPDATE rfp_reminders SET status = 'completed' WHERE id = ?", (reminder_id,))
        conn.commit()
        log_audit('RFP_REMINDER_COMPLETE_DASHBOARD', f"Marked RFP reminder ID {reminder_id} ({source}) completed from dashboard")
        flash("RFP reminder marked completed.", "success")
    except Exception as e:
        flash(f"Error completing RFP reminder: {e}", "error")
    finally:
        conn.close()
    return redirect(url_for('dashboard'))

# ----------------------------------------------------
# RFP Interactions Routes
# ----------------------------------------------------
@app.route('/rfps/<int:rfp_id>/interactions/add', methods=['POST'])
@login_required
def rfp_interaction_add(rfp_id):
    section = request.form.get('section', '').strip() # 'boq' or 'checklist'
    interaction_date = request.form.get('interaction_date', '').strip()
    summary = request.form.get('summary', '').strip()
    next_steps = request.form.get('next_steps', '').strip()
    followup_date = request.form.get('followup_date', '').strip()
    
    # Handle checkboxes
    types_list = request.form.getlist('type[]')
    types_str = ", ".join(types_list) if types_list else "Other"
    
    if not interaction_date or not summary or section not in ['boq', 'checklist']:
        flash("Date, summary, and valid section are required.", "error")
        return redirect(url_for('rfp_detail', rfp_id=rfp_id))
        
    conn = database.get_db_connection()
    try:
        conn.execute("""
            INSERT INTO rfp_interactions (rfp_id, section, user_id, interaction_date, type, summary, next_steps, followup_date, followup_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        """, (rfp_id, section, session['user_id'], interaction_date, types_str, summary, next_steps, followup_date if followup_date else None))
        conn.commit()
        log_audit('RFP_INTERACTION_CREATE', f"Logged interaction ({types_str}) in section {section} for RFP ID: {rfp_id}")
        flash("Interaction logged successfully.", "success")
    except Exception as e:
        flash(f"Error logging interaction: {e}", "error")
    finally:
        conn.close()
    return redirect(url_for('rfp_detail', rfp_id=rfp_id))

@app.route('/rfps/<int:rfp_id>/interactions/<int:interaction_id>/toggle', methods=['POST'])
@login_required
def rfp_interaction_toggle(rfp_id, interaction_id):
    conn = database.get_db_connection()
    try:
        current = conn.execute("SELECT followup_status FROM rfp_interactions WHERE id = ? AND rfp_id = ?", (interaction_id, rfp_id)).fetchone()
        if current:
            new_status = 'completed' if current['followup_status'] == 'pending' else 'pending'
            conn.execute("UPDATE rfp_interactions SET followup_status = ? WHERE id = ?", (new_status, interaction_id))
            conn.commit()
            log_audit('RFP_INTERACTION_TOGGLE', f"Toggled interaction ID {interaction_id} to {new_status}")
            flash(f"Interaction status updated.", "success")
        else:
            flash("Interaction not found.", "error")
    except Exception as e:
        flash(f"Error updating status: {e}", "error")
    finally:
        conn.close()
    return redirect(url_for('rfp_detail', rfp_id=rfp_id))

@app.route('/rfps/<int:rfp_id>/interactions/<int:interaction_id>/delete', methods=['POST'])
@login_required
def rfp_interaction_delete(rfp_id, interaction_id):
    conn = database.get_db_connection()
    try:
        conn.execute("DELETE FROM rfp_interactions WHERE id = ? AND rfp_id = ?", (interaction_id, rfp_id))
        conn.commit()
        log_audit('RFP_INTERACTION_DELETE', f"Deleted interaction ID {interaction_id}")
        flash("Interaction log entry deleted.", "success")
    except Exception as e:
        flash(f"Error deleting interaction: {e}", "error")
    finally:
        conn.close()
    return redirect(url_for('rfp_detail', rfp_id=rfp_id))

@app.route('/rfps/<int:rfp_id>/update-details', methods=['POST'])
@login_required
def rfp_update_details(rfp_id):
    pre_bid_date = request.form.get('pre_bid_date', '').strip()
    submission_date = request.form.get('submission_date', '').strip()
    contact_name = request.form.get('contact_name', '').strip()
    contact_address = request.form.get('contact_address', '').strip()
    contact_email = request.form.get('contact_email', '').strip()
    contact_phone = request.form.get('contact_phone', '').strip()
    
    title = request.form.get('title', '').strip()
    opportunity_from = request.form.get('opportunity_from', '').strip()
    customer_name = request.form.get('customer_name', '').strip()
    opportunity_date = request.form.get('opportunity_date', '').strip()
    opportunity_type = request.form.get('opportunity_type', '').strip()
    source = request.form.get('source', '').strip()
    opportunity_owner = request.form.get('opportunity_owner', '').strip()
    
    conn = database.get_db_connection()
    try:
        conn.execute("""
            UPDATE rfps 
            SET pre_bid_date = ?, submission_date = ?, contact_name = ?, contact_address = ?, contact_email = ?, contact_phone = ?,
                title = ?, opportunity_from = ?, customer_name = ?, opportunity_date = ?, opportunity_type = ?, source = ?, opportunity_owner = ?
            WHERE id = ?
        """, (pre_bid_date, submission_date, contact_name, contact_address, contact_email, contact_phone,
              title, opportunity_from, customer_name, opportunity_date, opportunity_type, source, opportunity_owner, rfp_id))
        conn.commit()
        log_audit('RFP_UPDATE', f"Updated details for RFP ID: {rfp_id}")
        flash("RFP details successfully updated.", "success")
    except Exception as e:
        flash(f"Error updating RFP details: {e}", "error")
    finally:
        conn.close()
    return redirect(url_for('rfp_detail', rfp_id=rfp_id))

@app.route('/rfps/<int:rfp_id>/save-boq', methods=['POST'])
@login_required
def rfp_save_boq(rfp_id):
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No data received"}), 400
        
    conn = database.get_db_connection()
    try:
        # Clean existing items
        conn.execute("DELETE FROM rfp_boq_items WHERE rfp_id = ?", (rfp_id,))
        
        items = data.get('items', [])
        for item in items:
            item_name = item.get('item_name', '').strip()
            qty = int(item.get('quantity', 1))
            if not item_name:
                continue
                
            cursor = conn.execute("""
                INSERT INTO rfp_boq_items (rfp_id, item_name, quantity)
                VALUES (?, ?, ?)
            """, (rfp_id, item_name, qty))
            boq_item_id = cursor.lastrowid
            
            mappings = item.get('mappings', {})
            for oem_name, details in mappings.items():
                model_val = ""
                remarks_val = ""
                if isinstance(details, dict):
                    model_val = details.get('model', '').strip()
                    remarks_val = details.get('remarks', '').strip()
                else:
                    model_val = str(details).strip()
                conn.execute("""
                    INSERT INTO rfp_boq_oem_mappings (boq_item_id, oem_name, offering_details, remarks)
                    VALUES (?, ?, ?, ?)
                """, (boq_item_id, oem_name.strip(), model_val, remarks_val))
                
        conn.commit()
        log_audit('RFP_BOQ_SAVE', f"Updated BoQ Matrix for RFP ID: {rfp_id}")
        return jsonify({"status": "success", "message": "BoQ Matrix successfully updated."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        conn.close()

@app.route('/rfps/<int:rfp_id>/export-boq-csv')
@login_required
def rfp_export_boq_csv(rfp_id):
    conn = database.get_db_connection()
    rfp = conn.execute("SELECT rfp_number FROM rfps WHERE id = ?", (rfp_id,)).fetchone()
    if not rfp:
        conn.close()
        flash("RFP not found.", "error")
        return redirect(url_for('rfps_list'))
        
    # Fetch BoQ items
    items = conn.execute("SELECT * FROM rfp_boq_items WHERE rfp_id = ? ORDER BY id ASC", (rfp_id,)).fetchall()
    
    # Fetch mapped OEMs to establish header columns
    mappings_all = conn.execute("""
        SELECT DISTINCT oem_name FROM rfp_boq_oem_mappings m
        JOIN rfp_boq_items i ON m.boq_item_id = i.id
        WHERE i.rfp_id = ?
        ORDER BY oem_name
    """, (rfp_id,)).fetchall()
    oems = [m['oem_name'] for m in mappings_all if m['oem_name']]
    
    # Build headers: [BoQ Item / Specification, Qty, OEM1 Model, OEM1 Remarks, OEM2 Model, OEM2 Remarks, ...]
    headers = ['BoQ Item / Specification', 'Qty']
    for oem in oems:
        headers.append(f'{oem} Model')
        headers.append(f'{oem} Remarks')
        
    # Generate CSV response
    import io
    import csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    
    for item in items:
        row = [item['item_name'], item['quantity']]
        
        # Fetch mappings for this item
        mappings_item = conn.execute("SELECT oem_name, offering_details, remarks FROM rfp_boq_oem_mappings WHERE boq_item_id = ?", (item['id'],)).fetchall()
        map_dict = {m['oem_name']: {'model': m['offering_details'] or "", 'remarks': m['remarks'] or ""} for m in mappings_item}
        
        for oem in oems:
            oem_data = map_dict.get(oem, {'model': "", 'remarks': ""})
            row.append(oem_data['model'])
            row.append(oem_data['remarks'])
            
        writer.writerow(row)
        
    conn.close()
    
    csv_data = output.getvalue()
    output.close()
    
    # Format filename: e.g. RFP_GEM-2026-B-99981_BoQ_Matrix.csv
    safe_rfp_num = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in rfp['rfp_number'])
    filename = f"RFP_{safe_rfp_num}_BoQ_Matrix.csv"
    
    from flask import make_response
    response = make_response(csv_data)
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    response.headers["Content-Type"] = "text/csv"
    return response

@app.route('/rfps/<int:rfp_id>/checklist/add', methods=['POST'])
@login_required
def rfp_checklist_add(rfp_id):
    doc_name = request.form.get('doc_name', '').strip()
    doc_description = request.form.get('doc_description', '').strip()
    oem_name = request.form.get('oem_name', '').strip()
    format_file = request.files.get('format_file')
    remarks = request.form.get('remarks', '').strip()
    
    if not doc_name:
        flash("Document Name is required.", "error")
        return redirect(url_for('rfp_detail', rfp_id=rfp_id))
        
    format_file_path = None
    if format_file and format_file.filename:
        # Verify size < 40MB
        format_file.seek(0, os.SEEK_END)
        file_size = format_file.tell()
        format_file.seek(0)
        if file_size > 40 * 1024 * 1024:
            flash("Format file exceeds the allowed 40 MB size limit.", "error")
            return redirect(url_for('rfp_detail', rfp_id=rfp_id))
            
        ext = os.path.splitext(format_file.filename)[1]
        unique_name = f"format_{uuid.uuid4().hex}{ext}"
        format_file.save(os.path.join(UPLOAD_FOLDER, unique_name))
        format_file_path = f"/uploads/{unique_name}"
        
    conn = database.get_db_connection()
    try:
        conn.execute("""
            INSERT INTO rfp_checklist (rfp_id, doc_name, doc_description, oem_name, format_file, remarks)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (rfp_id, doc_name, doc_description, oem_name or None, format_file_path, remarks or None))
        conn.commit()
        flash(f"Checklist item '{doc_name}' added successfully.", "success")
    except Exception as e:
        flash(f"Error adding checklist item: {e}", "error")
    finally:
        conn.close()
    return redirect(url_for('rfp_detail', rfp_id=rfp_id))

@app.route('/rfps/<int:rfp_id>/checklist/<int:item_id>/toggle', methods=['POST'])
@login_required
def rfp_checklist_toggle(rfp_id, item_id):
    conn = database.get_db_connection()
    try:
        item = conn.execute("SELECT status, doc_name FROM rfp_checklist WHERE id = ? AND rfp_id = ?", (item_id, rfp_id)).fetchone()
        if not item:
            conn.close()
            return jsonify({"status": "error", "message": "Checklist item not found."}), 404
            
        new_status = 'Received' if item['status'] == 'Not Received' else 'Not Received'
        conn.execute("UPDATE rfp_checklist SET status = ? WHERE id = ?", (new_status, item_id))
        conn.commit()
        log_audit('RFP_CHECKLIST_TOGGLE', f"Toggled status of checklist item: {item['doc_name']} to {new_status}")
        return jsonify({"status": "success", "new_status": new_status})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        conn.close()

@app.route('/rfps/<int:rfp_id>/checklist/<int:item_id>/delete', methods=['POST'])
@login_required
def rfp_checklist_delete(rfp_id, item_id):
    conn = database.get_db_connection()
    try:
        conn.execute("DELETE FROM rfp_checklist WHERE id = ? AND rfp_id = ?", (item_id, rfp_id))
        conn.commit()
        flash("Checklist item successfully removed.", "success")
    except Exception as e:
        flash(f"Error deleting checklist item: {e}", "error")
    finally:
        conn.close()
    return redirect(url_for('rfp_detail', rfp_id=rfp_id))

@app.route('/rfps/<int:rfp_id>/checklist/<int:item_id>/clone', methods=['POST'])
@login_required
def rfp_checklist_clone(rfp_id, item_id):
    conn = database.get_db_connection()
    try:
        item = conn.execute("SELECT doc_name, doc_description, format_file FROM rfp_checklist WHERE id = ? AND rfp_id = ?", (item_id, rfp_id)).fetchone()
        if item:
            conn.execute("""
                INSERT INTO rfp_checklist (rfp_id, doc_name, doc_description, format_file, status)
                VALUES (?, ?, ?, ?, 'Not Received')
            """, (rfp_id, item['doc_name'], item['doc_description'], item['format_file']))
            conn.commit()
            flash(f"Added another submission row for '{item['doc_name']}'.", "success")
        else:
            flash("Checklist item not found.", "error")
    except Exception as e:
        flash(f"Error cloning checklist item: {e}", "error")
    finally:
        conn.close()
    return redirect(url_for('rfp_detail', rfp_id=rfp_id))

@app.route('/rfps/<int:rfp_id>/checklist/<int:item_id>/upload', methods=['POST'])
@login_required
def rfp_checklist_upload_doc(rfp_id, item_id):
    file = request.files.get('uploaded_file')
    if not file or not file.filename:
        flash("No file selected.", "error")
        return redirect(url_for('rfp_detail', rfp_id=rfp_id))
        
    # Check size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > 40 * 1024 * 1024:
        flash("File exceeds the 40 MB size limit.", "error")
        return redirect(url_for('rfp_detail', rfp_id=rfp_id))
        
    ext = os.path.splitext(file.filename)[1]
    unique_name = f"doc_{uuid.uuid4().hex}{ext}"
    file.save(os.path.join(UPLOAD_FOLDER, unique_name))
    uploaded_file_path = f"/uploads/{unique_name}"
    
    conn = database.get_db_connection()
    try:
        conn.execute("""
            UPDATE rfp_checklist 
            SET uploaded_file = ?, status = 'Received' 
            WHERE id = ? AND rfp_id = ?
        """, (uploaded_file_path, item_id, rfp_id))
        conn.commit()
        flash("Document uploaded successfully.", "success")
    except Exception as e:
        flash(f"Error uploading document: {e}", "error")
    finally:
        conn.close()
    return redirect(url_for('rfp_detail', rfp_id=rfp_id))

@app.route('/rfps/<int:rfp_id>/checklist/<int:item_id>/upload-format', methods=['POST'])
@login_required
def rfp_checklist_upload_format(rfp_id, item_id):
    file = request.files.get('format_file')
    if not file or not file.filename:
        flash("No file selected.", "error")
        return redirect(url_for('rfp_detail', rfp_id=rfp_id))
        
    # Check size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > 40 * 1024 * 1024:
        flash("File exceeds the 40 MB size limit.", "error")
        return redirect(url_for('rfp_detail', rfp_id=rfp_id))
        
    ext = os.path.splitext(file.filename)[1]
    unique_name = f"format_{uuid.uuid4().hex}{ext}"
    file.save(os.path.join(UPLOAD_FOLDER, unique_name))
    format_file_path = f"/uploads/{unique_name}"
    
    conn = database.get_db_connection()
    try:
        conn.execute("""
            UPDATE rfp_checklist 
            SET format_file = ? 
            WHERE id = ? AND rfp_id = ?
        """, (format_file_path, item_id, rfp_id))
        conn.commit()
        flash("Template format file uploaded successfully.", "success")
    except Exception as e:
        flash(f"Error uploading format file: {e}", "error")
    finally:
        conn.close()
    return redirect(url_for('rfp_detail', rfp_id=rfp_id))

@app.route('/rfps/<int:rfp_id>/checklist/<int:item_id>/update-oem', methods=['POST'])
@login_required
def rfp_checklist_update_oem(rfp_id, item_id):
    oem_name = request.form.get('oem_name', '').strip()
    conn = database.get_db_connection()
    try:
        conn.execute("UPDATE rfp_checklist SET oem_name = ? WHERE id = ? AND rfp_id = ?", (oem_name or None, item_id, rfp_id))
        conn.commit()
        return jsonify({"status": "success", "message": "OEM updated."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        conn.close()

@app.route('/rfps/<int:rfp_id>/checklist/<int:item_id>/update-remarks', methods=['POST'])
@login_required
def rfp_checklist_update_remarks(rfp_id, item_id):
    remarks = request.form.get('remarks', '').strip()
    conn = database.get_db_connection()
    try:
        conn.execute("UPDATE rfp_checklist SET remarks = ? WHERE id = ? AND rfp_id = ?", (remarks or None, item_id, rfp_id))
        conn.commit()
        return jsonify({"status": "success", "message": "Remarks updated."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        conn.close()

@app.route('/rfps/<int:rfp_id>/checklist/<int:item_id>/delete-doc', methods=['POST'])
@login_required
def rfp_checklist_delete_doc(rfp_id, item_id):
    conn = database.get_db_connection()
    try:
        conn.execute("UPDATE rfp_checklist SET uploaded_file = NULL, status = 'Not Received' WHERE id = ? AND rfp_id = ?", (item_id, rfp_id))
        conn.commit()
        flash("Checklist document removed successfully.", "success")
    except Exception as e:
        flash(f"Error removing document: {e}", "error")
    finally:
        conn.close()
    return redirect(url_for('rfp_detail', rfp_id=rfp_id))

@app.route('/rfps/<int:rfp_id>/checklist/<int:item_id>/delete-format', methods=['POST'])
@login_required
def rfp_checklist_delete_format(rfp_id, item_id):
    conn = database.get_db_connection()
    try:
        conn.execute("UPDATE rfp_checklist SET format_file = NULL WHERE id = ? AND rfp_id = ?", (item_id, rfp_id))
        conn.commit()
        flash("Template format file removed successfully.", "success")
    except Exception as e:
        flash(f"Error removing format file: {e}", "error")
    finally:
        conn.close()
    return redirect(url_for('rfp_detail', rfp_id=rfp_id))

@app.route('/rfps/<int:rfp_id>/export-checklist-csv')
@login_required
def rfp_export_checklist_csv(rfp_id):
    conn = database.get_db_connection()
    rfp = conn.execute("SELECT rfp_number FROM rfps WHERE id = ?", (rfp_id,)).fetchone()
    if not rfp:
        conn.close()
        flash("RFP not found.", "error")
        return redirect(url_for('rfps_list'))
        
    # Fetch checklist items
    items = conn.execute("SELECT * FROM rfp_checklist WHERE rfp_id = ? ORDER BY id ASC", (rfp_id,)).fetchall()
    conn.close()
    
    # Generate CSV response
    import io
    import csv
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers
    writer.writerow([
        'Document Type', 
        'Description', 
        'Associated OEM', 
        'Submission Status', 
        'Format Template Path', 
        'Uploaded Document Path',
        'Remarks'
    ])
    
    for item in items:
        oem = item['oem_name'] if item['oem_name'] else 'General / All'
        format_file = item['format_file'] if item['format_file'] else 'No Template'
        uploaded_file = item['uploaded_file'] if item['uploaded_file'] else 'Not Submitted'
        
        writer.writerow([
            item['doc_name'],
            item['doc_description'] or '',
            oem,
            item['status'],
            format_file,
            uploaded_file,
            item['remarks'] or ''
        ])
        
    csv_data = output.getvalue()
    output.close()
    
    # Format filename: e.g. RFP_GEM-2026-B-99981_Checklist.csv
    safe_rfp_num = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in rfp['rfp_number'])
    filename = f"RFP_{safe_rfp_num}_Checklist.csv"
    
    from flask import make_response
    response = make_response(csv_data)
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    response.headers["Content-Type"] = "text/csv"
    return response



@app.route('/rfps/<int:rfp_id>/upload', methods=['POST'])
@login_required
def rfp_document_upload(rfp_id):
    if 'file' not in request.files:
        flash("No file part.", "error")
        return redirect(url_for('rfp_detail', rfp_id=rfp_id))
        
    file = request.files['file']
    doc_type = request.form.get('doc_type', 'rfp').strip()
    
    if file.filename == '':
        flash("No file selected.", "error")
        return redirect(url_for('rfp_detail', rfp_id=rfp_id))
        
    # Enforce 40 MB max file size limit
    MAX_SIZE_BYTES = 40 * 1024 * 1024
    
    # Read size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > MAX_SIZE_BYTES:
        flash(f"File size exceeds 40 MB limit (Selected file size: {file_size / (1024*1024):.2f} MB). Please compress or split the file.", "error")
        return redirect(url_for('rfp_detail', rfp_id=rfp_id))
        
    ext = os.path.splitext(file.filename)[1].lower()
    
    import uuid
    original_name = file.filename
    safe_filename = f"rfp_{rfp_id}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
    
    try:
        file.save(filepath)
        conn = database.get_db_connection()
        conn.execute("""
            INSERT INTO rfp_documents (rfp_id, filename, original_name, doc_type, file_size)
            VALUES (?, ?, ?, ?, ?)
        """, (rfp_id, safe_filename, original_name, doc_type, file_size))
        conn.commit()
        conn.close()
        
        log_audit('RFP_DOC_UPLOAD', f"Uploaded {doc_type}: {original_name} for RFP ID: {rfp_id}")
        flash(f"Document '{original_name}' uploaded successfully.", "success")
    except Exception as e:
        flash(f"Error saving document: {e}", "error")
        
    return redirect(url_for('rfp_detail', rfp_id=rfp_id))

@app.route('/rfps/<int:rfp_id>/document/<int:doc_id>/delete', methods=['POST'])
@login_required
def rfp_document_delete(rfp_id, doc_id):
    conn = database.get_db_connection()
    try:
        doc = conn.execute("SELECT filename, original_name FROM rfp_documents WHERE id = ? AND rfp_id = ?", (doc_id, rfp_id)).fetchone()
        if doc:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], doc['filename'])
            if os.path.exists(filepath):
                os.remove(filepath)
            conn.execute("DELETE FROM rfp_documents WHERE id = ?", (doc_id,))
            conn.commit()
            log_audit('RFP_DOC_DELETE', f"Deleted document: {doc['original_name']} from RFP ID: {rfp_id}")
            flash(f"Document '{doc['original_name']}' successfully deleted.", "success")
        else:
            flash("Document record not found.", "error")
    except Exception as e:
        flash(f"Error deleting document: {e}", "error")
    finally:
        conn.close()
    return redirect(url_for('rfp_detail', rfp_id=rfp_id))

@app.route('/rfps/<int:rfp_id>/delete', methods=['POST'])
@login_required
def rfp_delete(rfp_id):
    conn = database.get_db_connection()
    try:
        rfp = conn.execute("SELECT rfp_number FROM rfps WHERE id = ?", (rfp_id,)).fetchone()
        if not rfp:
            conn.close()
            flash("RFP not found.", "error")
            return redirect(url_for('rfps_list'))
            
        docs = conn.execute("SELECT filename FROM rfp_documents WHERE rfp_id = ?", (rfp_id,)).fetchall()
        for doc in docs:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], doc['filename'])
            if os.path.exists(filepath):
                try: os.remove(filepath)
                except: pass
                
        conn.execute("DELETE FROM rfps WHERE id = ?", (rfp_id,))
        conn.commit()
        log_audit('RFP_DELETE', f"Deleted Master RFP: {rfp['rfp_number']}")
        flash(f"RFP '{rfp['rfp_number']}' and all its associated documents/data have been permanently deleted.", "success")
    except Exception as e:
        flash(f"Error deleting RFP: {e}", "error")
    finally:
        conn.close()
    return redirect(url_for('rfps_list'))

# Initialize DB tables on import/startup (crucial for Passenger WSGI cPanel migrations)
database.init_db()

def run_oem_news_fetch_thread(user_id=None, username=None):
    import concurrent.futures
    from scraper import fetch_oem_news_rss
    
    conn = database.get_db_connection()
    try:
        # Get all unique OEMs
        rows = conn.execute("SELECT DISTINCT company_name FROM contacts ORDER BY company_name").fetchall()
        oems = [r['company_name'] for r in rows if r['company_name']]
        
        if not oems:
            conn.close()
            return
            
        print(f"Concurrent OEM news fetch starting for {len(oems)} OEMs...")
        all_articles = []
        
        # Parallel fetch with 10 threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_oem = {executor.submit(fetch_oem_news_rss, oem): oem for oem in oems}
            for future in concurrent.futures.as_completed(future_to_oem):
                oem = future_to_oem[future]
                try:
                    articles = future.result()
                    if articles:
                        all_articles.extend(articles)
                except Exception as exc:
                    print(f"OEM {oem} fetch generated an exception: {exc}")
                    
        # Persist to database
        added_count = 0
        for art in all_articles:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO oem_news (oem_name, title, link, pub_date, source, snippet)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (art['oem_name'], art['title'], art['link'], art['pub_date'], art['source'], art['snippet']))
                added_count += 1
            except Exception as e:
                pass
        conn.commit()
        
        # Log audit log entry
        if username:
            conn.execute("INSERT INTO audit_logs (user_id, action, details) VALUES ((SELECT id FROM users WHERE username = ?), ?, ?)",
                         (username, 'NEWS_FETCH_SUCCESS', f"OEM news successfully refreshed. Checked {len(oems)} OEMs and cached articles."))
        else:
            conn.execute("INSERT INTO audit_logs (user_id, action, details) VALUES (NULL, ?, ?)",
                         ('NEWS_FETCH_SUCCESS', f"Automated nightly news fetch completed. Checked {len(oems)} OEMs and cached articles."))
        conn.commit()
    except Exception as e:
        print(f"Error in background news fetch: {e}")
    finally:
        conn.close()

@app.route('/news')
@login_required
def oem_news_page():
    conn = database.get_db_connection()
    # Fetch all news
    news_rows = conn.execute("SELECT * FROM oem_news ORDER BY id DESC").fetchall()
    
    # Get list of unique OEMs that have news
    oems_rows = conn.execute("SELECT DISTINCT oem_name FROM oem_news ORDER BY oem_name").fetchall()
    oems = [r['oem_name'] for r in oems_rows]
    
    # If no news cached, also query unique OEMs from directory contacts to show in filter
    if not oems:
        contacts_rows = conn.execute("SELECT DISTINCT company_name FROM contacts ORDER BY company_name").fetchall()
        oems = [r['company_name'] for r in contacts_rows if r['company_name']]
        
    # Get last successful sync timestamp
    last_sync_row = conn.execute("SELECT created_at FROM audit_logs WHERE action = 'NEWS_FETCH_SUCCESS' ORDER BY id DESC LIMIT 1").fetchone()
    last_fetch = last_sync_row['created_at'] if last_sync_row else None
    
    conn.close()
    
    return render_template(
        'news.html',
        news_list=news_rows,
        oems=oems,
        last_fetch=last_fetch
    )

@app.route('/news/fetch', methods=['POST'])
@login_required
def fetch_news_manually():
    import threading
    t = threading.Thread(target=run_oem_news_fetch_thread, args=(session.get('user_id'), session.get('username')))
    t.daemon = True
    t.start()
    t.join(4.0) # Wait up to 4 seconds for fast concurrent thread pool completion
    
    flash("OEM News fetch completed or running in the background. The latest announcements have been synced.", "success")
    return redirect(url_for('oem_news_page'))

if __name__ == '__main__':
    # Run locally (accessible on local network: host='0.0.0.0' makes it accessible by team)
    app.run(host='0.0.0.0', port=5000, debug=True)
