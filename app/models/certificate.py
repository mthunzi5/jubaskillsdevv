from app import db
from datetime import datetime

class Certificate(db.Model):
    __tablename__ = 'certificates'
    
    id = db.Column(db.Integer, primary_key=True)
    certificate_number = db.Column(db.String(50), unique=True, nullable=False)
    
    # Recipient
    intern_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    intern_name = db.Column(db.String(200), nullable=False)
    
    # Certificate details
    program_name = db.Column(db.String(200), default='Skills Development Program')
    completion_date = db.Column(db.DateTime, default=datetime.utcnow)
    issue_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Performance metrics
    total_hours = db.Column(db.Float)
    final_grade = db.Column(db.Float)
    tasks_completed = db.Column(db.Integer)
    
    # Issuer
    issued_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Admin Approval and Signing
    is_approved = db.Column(db.Boolean, default=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    admin_signature = db.Column(db.String(200), nullable=True)  # Admin's name for signature
    admin_notes = db.Column(db.Text, nullable=True)  # Optional notes from admin
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    intern = db.relationship('User', foreign_keys=[intern_id], backref='certificates')
    issuer = db.relationship('User', foreign_keys=[issued_by], backref='issued_certificates')
    approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_certificates')
    
    def __repr__(self):
        return f'<Certificate {self.certificate_number}>'
    
    @staticmethod
    def generate_certificate_number():
        """Generate unique certificate number"""
        from datetime import datetime
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        count = Certificate.query.count() + 1
        return f'JUBA-CERT-{timestamp}-{count:04d}'
