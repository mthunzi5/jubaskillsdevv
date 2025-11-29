from app import db
from datetime import datetime

class Evaluation(db.Model):
    __tablename__ = 'evaluations'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Who and when
    intern_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    evaluator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    evaluation_date = db.Column(db.DateTime, default=datetime.utcnow)
    period = db.Column(db.String(100))  # e.g., 'Week 1', 'Month 1', 'Q1 2025'
    
    # Skills assessment (1-5 rating scale)
    technical_skills = db.Column(db.Integer)  # 1-5
    communication = db.Column(db.Integer)  # 1-5
    teamwork = db.Column(db.Integer)  # 1-5
    problem_solving = db.Column(db.Integer)  # 1-5
    punctuality = db.Column(db.Integer)  # 1-5
    initiative = db.Column(db.Integer)  # 1-5
    professionalism = db.Column(db.Integer)  # 1-5
    
    # Overall rating
    overall_rating = db.Column(db.Float)  # calculated average
    
    # Qualitative feedback
    strengths = db.Column(db.Text)
    areas_for_improvement = db.Column(db.Text)
    additional_comments = db.Column(db.Text)
    recommendations = db.Column(db.Text)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    intern = db.relationship('User', foreign_keys=[intern_id], backref='evaluations')
    evaluator = db.relationship('User', foreign_keys=[evaluator_id], backref='conducted_evaluations')
    
    def __repr__(self):
        return f'<Evaluation for User {self.intern_id}>'
    
    def calculate_overall_rating(self):
        """Calculate average rating from all skill ratings"""
        ratings = [
            self.technical_skills,
            self.communication,
            self.teamwork,
            self.problem_solving,
            self.punctuality,
            self.initiative,
            self.professionalism
        ]
        valid_ratings = [r for r in ratings if r is not None]
        if valid_ratings:
            self.overall_rating = sum(valid_ratings) / len(valid_ratings)
        return self.overall_rating
