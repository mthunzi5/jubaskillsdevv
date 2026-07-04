from app import db
from datetime import datetime
import os

class JobApplication(db.Model):
    """Job Application model for Juba Consultants opportunities"""
    __tablename__ = 'job_applications'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Applicant information
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    
    # Additional details
    national_id = db.Column(db.String(20), nullable=True)
    qualification_level = db.Column(db.String(100), nullable=True)  # e.g., High School, Diploma, Degree
    
    # Application content
    motivation = db.Column(db.Text, nullable=False)
    skills = db.Column(db.String(500), nullable=True)  # comma-separated
    
    # Status tracking
    status = db.Column(db.String(50), default='submitted')  # submitted, under_review, shortlisted, rejected, accepted
    review_notes = db.Column(db.Text, nullable=True)
    
    # Reviewed by staff member
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    
    # Rating
    rating = db.Column(db.Integer, nullable=True)  # 1-5 stars
    
    # Timestamps
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Soft delete
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    documents = db.relationship('JobApplicationDocument', backref='application', lazy='dynamic', cascade='all, delete-orphan')
    reviewer = db.relationship('User', backref='reviewed_applications')
    
    def __repr__(self):
        return f'<JobApplication {self.full_name} - {self.status}>'
    
    def has_all_required_documents(self):
        """Check if application has all required documents"""
        required_types = ['id_copy', 'qualification', 'cv', 'affidavit']
        uploaded_types = [doc.document_type for doc in self.documents.filter_by(is_deleted=False)]
        return all(req_type in uploaded_types for req_type in required_types)
    
    def get_documents_by_type(self, doc_type):
        """Get documents by type"""
        return self.documents.filter_by(document_type=doc_type, is_deleted=False).all()
    
    def get_missing_documents(self):
        """Get list of missing required documents"""
        required_types = {
            'id_copy': 'ID Copy',
            'qualification': 'Recently Certified Qualifications',
            'cv': 'Curriculum Vitae (CV)',
            'affidavit': 'Affidavit (SETA Declaration)'
        }
        uploaded_types = [doc.document_type for doc in self.documents.filter_by(is_deleted=False)]
        missing = {key: value for key, value in required_types.items() if key not in uploaded_types}
        return missing
    
    def mark_as_reviewed(self, reviewer_id, rating=None, status='under_review', notes=None):
        """Mark application as reviewed"""
        self.reviewed_by = reviewer_id
        self.reviewed_at = datetime.utcnow()
        if rating is not None:
            self.rating = rating
        self.status = status
        if notes:
            self.review_notes = notes


class JobApplicationDocument(db.Model):
    """Documents uploaded for job applications"""
    __tablename__ = 'job_application_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('job_applications.id'), nullable=False)
    
    # Document info
    document_type = db.Column(db.String(50), nullable=False)  # id_copy, qualification, cv, affidavit, other
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)  # in bytes
    mime_type = db.Column(db.String(100))
    
    # Verification
    is_verified = db.Column(db.Boolean, default=False)
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)
    verification_notes = db.Column(db.Text, nullable=True)
    
    # Timestamps
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Soft delete
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    verifier = db.relationship('User', backref='verified_documents', foreign_keys=[verified_by])
    
    def __repr__(self):
        return f'<JobApplicationDocument {self.document_type} - {self.original_filename}>'
    
    def get_human_readable_type(self):
        """Get human-readable document type"""
        types = {
            'id_copy': 'ID Copy / National ID',
            'qualification': 'Recently Certified Qualifications',
            'cv': 'Curriculum Vitae (CV)',
            'affidavit': 'Affidavit (SETA Declaration)',
            'other': 'Other Supporting Document'
        }
        return types.get(self.document_type, self.document_type)
    
    def mark_as_verified(self, verifier_id, notes=None):
        """Mark document as verified"""
        self.is_verified = True
        self.verified_by = verifier_id
        self.verified_at = datetime.utcnow()
        if notes:
            self.verification_notes = notes


class JobApplicationSettings(db.Model):
    """System settings for job application portal availability."""
    __tablename__ = 'job_application_settings'

    id = db.Column(db.Integer, primary_key=True)
    applications_open = db.Column(db.Boolean, default=True, nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    updater = db.relationship('User', backref='job_application_settings_updates')
