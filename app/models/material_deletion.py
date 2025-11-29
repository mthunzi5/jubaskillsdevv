from app import db
from datetime import datetime

class MaterialDeletionRequest(db.Model):
    """Model for material deletion requests requiring approval"""
    __tablename__ = 'material_deletion_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('training_materials.id'), nullable=False)
    requested_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewed_at = db.Column(db.DateTime)
    review_comment = db.Column(db.Text)
    
    # Relationships
    material = db.relationship('TrainingMaterial', backref='deletion_requests')
    requested_by = db.relationship('User', foreign_keys=[requested_by_id], backref='material_deletion_requests')
    reviewed_by = db.relationship('User', foreign_keys=[reviewed_by_id], backref='reviewed_material_deletions')


class MaterialDeletionHistory(db.Model):
    """Model to track deleted materials for audit trail"""
    __tablename__ = 'material_deletion_history'
    
    id = db.Column(db.Integer, primary_key=True)
    material_title = db.Column(db.String(200), nullable=False)
    material_description = db.Column(db.Text)
    material_category = db.Column(db.String(50))
    file_path = db.Column(db.String(255))
    file_type = db.Column(db.String(50))
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    uploaded_at = db.Column(db.DateTime)
    deleted_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    deleted_at = db.Column(db.DateTime, default=datetime.utcnow)
    deletion_reason = db.Column(db.Text)
    
    # Relationships
    uploaded_by = db.relationship('User', foreign_keys=[uploaded_by_id])
    deleted_by = db.relationship('User', foreign_keys=[deleted_by_id])
