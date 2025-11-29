from app import db
from datetime import datetime

class Task(db.Model):
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100))  # e.g., 'Assignment', 'Project', 'Quiz'
    
    # Assignment details
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # intern
    assigned_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # staff/admin
    due_date = db.Column(db.DateTime)
    
    # Status tracking
    status = db.Column(db.String(50), default='pending')  # pending, in_progress, submitted, completed, overdue
    priority = db.Column(db.String(20), default='medium')  # low, medium, high
    
    # Submission
    submission_text = db.Column(db.Text)
    submission_file = db.Column(db.String(500))
    submitted_at = db.Column(db.DateTime)
    
    # Grading
    grade = db.Column(db.Float)  # 0-100
    feedback = db.Column(db.Text)
    graded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    graded_at = db.Column(db.DateTime)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    intern = db.relationship('User', foreign_keys=[assigned_to], backref='assigned_tasks')
    assigner = db.relationship('User', foreign_keys=[assigned_by], backref='created_tasks')
    grader = db.relationship('User', foreign_keys=[graded_by], backref='graded_tasks')
    
    def __repr__(self):
        return f'<Task {self.title}>'
    
    def is_overdue(self):
        """Check if task is overdue"""
        if self.due_date and self.status not in ['completed', 'submitted']:
            return datetime.utcnow() > self.due_date
        return False
    
    def days_until_due(self):
        """Calculate days until due date"""
        if self.due_date:
            delta = self.due_date - datetime.utcnow()
            return delta.days
        return None
