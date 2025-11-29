from datetime import datetime
from app import db

class Timesheet(db.Model):
    """Timesheet model for intern submissions"""
    __tablename__ = 'timesheets'
    
    id = db.Column(db.Integer, primary_key=True)
    intern_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)  # in bytes
    
    # Month organization
    submission_month = db.Column(db.String(7), nullable=False)  # Format: YYYY-MM
    submission_year = db.Column(db.Integer, nullable=False)
    submission_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Soft delete
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    deleted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Permanent delete approval
    pending_permanent_delete = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships - intern relationship is defined in User model with backref
    deleter = db.relationship('User', foreign_keys=[deleted_by])
    
    def to_dict(self):
        """Convert timesheet to dictionary"""
        return {
            'id': self.id,
            'intern_id': self.intern_id,
            'intern_name': f"{self.intern.name} {self.intern.surname}" if self.intern else "Unknown",
            'intern_type': self.intern.intern_type if self.intern else None,
            'filename': self.original_filename,
            'file_size': self.file_size,
            'submission_month': self.submission_month,
            'submission_date': self.submission_date.isoformat() if self.submission_date else None,
            'is_deleted': self.is_deleted,
            'pending_permanent_delete': self.pending_permanent_delete
        }
    
    def __repr__(self):
        return f'<Timesheet {self.id} - {self.original_filename}>'
