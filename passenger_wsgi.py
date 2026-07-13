import sys
import os

# Add project root directory to python path
sys.path.insert(0, os.path.dirname(__file__))

# Expose WSGI application callable with startup crash logging
try:
    from app import app as application
except Exception as e:
    # Write startup error to a log file inside the app folder for easy debugging
    with open(os.path.join(os.path.dirname(__file__), 'startup_error.log'), 'a') as f:
        import traceback
        import datetime
        f.write(f"--- Startup Crash Logged at {datetime.datetime.now()} ---\n")
        traceback.print_exc(file=f)
        f.write("\n")
    raise e

