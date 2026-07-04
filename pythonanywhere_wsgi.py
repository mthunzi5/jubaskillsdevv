"""PythonAnywhere WSGI entry point for Juba Skills LMS.

Update `project_home` if the repository folder name changes.
"""

import os
import sys

project_home = '/home/JubaSkills/jubaskillsdevv'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.environ.setdefault('FLASK_ENV', 'production')

from dotenv import load_dotenv

load_dotenv(os.path.join(project_home, '.env'))

from app import create_app

application = create_app('production')
application.debug = False
