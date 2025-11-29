from app import db
from datetime import datetime

class TrainingMaterial(db.Model):
    __tablename__ = 'training_materials'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))  # e.g., 'Technical Skills', 'Soft Skills', 'Safety'
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50))  # pdf, docx, pptx, etc.
    file_size = db.Column(db.Integer)  # in bytes
    
    # Metadata
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    uploader = db.relationship('User', backref='uploaded_materials', foreign_keys=[uploaded_by])
    
    def __repr__(self):
        return f'<TrainingMaterial {self.title}>'
    
    def get_file_size_mb(self):
        """Return file size in MB"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0
