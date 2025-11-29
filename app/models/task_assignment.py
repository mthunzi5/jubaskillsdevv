from app import db
from datetime import datetime

class TaskAssignment(db.Model):
    """Many-to-many relationship between tasks and interns"""
    __tablename__ = 'task_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks_v2.id'), nullable=False)
    intern_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Status tracking per intern
    status = db.Column(db.String(50), default='pending')  # pending, in_progress, submitted, completed, overdue
    
    # Submission per intern
    submission_text = db.Column(db.Text)
    submission_file = db.Column(db.String(500))
    submitted_at = db.Column(db.DateTime)
    
    # Grading per intern
    grade = db.Column(db.Float)  # 0-100
    feedback = db.Column(db.Text)
    graded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    graded_at = db.Column(db.DateTime)
    
    # Timestamps
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    task = db.relationship('TaskV2', back_populates='assignments')
    intern = db.relationship('User', foreign_keys=[intern_id], backref='task_assignments')
    grader = db.relationship('User', foreign_keys=[graded_by])
    
    def __repr__(self):
        return f'<TaskAssignment {self.task_id} -> {self.intern_id}>'


class TaskV2(db.Model):
    """Enhanced task model with type-specific content"""
    __tablename__ = 'tasks_v2'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=False)  # Assignment, Project, Quiz, Research, Practical
    
    # Assignment metadata
    assigned_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assign_type = db.Column(db.String(20))  # all, varsity, tvet, individual
    due_date = db.Column(db.DateTime)
    priority = db.Column(db.String(20), default='medium')
    
    # Type-specific content
    # For Assignment/Research: reference file
    reference_file = db.Column(db.String(500))
    
    # For Quiz: auto-grading enabled
    has_auto_grading = db.Column(db.Boolean, default=False)
    passing_score = db.Column(db.Float, default=70.0)
    
    # Task availability control
    is_open = db.Column(db.Boolean, default=True)  # Controls if interns can submit
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    assigner = db.relationship('User', foreign_keys=[assigned_by], backref='created_tasks_v2')
    assignments = db.relationship('TaskAssignment', back_populates='task', cascade='all, delete-orphan')
    quiz_questions = db.relationship('QuizQuestion', back_populates='task', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<TaskV2 {self.title}>'
    
    def get_intern_assignment(self, intern_id):
        """Get assignment for specific intern"""
        return TaskAssignment.query.filter_by(task_id=self.id, intern_id=intern_id).first()
    
    def is_overdue(self):
        """Check if task is overdue"""
        if self.due_date:
            return datetime.utcnow() > self.due_date
        return False


class QuizQuestion(db.Model):
    """Quiz questions for quiz-type tasks"""
    __tablename__ = 'quiz_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks_v2.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(50), default='multiple_choice')  # multiple_choice, true_false, short_answer
    
    # Multiple choice options (JSON stored as text)
    option_a = db.Column(db.Text)
    option_b = db.Column(db.Text)
    option_c = db.Column(db.Text)
    option_d = db.Column(db.Text)
    
    # Correct answer
    correct_answer = db.Column(db.String(10))  # A, B, C, D, or True/False, or text for short answer
    
    # Scoring
    points = db.Column(db.Float, default=1.0)
    
    # Order
    question_order = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    task = db.relationship('TaskV2', back_populates='quiz_questions')
    answers = db.relationship('QuizAnswer', back_populates='question', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<QuizQuestion {self.id}>'


class QuizAnswer(db.Model):
    """Student answers to quiz questions"""
    __tablename__ = 'quiz_answers'
    
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('task_assignments.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('quiz_questions.id'), nullable=False)
    
    answer = db.Column(db.Text)  # Student's answer
    is_correct = db.Column(db.Boolean)  # Auto-graded result
    points_earned = db.Column(db.Float, default=0.0)
    
    answered_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    assignment = db.relationship('TaskAssignment', backref='quiz_answers')
    question = db.relationship('QuizQuestion', back_populates='answers')
    
    def __repr__(self):
        return f'<QuizAnswer {self.id}>'
