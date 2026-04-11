# PythonAnywhere Deployment Guide - JUBA LMS

## ✅ You are here: Repository cloned successfully!

Current location: `~/jubaskillsdevv`

---

## 📋 Step-by-Step Deployment

### 1. Create Virtual Environment
```bash
cd ~/jubaskillsdevv
mkvirtualenv --python=/usr/bin/python3.10 jubalmss
```

### 2. Install Dependencies
```bash
workon jubalmss
pip install -r requirements.txt
```

### 3. Set Up Environment Variables
```bash
cp .env.example .env
nano .env
```

**Edit the .env file with these values:**
```bash
SECRET_KEY=om_e1f6UjuFV4-kmOuYuUIJzLGAW8w5idoZzrVW_fqQ
JWT_SECRET_KEY=3df0qVGZIUPq8Ekfwf7hNKanIeAjxZEfXtQ2iN6kCOc
DATABASE_URI=sqlite:////home/JubaSkills/jubaskillsdevv/instance/juba_lms.db
FLASK_ENV=production
FLASK_DEBUG=0 
```

**To generate secure keys, run:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```
Run this twice to get two different keys.

### 4. Initialize Database
```bash
    workon jubalmss
export FLASK_APP=app
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

**Default admin will be created automatically:**
- Email: `admin@juba.ac.za`
- Password: `Admin@2025`

### 5. Create Required Directories
```bash
mkdir -p app/static/materials
mkdir -p app/static/tasks
mkdir -p app/static/request_hub
mkdir -p app/static/submission_receipts
mkdir -p uploads/timesheets
mkdir -p instance
```

### 6. Set Up Web App in PythonAnywhere Dashboard

**6.1 Go to the "Web" tab**

**6.2 Click "Add a new web app"**
- Choose "Manual configuration"
- Select Python 3.10

**6.3 Configure WSGI file**

Click on the WSGI configuration file link and replace its contents with:

```python
import sys
import os

# Add your project directory to the sys.path
project_home = '/home/YOUR_USERNAME/jubaskillsdevv'
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# Set environment variables
os.environ['FLASK_APP'] = 'app'
os.environ['FLASK_ENV'] = 'production'

# Load environment variables from .env file
from dotenv import load_dotenv
env_path = os.path.join(project_home, '.env')
load_dotenv(env_path)

# Import Flask app
from app import create_app
application = create_app()
```

**Replace `YOUR_USERNAME` with your actual PythonAnywhere username!**

**6.4 Configure Virtual Environment**

In the "Virtualenv" section, enter:
```
/home/YOUR_USERNAME/.virtualenvs/jubalmss
```

**6.5 Configure Static Files**

Add these static file mappings:

| URL | Directory |
|-----|-----------|
| `/static/` | `/home/YOUR_USERNAME/jubaskillsdevv/app/static/` |
| `/uploads/` | `/home/YOUR_USERNAME/jubaskillsdevv/uploads/` |

**6.6 Reload the Web App**

Click the green "Reload" button at the top of the page.

---

## 🔧 Testing the Deployment

1. **Visit your site:**
   - `https://YOUR_USERNAME.pythonanywhere.com`

2. **Login as admin:**
   - Email: `admin@juba.ac.za`
   - Password: `Admin@2025`
   - **⚠️ Change password immediately after first login!**

3. **Create test users:**
   - Go to Admin Dashboard → Users
   - Create staff and intern accounts

4. **Test key features:**
   - ✅ Request Hub (create request, submit as intern)
   - ✅ Certificate issuance and approval
   - ✅ PDF receipt generation
   - ✅ Bulk ZIP download
   - ✅ Notifications

---

## 🐛 Troubleshooting

### Error: "ModuleNotFoundError"
```bash
workon jubalmss
pip install -r requirements.txt
```

### Error: "No such file or directory: '.env'"
```bash
cd ~/jubaskillsdevv
cp .env.example .env
nano .env
```

### Error: Database errors
```bash
workon jubalmss
cd ~/jubaskillsdevv
export FLASK_APP=app
flask db upgrade
```

### Static files not loading
- Check static file mappings in Web tab
- Ensure paths use absolute paths with your username
- Click "Reload" button

### Application doesn't start
1. Check error log in Web tab
2. Verify WSGI file has correct username
3. Verify virtual environment path
4. Check .env file exists and has correct values

---

## 📊 View Logs

**Error Log:**
```bash
tail -f /var/log/YOUR_USERNAME.pythonanywhere.com.error.log
```

**Server Log:**
```bash
tail -f /var/log/YOUR_USERNAME.pythonanywhere.com.server.log
```

---

## 🔄 Updating the Application

When you push updates to GitHub:

```bash
cd ~/jubaskillsdevv
git pull origin main
workon jubalmss
pip install -r requirements.txt  # If dependencies changed
export FLASK_APP=app
flask db upgrade  # If database schema changed
```

Then click "Reload" in the Web tab.

---

## 🔐 Security Checklist

After deployment:
- [ ] Changed default admin password
- [ ] Set strong SECRET_KEY and JWT_SECRET_KEY in .env
- [ ] Verified FLASK_DEBUG=0 in .env
- [ ] Tested file upload limits
- [ ] Reviewed user permissions
- [ ] Backed up database regularly

---

## 📞 Quick Reference

**Your Application URL:**
`https://YOUR_USERNAME.pythonanywhere.com`

**Default Admin:**
- Email: `admin@juba.ac.za`
- Password: `Admin@2025` (CHANGE THIS!)

**Database Location:**
`/home/YOUR_USERNAME/jubaskillsdevv/instance/juba_lms.db`

**Log Files:**
- Error: `/var/log/YOUR_USERNAME.pythonanywhere.com.error.log`
- Server: `/var/log/YOUR_USERNAME.pythonanywhere.com.server.log`

---

## 🎯 Next Steps

1. Complete steps 1-6 above
2. Test the application
3. Change default admin password
4. Create staff and intern accounts
5. Upload training materials
6. Test all features

**Good luck with your deployment! 🚀**

---

*Last Updated: December 4, 2025*
