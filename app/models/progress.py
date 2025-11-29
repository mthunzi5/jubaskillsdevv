from app import db
from datetime import datetime

class Progress(db.Model):
    __tablename__ = 'progress'
    
    id = db.Column(db.Integer, primary_key=True)
    intern_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Progress metrics
    total_tasks = db.Column(db.Integer, default=0)
    completed_tasks = db.Column(db.Integer, default=0)
    average_grade = db.Column(db.Float, default=0.0)
    
    # Training materials progress
    materials_viewed = db.Column(db.Integer, default=0)
    
    # Completion tracking
    total_hours_logged = db.Column(db.Float, default=0.0)  # from timesheets
    completion_percentage = db.Column(db.Float, default=0.0)
    
    # Certificate eligibility
    is_eligible_for_certificate = db.Column(db.Boolean, default=False)
    certificate_issued = db.Column(db.Boolean, default=False)
    
    # Metadata
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    intern = db.relationship('User', backref='progress_record', foreign_keys=[intern_id])
    
    def __repr__(self):
        return f'<Progress for User {self.intern_id}>'
    
    def update_progress(self):
        """Recalculate progress metrics"""
        from app.models.task_assignment import TaskAssignment
        
        # Get all task assignments for this intern (V2 system)
        assignments = TaskAssignment.query.filter_by(intern_id=self.intern_id).all()
        
        # Filter out assignments for inactive tasks
        active_assignments = [a for a in assignments if a.task.is_active]
        
        self.total_tasks = len(active_assignments)
        self.completed_tasks = len([a for a in active_assignments if a.status == 'completed'])
        
        # Calculate average grade
        graded_assignments = [a for a in active_assignments if a.grade is not None]
        if graded_assignments:
            self.average_grade = sum(a.grade for a in graded_assignments) / len(graded_assignments)
        else:
            self.average_grade = 0.0
        
        # Calculate completion percentage
        if self.total_tasks > 0:
            self.completion_percentage = (self.completed_tasks / self.total_tasks) * 100
        else:
            self.completion_percentage = 0.0
        
        # Check certificate eligibility (e.g., >80% completion and >70% average grade)
        if self.completion_percentage >= 80 and self.average_grade >= 70:
            self.is_eligible_for_certificate = True
        else:
            self.is_eligible_for_certificate = False
        
        self.last_updated = datetime.utcnow()
