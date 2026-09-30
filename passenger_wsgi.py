import os
import sys

# Set up paths for cPanel
sys.path.insert(0, os.path.dirname(__file__))

# Provide application object for Passenger WSGI
from app import app as application
