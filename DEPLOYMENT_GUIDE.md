# Juba Skills LMS - PythonAnywhere Deployment Guide

## Step 1: Create PythonAnywhere Account
1. Go to https://www.pythonanywhere.com/registration/register/beginner/
2. Sign up for a FREE Beginner account
3. Verify your email
4. Login to your dashboard

## Step 2: Upload Your Code

### Option A: Using Git (Recommended)
1. In PythonAnywhere dashboard, click "Consoles" tab
2. Start a new "Bash" console
3. Run these commands:
```bash
git clone https://github.com/mthunzi5/JubaLms.git jubalmss
cd jubalmss
```

### Option B: Manual Upload
1. Click "Files" tab
2. Navigate to home directory
3. Create folder: jubalmss
4. Upload all your files (drag and drop)

## Step 3: Create Virtual Environment
In Bash console:
```bash
cd ~/jubalmss
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Step 4: Setup Web App
1. Click "Web" tab
2. Click "Add a new web app"
3. Choose "Manual configuration"
4. Select "Python 3.10"
5. Click "Next"

## Step 5: Configure WSGI File
1. In "Web" tab, find "Code" section
2. Click on WSGI configuration file link (e.g., /var/www/yourusername_pythonanywhere_com_wsgi.py)
3. Delete all content and replace with:

```python
import sys
import os

# Add your project directory to the sys.path
project_home = '/home/yourusername/jubalmss'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment variables
os.environ['FLASK_ENV'] = 'production'

# Import Flask app
from run import app as application
```

**IMPORTANT**: Replace `yourusername` with YOUR actual PythonAnywhere username

## Step 6: Configure Virtual Environment
1. In "Web" tab, find "Virtualenv" section
2. Enter path: `/home/yourusername/jubalmss/venv`
3. Click checkmark to save

## Step 7: Configure Static Files
In "Web" tab, "Static files" section, add:
- URL: `/static/`
- Directory: `/home/yourusername/jubalmss/app/static/`

## Step 8: Set Environment Variables (Optional)
1. Click "Web" tab
2. Scroll to "Environment variables" section
3. Add:
   - SECRET_KEY: your-secret-key-here
   - FLASK_ENV: production

## Step 9: Create Database and Admin
In Bash console:
```bash
cd ~/jubalmss
source venv/bin/activate
python
```

Then in Python:
```python
from app import create_app, db
from app.utils.helpers import create_default_admin

app = create_app('production')
with app.app_context():
    db.create_all()
    create_default_admin()
    print("Database created and admin account ready!")
exit()
```

## Step 10: Reload Web App
1. Go to "Web" tab
2. Click big green "Reload" button
3. Click on your site URL: https://yourusername.pythonanywhere.com

## Step 11: Test Your App
1. Visit your site URL
2. Login with: admin@juba.ac.za / Admin@2025
3. Test all features

## Troubleshooting

### Error Logs
- Click "Web" tab
- Scroll to "Log files" section
- Check error.log and server.log

### Common Issues

**1. Import errors:**
```bash
cd ~/jubalmss
source venv/bin/activate
pip install -r requirements.txt
```

**2. Database not found:**
- Check instance folder exists: `mkdir -p instance`
- Ensure database path in config.py is correct

**3. Static files not loading:**
- Verify static files mapping in Web tab
- Check folder permissions: `chmod -R 755 app/static`

**4. File upload errors:**
- Create upload directories:
```bash
mkdir -p app/static/submissions
mkdir -p app/static/materials
mkdir -p app/static/board_attachments
mkdir -p uploads/timesheets
chmod -R 755 app/static uploads
```

## Maintenance

### Update Code
```bash
cd ~/jubalmss
git pull origin main
# Then click "Reload" in Web tab
```

### Backup Database
```bash
cd ~/jubalmss/instance
cp juba_lms.db juba_lms_backup_$(date +%Y%m%d).db
```

### View Logs
```bash
# Error log
tail -f /var/log/yourusername.pythonanywhere.com.error.log

# Server log
tail -f /var/log/yourusername.pythonanywhere.com.server.log
```

## Important Notes
- Free tier has 512MB storage limit
- Must login to PythonAnywhere every 3 months
- Site runs 24/7 without sleep
- Your URL: https://yourusername.pythonanywhere.com
- Can upgrade to paid plan for custom domain

## Next Steps After Deployment
1. Change admin password immediately
2. Test all features (upload, download, create tasks, etc.)
3. Create staff and intern test accounts
4. Monitor error logs for first few days
5. Set calendar reminder to login every 3 months
