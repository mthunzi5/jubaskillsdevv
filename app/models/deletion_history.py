from datetime import datetime
from app import db

class DeletionHistory(db.Model):
    """Track all deletion activities with reasons"""
    __tablename__ = 'deletion_history'
    
    id = db.Column(db.Integer, primary_key=True)
    deleted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    deleted_user_id = db.Column(db.Integer, nullable=True)  # If user was deleted
    deleted_item_type = db.Column(db.String(50), nullable=False)  # user, timesheet, etc
    deleted_item_id = db.Column(db.Integer, nullable=False)
    deletion_reason = db.Column(db.Text, nullable=False)
    deletion_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_permanent = db.Column(db.Boolean, default=False)  # True if permanently deleted
    
    # Store deleted item details as JSON string
    deleted_item_details = db.Column(db.Text, nullable=True)
    
    # Relationship
    deleter = db.relationship('User', foreign_keys=[deleted_by], backref='deletions_made')
    
    def to_dict(self):
        """Convert deletion history to dictionary"""
        return {
            'id': self.id,
            'deleted_by': self.deleted_by,
            'deleter_name': f"{self.deleter.name} {self.deleter.surname}" if self.deleter else "Unknown",
            'deleter_role': self.deleter.role if self.deleter else None,
            'deleted_item_type': self.deleted_item_type,
            'deleted_item_id': self.deleted_item_id,
            'deletion_reason': self.deletion_reason,
            'deletion_date': self.deletion_date.isoformat() if self.deletion_date else None,
            'is_permanent': self.is_permanent,
            'deleted_item_details': self.deleted_item_details
        }
    
    def __repr__(self):
        return f'<DeletionHistory {self.id} - {self.deleted_item_type}>'
