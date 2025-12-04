# Juba LMS Deployment Guide

## Pre-Deployment Checklist

### ✅ Fixed Issues
- [x] Removed duplicate "Evaluations" link in admin sidebar
- [x] Added "Certificates" link to admin sidebar
- [x] Fixed intern sidebar condition (using `is_intern()` method)
- [x] All dependencies listed in requirements.txt
- [x] Database migrations created and tested

### 🔧 Configuration

#### 1. Environment Variables
Create a `.env` file based on `.env.example`:

```bash
SECRET_KEY=<generate-strong-random-key>
JWT_SECRET_KEY=<generate-strong-random-key>
DATABASE_URI=sqlite:///juba_lms.db  # or PostgreSQL for production
FLASK_ENV=production
```

**Generate secure keys:**
```python
import secrets
print(secrets.token_urlsafe(32))
```

#### 2. Database Setup
```bash
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Set environment
$env:FLASK_APP="app"

# Run migrations
flask db upgrade

# Create default admin (auto-created on first run)
# Default credentials: admin@juba.ac.za / Admin@2025
```

#### 3. Static Files
Ensure these directories exist:
- `app/static/materials/` - Training materials
- `app/static/uploads/` - User uploads
- `app/static/board/` - Communication board attachments
- `uploads/timesheets/` - Timesheet PDFs
- `uploads/receipts/` - Request submission receipts

### 🚀 Production Deployment

#### Option 1: Windows Server with IIS
1. Install Python 3.9+
2. Create virtual environment and install dependencies
3. Configure IIS with FastCGI
4. Set up HTTPS certificate
5. Configure application pool

#### Option 2: Linux Server with Gunicorn + Nginx
```bash
# Install dependencies
pip install -r requirements.txt

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app('production')"
```

**Nginx Configuration:**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /static {
        alias /path/to/jubalmss/app/static;
    }
}
```

### 🔒 Security Checklist
- [ ] Change default admin password immediately after first login
- [ ] Use strong SECRET_KEY and JWT_SECRET_KEY
- [ ] Enable HTTPS in production
- [ ] Set DEBUG=False in production
- [ ] Use PostgreSQL instead of SQLite for production
- [ ] Implement rate limiting
- [ ] Set up firewall rules
- [ ] Regular backups of database
- [ ] Keep dependencies updated

### 📊 Database Migration
If migrating from old database:
```bash
# Backup current database
cp instance/juba_lms.db instance/juba_lms.db.backup

# Run migrations
flask db upgrade
```

### 🧪 Testing Before Deployment
1. Test all user roles (admin, staff, intern)
2. Test certificate approval workflow
3. Test request hub features (bulk download, notifications, analytics)
4. Test recurring requests
5. Verify PDF receipt generation
6. Test communication board
7. Check all navigation links work
8. Test mobile responsiveness

### 📦 Key Features
✅ Request Hub Enhancements:
- Bulk document download (ZIP with folders)
- In-app notification system with bell icon
- Request statistics and analytics dashboard
- Recurring requests (weekly/monthly/quarterly)
- PDF submission receipts

✅ Certificate System:
- Staff can issue certificates to eligible interns
- Admin approval required (with signature)
- Admin can directly award certificates bypassing requirements
- 3-signature certificate layout (Intern, Issuer, Admin)

✅ Role-Based Access:
- Admin: Full system access, approval workflows, user management
- Staff: Issue certificates, create tasks, view progress, evaluations
- Intern: Complete tasks, view progress, receive certificates

### 🐛 Known Issues (Non-Critical)
- CSS linting warnings in Jinja2 templates (false positives, no functional impact)
- Template inline styles trigger linter warnings (working as intended)

### 📝 Post-Deployment
1. Monitor application logs
2. Set up automated backups
3. Configure email notifications (if needed)
4. Train users on new features
5. Collect feedback and iterate

### 🔄 Maintenance
```bash
# Update dependencies
pip install --upgrade -r requirements.txt

# Create new migration after model changes
flask db migrate -m "Description"
flask db upgrade

# Backup database regularly
# SQLite: Copy instance/juba_lms.db
# PostgreSQL: pg_dump command
```

### 📞 Support
- Review error logs in console output
- Check Flask debug mode is OFF in production
- Verify all environment variables are set
- Ensure all directories have proper permissions

---

**Current Version:** 2.0
**Last Updated:** December 4, 2025
**Default Admin:** admin@juba.ac.za / Admin@2025 (Change immediately!)
