# WSGI Configuration for PythonAnywhere
# Replace 'yourusername' with your actual PythonAnywhere username

import sys
import os

# Add your project directory to the sys.path
project_home = '/home/yourusername/jubalmss'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment variables
os.environ['FLASK_ENV'] = 'production'
os.environ['SECRET_KEY'] = 'change-this-to-a-random-secret-key-in-production'

# Import Flask app
from run import app as application

# For debugging (remove in production)
application.debug = False
