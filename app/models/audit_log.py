from datetime import datetime

from app import db


class OperationAuditLog(db.Model):
    """Audit log for operational actions across modules."""
    __tablename__ = 'operation_audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(80), nullable=False)
    entity_type = db.Column(db.String(80), nullable=False)
    entity_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    actor = db.relationship('User', backref='operation_audit_logs', foreign_keys=[actor_user_id])

    def __repr__(self):
        return f'<OperationAuditLog {self.action} {self.entity_type}:{self.entity_id}>'
