import os
import tempfile
import uuid
import threading
import msoffcrypto
import openpyxl
from datetime import datetime

def log_status(job_dir, message):
    log_file = os.path.join(job_dir, "log.txt")
    with open(log_file, "a") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")

def remove_file_encryption(input_path, output_path, password, job_dir):
    try:
        log_status(job_dir, "Starting file encryption removal using password...")
        with open(input_path, "rb") as f_in:
            file = msoffcrypto.OfficeFile(f_in)
            file.load_key(password=password)
            with open(output_path, "wb") as f_out:
                file.decrypt(f_out)
        log_status(job_dir, "File decrypted successfully.")
        log_status(job_dir, "PROCESS_COMPLETE")
    except Exception as e:
        log_status(job_dir, f"Error: {str(e)}")
        log_status(job_dir, "PROCESS_COMPLETE")

def remove_sheet_protection(input_path, output_path, job_dir):
    try:
        log_status(job_dir, "Starting sheet/workbook protection removal...")
        is_xlsm = input_path.lower().endswith('.xlsm')
        wb = openpyxl.load_workbook(input_path, keep_vba=is_xlsm)
        
        # Remove workbook protection
        if wb.security:
            wb.security.workbookPassword = None
            wb.security.lockStructure = False
            wb.security.lockWindows = False
            log_status(job_dir, "Workbook protection removed.")

        # Remove sheet protection
        for sheet in wb.worksheets:
            if sheet.protection.sheet:
                sheet.protection.disable()
                log_status(job_dir, f"Protection removed from sheet: {sheet.title}")

        wb.save(output_path)
        wb.close()
        log_status(job_dir, "File saved successfully without protection.")
        log_status(job_dir, "PROCESS_COMPLETE")
    except Exception as e:
        log_status(job_dir, f"Error: {str(e)}")
        log_status(job_dir, "PROCESS_COMPLETE")

def process_file_in_background(input_path, output_path, mode, password, job_dir):
    if mode == "file_encryption":
        thread = threading.Thread(target=remove_file_encryption, args=(input_path, output_path, password, job_dir))
    elif mode == "sheet_protection":
        thread = threading.Thread(target=remove_sheet_protection, args=(input_path, output_path, job_dir))
    else:
        log_status(job_dir, "Invalid mode selected.")
        log_status(job_dir, "PROCESS_COMPLETE")
        return
    
    thread.start()
