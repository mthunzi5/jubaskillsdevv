# Juba Skills Development Academy - Learning Management System

## Overview
This is a comprehensive Learning Management System built for Juba Skills Development Academy and Training. The system facilitates communication and workflow management between Admins (Managers), Staff, and Interns.

## Features

### Roles
- **Admin (Manager)**: Full system control with user management and deletion approval capabilities
- **Staff**: View and download intern timesheets, manage intern information
- **Interns**: Submit timesheets and manage personal profiles

### Key Functionality

#### Admin Features
- Create and manage all user roles (Admin, Staff, Interns)
- Full CRUD operations on user accounts
- View complete user list with filtering options
- Deletion management with mandatory reason tracking
- Comprehensive deletion history (who deleted what and when)
- Approve or reject soft-delete requests from other roles
- Dashboard with system statistics

#### Staff Features
- View all submitted timesheets organized by month
- Filter timesheets by intern type (Varsity/TVET)
- Download individual timesheets (PDF)
- Bulk download all timesheets for a specific month (ZIP)
- View detailed intern information
- Track submission history per intern

#### Intern Features
- Submit timesheets in PDF format (max 16MB)
- View personal submission history
- Soft-delete own timesheets (requires admin approval)
- Complete profile on first login
- Update personal information
- Change password

### Security Features
- Role-based access control
- Secure password hashing
- Session management with Flask-Login
- JWT token support
- First-time login profile completion requirement
- Default intern password: `JubaFuture2025`

### Deletion System
- **Admin deletions**: Immediate with reason tracking
- **Non-admin deletions**: Soft delete (hidden from user view)
- Admins can view all soft-deleted items
- Admins approve permanent deletion
- Complete deletion history maintained

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Setup Steps

1. **Clone or extract the project**
```powershell
cd C:\Users\Mthunzi\jubalmss
```

2. **Create a virtual environment**
```powershell
python -m venv venv
```

3. **Activate the virtual environment**
```powershell
.\venv\Scripts\Activate.ps1
```

4. **Install dependencies**
```powershell
pip install -r requirements.txt
```

5. **Set up environment variables** (Optional)
```powershell
Copy-Item .env.example .env
# Edit .env with your preferred settings
```

6. **Run the application**
```powershell
python run.py
```

The application will be available at `http://localhost:5000`

## Default Admin Account
- **Email**: admin@juba.ac.za
- **Password**: Admin@2025

**IMPORTANT**: Change this password immediately after first login!

## User Management

### Creating Interns
Admins add interns with:
- 13-digit ID number (used for login)
- Intern type: Varsity or TVET
- Default password: `JubaFuture2025`

Interns complete their profile on first login with:
- Name and surname
- Email address
- Phone number
- Optional password change

### Creating Staff/Admin
Admins add staff/admin users with:
- Email address (used for login)
- Name
- Custom password

## File Upload
- **Format**: PDF only
- **Max size**: 16MB
- **Storage**: Local filesystem (`uploads/timesheets/`)
- Automatic filename generation with timestamps

## Database
- **Type**: SQLite
- **File**: `juba_lms.db`
- **Location**: Project root directory
- Automatically created on first run

## Project Structure
```
jubalmss/
├── app/
│   ├── __init__.py
│   ├── models/
│   │   ├── user.py
│   │   ├── timesheet.py
│   │   ├── deletion_history.py
│   │   └── soft_delete.py
│   ├── routes/
│   │   ├── auth.py
│   │   ├── admin.py
│   │   ├── staff.py
│   │   ├── intern.py
│   │   └── main.py
│   ├── templates/
│   │   ├── base.html
│   │   ├── auth/
│   │   ├── admin/
│   │   ├── staff/
│   │   └── intern/
│   └── utils/
│       ├── helpers.py
│       └── decorators.py
├── uploads/
│   └── timesheets/
├── config.py
├── requirements.txt
├── run.py
└── README.md
```

## Technology Stack
- **Backend**: Flask (Python web framework)
- **Database**: SQLite with SQLAlchemy ORM
- **Authentication**: Flask-Login + Flask-JWT-Extended
- **Frontend**: Bootstrap 5 + Bootstrap Icons
- **File Handling**: Werkzeug for secure uploads

## Development

### Running in Development Mode
```powershell
python run.py
```

### Database Migrations
If you need to make database schema changes:
```powershell
flask db init
flask db migrate -m "Description of changes"
flask db upgrade
```

## Troubleshooting

### Port Already in Use
If port 5000 is already in use, edit `run.py` and change the port:
```python
app.run(debug=True, host='0.0.0.0', port=5001)
```

### Upload Folder Permissions
Ensure the application has write permissions to the `uploads` directory.

### Database Issues
Delete `juba_lms.db` to reset the database (WARNING: This will delete all data).

## Security Notes
- Change default admin password immediately
- Use strong passwords for all accounts
- Keep `.env` file secure and never commit it to version control
- In production, set `DEBUG = False` in config
- Use HTTPS in production environments

## Support
For issues or questions, contact the system administrator.

## License
Proprietary - Juba Skills Development Academy and Training

---
**Version**: 1.0.0  
**Last Updated**: November 2025
