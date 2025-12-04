"""
WSGI entry point for PythonAnywhere deployment
"""
import sys
import os

# Add your project directory to the sys.path
project_home = '/home/yourusername/jubalmss'  # Update with your PythonAnywhere username
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# Set environment variables
os.environ['FLASK_APP'] = 'app'
os.environ['FLASK_ENV'] = 'production'

# Import the application
from app import create_app

application = create_app()

# For debugging (remove in production)
# import logging
# logging.basicConfig(level=logging.DEBUG)
