from app import db
from datetime import datetime

class TaskDeletionRequest(db.Model):
    """Track task deletion requests that need admin approval"""
    __tablename__ = 'task_deletion_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    
    # Who requested the deletion
    requested_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Approval status
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    review_comment = db.Column(db.Text, nullable=True)
    
    # Relationships
    task = db.relationship('Task', backref='deletion_requests', foreign_keys=[task_id])
    requester = db.relationship('User', foreign_keys=[requested_by], backref='task_deletion_requests')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by], backref='reviewed_task_deletions')
    
    def __repr__(self):
        return f'<TaskDeletionRequest {self.id} for Task {self.task_id}>'


class TaskDeletionHistory(db.Model):
    """History of all deleted tasks"""
    __tablename__ = 'task_deletion_history'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, nullable=False)
    
    # Task details (stored for history)
    task_title = db.Column(db.String(200), nullable=False)
    task_description = db.Column(db.Text)
    task_category = db.Column(db.String(100))
    assigned_to_name = db.Column(db.String(200))
    assigned_by_name = db.Column(db.String(200))
    task_status = db.Column(db.String(50))
    task_grade = db.Column(db.Float)
    
    # Deletion details
    deletion_reason = db.Column(db.Text, nullable=False)
    deleted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    deleted_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # If it went through approval process
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    deleter = db.relationship('User', foreign_keys=[deleted_by], backref='deleted_tasks_history')
    approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_task_deletions')
    
    def __repr__(self):
        return f'<TaskDeletionHistory {self.id} - {self.task_title}>'
