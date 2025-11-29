from datetime import datetime
from app import db

class SoftDelete(db.Model):
    """Track items pending permanent deletion approval"""
    __tablename__ = 'soft_deletes'
    
    id = db.Column(db.Integer, primary_key=True)
    item_type = db.Column(db.String(50), nullable=False)  # user, timesheet, etc
    item_id = db.Column(db.Integer, nullable=False)
    deleted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    deletion_reason = db.Column(db.Text, nullable=False)
    deleted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    approved = db.Column(db.Boolean, default=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    deleter = db.relationship('User', foreign_keys=[deleted_by], backref='soft_deletes_made')
    approver = db.relationship('User', foreign_keys=[approved_by], backref='soft_deletes_approved')
    
    def to_dict(self):
        """Convert soft delete to dictionary"""
        return {
            'id': self.id,
            'item_type': self.item_type,
            'item_id': self.item_id,
            'deleted_by': self.deleted_by,
            'deleter_name': f"{self.deleter.name} {self.deleter.surname}" if self.deleter else "Unknown",
            'deletion_reason': self.deletion_reason,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'approved': self.approved,
            'approved_by': self.approved_by,
            'approver_name': f"{self.approver.name} {self.approver.surname}" if self.approver else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None
        }
    
    def __repr__(self):
        return f'<SoftDelete {self.id} - {self.item_type}>'
