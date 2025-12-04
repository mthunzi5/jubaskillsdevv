# PythonAnywhere Deployment Guide

## Prerequisites
- PythonAnywhere account (free or paid)
- Git installed on PythonAnywhere
- Basic knowledge of Linux commands

## Step-by-Step Deployment

### 1. Prepare Your PythonAnywhere Account

1. Sign up at https://www.pythonanywhere.com
2. Open a Bash console from the dashboard

### 2. Clone the Repository

```bash
cd ~
git clone https://github.com/mthunzi5/jubaskillsdevv.git
cd jubaskillsdevv
```

### 3. Create Virtual Environment

```bash
mkvirtualenv --python=/usr/bin/python3.10 jubalmss
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
nano .env
```

Add the following (replace with your actual values):
```env
SECRET_KEY=generate-a-strong-random-key-here
JWT_SECRET_KEY=generate-another-strong-key-here
DATABASE_URI=sqlite:////home/yourusername/jubaskillsdevv/instance/juba_lms.db
UPLOAD_FOLDER=uploads/timesheets
MAX_CONTENT_LENGTH=16777216
FLASK_ENV=production
```

**Generate secure keys:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Press `Ctrl+X`, then `Y`, then `Enter` to save.

### 5. Initialize Database

```bash
export FLASK_APP=app
flask db upgrade
```

### 6. Configure Web App

1. Go to PythonAnywhere **Web** tab
2. Click **Add a new web app**
3. Choose **Manual configuration**
4. Select **Python 3.10**
5. Click through the setup

### 7. Configure WSGI File

1. In the Web tab, find **Code** section
2. Click on the WSGI configuration file link
3. **Delete all existing code**
4. Replace with:

```python
"""
WSGI configuration for Juba LMS on PythonAnywhere
"""
import sys
import os

# Add your project directory to the sys.path
project_home = '/home/yourusername/jubaskillsdevv'  # CHANGE yourusername
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# Load environment variables
from dotenv import load_dotenv
env_path = os.path.join(project_home, '.env')
load_dotenv(env_path)

# Import the application
from app import create_app

application = create_app()
```

⚠️ **IMPORTANT**: Replace `yourusername` with your actual PythonAnywhere username!

### 8. Configure Static Files

In the Web tab, scroll to **Static files** section:

| URL | Directory |
|-----|-----------|
| `/static/` | `/home/yourusername/jubaskillsdevv/app/static/` |

### 9. Configure Virtual Environment

In the Web tab, find **Virtualenv** section:
- Enter: `/home/yourusername/.virtualenvs/jubalmss`

### 10. Create Required Directories

```bash
cd ~/jubaskillsdevv
mkdir -p instance
mkdir -p app/static/materials
mkdir -p app/static/tasks
mkdir -p app/static/request_hub
mkdir -p app/static/submission_receipts
mkdir -p uploads/timesheets
```

### 11. Set Permissions

```bash
chmod 755 instance
chmod 755 app/static/*
chmod 755 uploads/timesheets
```

### 12. Reload Web App

In the Web tab, click the green **Reload** button.

### 13. Access Your Application

Your app will be available at:
- Free account: `http://yourusername.pythonanywhere.com`
- Paid account: Can use custom domain

## Post-Deployment Tasks

### Change Default Admin Password

1. Visit your application URL
2. Log in with default credentials:
   - Email: `admin@juba.ac.za`
   - Password: `Admin@2025`
3. Go to **Change Password** and update immediately!

### Create Initial Users

1. Log in as admin
2. Go to **Users** → **Create User**
3. Create staff and intern accounts

### Upload Training Materials

1. Log in as staff
2. Go to **Training Materials** → **Upload Material**

## Updating Your Deployment

### Pull Latest Changes

```bash
cd ~/jubaskillsdevv
git pull origin main
workon jubalmss
pip install -r requirements.txt
flask db upgrade
```

Then reload your web app in the Web tab.

## Database Management

### Backup Database

```bash
cd ~/jubaskillsdevv
cp instance/juba_lms.db instance/juba_lms_backup_$(date +%Y%m%d).db
```

### Reset Database (CAUTION!)

```bash
cd ~/jubaskillsdevv
rm instance/*.db
rm -rf migrations/
export FLASK_APP=app
flask db init
flask db migrate -m "Fresh database"
flask db upgrade
```

## Troubleshooting

### Error Logs

View error logs in PythonAnywhere:
1. Go to **Web** tab
2. Scroll to **Log files**
3. Check **Error log** and **Server log**

### Common Issues

#### 1. Import Errors
**Problem**: `ModuleNotFoundError`
**Solution**: 
```bash
workon jubalmss
pip install -r requirements.txt
```

#### 2. Database Locked
**Problem**: `database is locked`
**Solution**: 
```bash
# Check for stale connections
lsof ~/jubaskillsdevv/instance/juba_lms.db
# Kill the process if needed
```

#### 3. Static Files Not Loading
**Problem**: CSS/JS not loading
**Solution**: 
- Verify static files mapping in Web tab
- Check paths are correct with your username
- Reload web app

#### 4. Permission Denied
**Problem**: `Permission denied` on uploads
**Solution**:
```bash
chmod -R 755 ~/jubaskillsdevv/uploads/
chmod -R 755 ~/jubaskillsdevv/app/static/
```

#### 5. 502 Bad Gateway
**Problem**: Application won't start
**Solution**: 
- Check WSGI file has correct username
- Check virtual environment path is correct
- Review error log for details

### Debug Mode

To enable detailed error messages temporarily:

In WSGI file, add before `application = create_app()`:
```python
import os
os.environ['FLASK_DEBUG'] = '1'
```

⚠️ **Remove this before going to production!**

## Performance Optimization

### Enable Compression

In WSGI file, add:
```python
from flask_compress import Compress
Compress(application)
```

Then install:
```bash
workon jubalmss
pip install flask-compress
```

### Database Connection Pooling

For PostgreSQL (recommended for production):

1. Create PostgreSQL database in PythonAnywhere
2. Update `.env`:
```env
DATABASE_URI=postgresql://username:password@hostname/database
```
3. Install driver:
```bash
pip install psycopg2-binary
```

## Scheduled Tasks

### Set up Recurring Request Generator

In PythonAnywhere **Tasks** tab:

**Daily task at 00:00**:
```bash
cd /home/yourusername/jubaskillsdevv && /home/yourusername/.virtualenvs/jubalmss/bin/python -c "from app import create_app; from app.utils.recurring import generate_recurring_requests; app = create_app(); app.app_context().push(); generate_recurring_requests()"
```

## Security Checklist

- [ ] Changed default admin password
- [ ] Set strong `SECRET_KEY` and `JWT_SECRET_KEY`
- [ ] Set `FLASK_ENV=production` in `.env`
- [ ] Removed debug mode from WSGI
- [ ] Configured proper database permissions
- [ ] Set up HTTPS (automatic on PythonAnywhere)
- [ ] Regular database backups scheduled

## Monitoring

### Check Application Health

```bash
cd ~/jubaskillsdevv
workon jubalmss
python -c "from app import create_app; app = create_app(); print('OK')"
```

### Monitor Disk Space

```bash
df -h
du -sh ~/jubaskillsdevv/
```

## Support

- PythonAnywhere Help: https://help.pythonanywhere.com
- Flask Documentation: https://flask.palletsprojects.com
- GitHub Issues: https://github.com/mthunzi5/jubaskillsdevv/issues

---

**Deployment Version**: 1.0.0  
**Last Updated**: December 4, 2025
