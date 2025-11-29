#!/bin/bash
# Setup script for PythonAnywhere deployment
# Run this in PythonAnywhere Bash console after uploading code

echo "=== Juba Skills LMS - PythonAnywhere Setup ==="
echo ""

# Get username
USERNAME=$(whoami)
PROJECT_DIR="/home/$USERNAME/jubalmss"

echo "Project directory: $PROJECT_DIR"
echo ""

# Navigate to project
cd $PROJECT_DIR

# Create virtual environment
echo "Creating virtual environment..."
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
echo "Creating upload directories..."
mkdir -p instance
mkdir -p app/static/submissions
mkdir -p app/static/materials
mkdir -p app/static/board_attachments
mkdir -p app/static/images
mkdir -p uploads/timesheets

# Set permissions
echo "Setting permissions..."
chmod -R 755 app/static
chmod -R 755 uploads
chmod -R 755 instance

# Initialize database
echo "Initializing database..."
python3 << EOF
from app import create_app, db
from app.utils.helpers import create_default_admin

app = create_app('production')
with app.app_context():
    db.create_all()
    create_default_admin()
    print("✓ Database created successfully!")
    print("✓ Default admin account created!")
    print("  Email: admin@juba.ac.za")
    print("  Password: Admin@2025")
EOF

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "Next steps:"
echo "1. Go to Web tab in PythonAnywhere dashboard"
echo "2. Configure WSGI file (copy from pythonanywhere_wsgi.py)"
echo "3. Set virtualenv path: $PROJECT_DIR/venv"
echo "4. Add static files mapping: /static/ -> $PROJECT_DIR/app/static/"
echo "5. Click 'Reload' button"
echo "6. Visit your site: https://$USERNAME.pythonanywhere.com"
echo ""
