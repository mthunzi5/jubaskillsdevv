from app import db
from datetime import datetime

class Request(db.Model):
    """Staff requests for documents/information from interns"""
    __tablename__ = 'requests'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    request_type = db.Column(db.String(50), nullable=False)  # timesheet, id_document, proof_of_registration, etc.
    
    # Target audience
    target_type = db.Column(db.String(20), nullable=False)  # specific, all, varsity, tvet
    target_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Only if target_type = 'specific'
    
    # Document settings
    requires_documents = db.Column(db.Boolean, default=True)
    max_documents = db.Column(db.Integer, default=5)  # Up to 25
    requires_text = db.Column(db.Boolean, default=False)
    text_field_label = db.Column(db.String(200), nullable=True)  # e.g., "Additional Comments"
    
    # Metadata
    deadline = db.Column(db.DateTime, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='created_requests')
    target_user = db.relationship('User', foreign_keys=[target_user_id], backref='specific_requests')
    submissions = db.relationship('RequestSubmission', backref='request', lazy='dynamic', cascade='all, delete-orphan')
    
    def get_target_users(self):
        """Get list of users who should respond to this request"""
        from app.models.user import User
        
        if self.target_type == 'specific':
            return [self.target_user] if self.target_user else []
        elif self.target_type == 'all':
            return User.query.filter_by(role='intern', is_deleted=False).all()
        elif self.target_type == 'varsity':
            return User.query.filter_by(role='intern', intern_type='varsity', is_deleted=False).all()
        elif self.target_type == 'tvet':
            return User.query.filter_by(role='intern', intern_type='tvet', is_deleted=False).all()
        return []
    
    def has_submitted(self, user_id):
        """Check if a user has already submitted for this request"""
        return self.submissions.filter_by(user_id=user_id).first() is not None
    
    def get_submission(self, user_id):
        """Get submission for a specific user"""
        return self.submissions.filter_by(user_id=user_id).first()
    
    def get_submission_count(self):
        """Get total number of submissions"""
        return self.submissions.count()
    
    def get_expected_count(self):
        """Get expected number of submissions"""
        return len(self.get_target_users())


class RequestSubmission(db.Model):
    """Intern submissions for requests"""
    __tablename__ = 'request_submissions'
    
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('requests.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Optional text field
    text_content = db.Column(db.Text, nullable=True)
    
    # Status
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    review_notes = db.Column(db.Text, nullable=True)
    
    # Metadata
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='request_submissions')
    reviewed_by = db.relationship('User', foreign_keys=[reviewed_by_id], backref='reviewed_submissions')
    documents = db.relationship('RequestDocument', backref='submission', lazy='dynamic', cascade='all, delete-orphan')
    
    def get_document_count(self):
        """Get number of documents uploaded"""
        return self.documents.count()


class RequestDocument(db.Model):
    """Documents uploaded for request submissions"""
    __tablename__ = 'request_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('request_submissions.id'), nullable=False)
    
    # File information
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)  # in bytes
    mime_type = db.Column(db.String(100), nullable=True)
    
    # User-provided name for the document
    document_name = db.Column(db.String(200), nullable=True)  # e.g., "Week 1 Timesheet", "ID Copy"
    
    # Metadata
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_file_size_formatted(self):
        """Get formatted file size"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def get_file_icon(self):
        """Get Bootstrap icon based on file type"""
        if self.mime_type:
            if 'image' in self.mime_type:
                return 'bi-file-image'
            elif 'pdf' in self.mime_type:
                return 'bi-file-pdf'
            elif 'word' in self.mime_type or 'document' in self.mime_type:
                return 'bi-file-word'
            elif 'excel' in self.mime_type or 'spreadsheet' in self.mime_type:
                return 'bi-file-excel'
            elif 'zip' in self.mime_type or 'compressed' in self.mime_type:
                return 'bi-file-zip'
        return 'bi-file-earmark'
