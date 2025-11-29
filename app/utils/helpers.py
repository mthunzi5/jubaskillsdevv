import os
import json
from datetime import datetime
from app import db
from app.models.user import User

def create_default_admin():
    """Create default admin account if none exists"""
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        admin = User(
            email='admin@juba.ac.za',
            role='admin',
            name='System',
            surname='Administrator',
            is_profile_complete=True,
            first_login=False
        )
        admin.set_password('Admin@2025')
        db.session.add(admin)
        db.session.commit()
        print("Default admin created: admin@juba.ac.za / Admin@2025")

def allowed_file(filename, allowed_extensions):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def generate_filename(original_filename, prefix=''):
    """Generate unique filename"""
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    ext = original_filename.rsplit('.', 1)[1].lower()
    return f"{prefix}{timestamp}_{original_filename}"

def get_file_size_mb(size_bytes):
    """Convert bytes to MB"""
    return round(size_bytes / (1024 * 1024), 2)

def format_month_year(date_obj):
    """Format date to YYYY-MM"""
    return date_obj.strftime('%Y-%m')

def save_deletion_history(deleted_by, item_type, item_id, reason, item_details=None, is_permanent=False):
    """Save deletion to history"""
    from app.models.deletion_history import DeletionHistory
    
    history = DeletionHistory(
        deleted_by=deleted_by,
        deleted_item_type=item_type,
        deleted_item_id=item_id,
        deletion_reason=reason,
        is_permanent=is_permanent,
        deleted_item_details=json.dumps(item_details) if item_details else None
    )
    db.session.add(history)
    db.session.commit()
    return history

def create_soft_delete_request(item_type, item_id, deleted_by, reason):
    """Create soft delete request for admin approval"""
    from app.models.soft_delete import SoftDelete
    
    soft_delete = SoftDelete(
        item_type=item_type,
        item_id=item_id,
        deleted_by=deleted_by,
        deletion_reason=reason
    )
    db.session.add(soft_delete)
    db.session.commit()
    return soft_delete
