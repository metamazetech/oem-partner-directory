import os
import uuid
import tempfile
import time
import shutil
from flask import Blueprint, render_template, request, jsonify, Response, send_file, after_this_request
from werkzeug.utils import secure_filename
from excel_utils import process_file_in_background, log_status

excel_bp = Blueprint('excel_tool', __name__, template_folder='templates')

@excel_bp.route('/excel', methods=['GET'])
def index():
    return render_template('excel_tool.html')

@excel_bp.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if not file.filename.lower().endswith(('.xls', '.xlsx', '.xlsm')):
        return jsonify({"error": "Invalid file type. Only .xls, .xlsx, or .xlsm files are supported."}), 400

    mode = request.form.get('mode')
    password = request.form.get('password', '')

    if mode not in ['file_encryption', 'sheet_protection']:
        return jsonify({"error": "Invalid mode"}), 400

    job_id = str(uuid.uuid4())
    job_dir = os.path.join(tempfile.gettempdir(), job_id)
    os.makedirs(job_dir, exist_ok=True)

    filename = secure_filename(file.filename)
    input_path = os.path.join(job_dir, f"input_{filename}")
    
    name, ext = os.path.splitext(filename)
    output_filename = f"{name}_unlocked{ext}"
    output_path = os.path.join(job_dir, output_filename)

    file.save(input_path)

    log_status(job_dir, "File uploaded, starting processing...")

    process_file_in_background(input_path, output_path, mode, password, job_dir)

    return jsonify({
        "job_id": job_id,
        "output_filename": output_filename
    })

@excel_bp.route('/stream/<job_id>')
def stream_logs(job_id):
    job_dir = os.path.join(tempfile.gettempdir(), job_id)
    log_file = os.path.join(job_dir, "log.txt")

    def generate():
        with open(log_file, "a"):
            pass
        
        with open(log_file, "r") as f:
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.5)
                    continue
                
                yield f"data: {line}\n\n"
                if "PROCESS_COMPLETE" in line:
                    break
    
    return Response(generate(), mimetype='text/event-stream')

@excel_bp.route('/download/<job_id>/<filename>')
def download_file(job_id, filename):
    job_dir = os.path.join(tempfile.gettempdir(), job_id)
    output_path = os.path.join(job_dir, filename)

    if not os.path.exists(output_path):
        return "File not found", 404

    @after_this_request
    def remove_job_dir(response):
        try:
            shutil.rmtree(job_dir, ignore_errors=True)
        except Exception as e:
            print(f"Error removing job dir: {e}")
        return response

    return send_file(output_path, as_attachment=True, download_name=filename)
