from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login_manager
import secrets

class User(UserMixin, db.Model):
    """User model for all roles: admin, staff, intern"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, staff, intern
    
    # Common fields
    name = db.Column(db.String(100), nullable=True)
    surname = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    
    # Intern specific fields
    id_number = db.Column(db.String(13), unique=True, nullable=True)  # 13 digits for interns
    intern_type = db.Column(db.String(20), nullable=True)  # varsity or tvet
    
    # Profile completion
    is_profile_complete = db.Column(db.Boolean, default=False)
    first_login = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Soft delete
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    
    # Password reset
    reset_token = db.Column(db.String(100), unique=True, nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    requires_password_change = db.Column(db.Boolean, default=False)
    
    # Last login tracking
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    timesheets = db.relationship('Timesheet', backref='intern', lazy='dynamic', foreign_keys='Timesheet.intern_id')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password"""
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        """Check if user is admin"""
        return self.role == 'admin'
    
    def is_staff(self):
        """Check if user is staff"""
        return self.role == 'staff'
    
    def is_intern(self):
        """Check if user is intern"""
        return self.role == 'intern'
    
    def generate_reset_token(self):
        """Generate password reset token"""
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
        return self.reset_token
    
    def verify_reset_token(self, token):
        """Verify reset token is valid and not expired"""
        if self.reset_token != token:
            return False
        if self.reset_token_expiry < datetime.utcnow():
            return False
        return True
    
    def clear_reset_token(self):
        """Clear reset token after use"""
        self.reset_token = None
        self.reset_token_expiry = None
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'role': self.role,
            'name': self.name,
            'surname': self.surname,
            'phone': self.phone,
            'id_number': self.id_number,
            'intern_type': self.intern_type,
            'is_profile_complete': self.is_profile_complete,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_deleted': self.is_deleted
        }
    
    def __repr__(self):
        return f'<User {self.email or self.id_number} - {self.role}>'

@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    return User.query.get(int(user_id))
