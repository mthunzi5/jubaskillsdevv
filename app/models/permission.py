from datetime import datetime

from app import db


class RolePermission(db.Model):
    """Simple role-based permission matrix with optional DB overrides."""
    __tablename__ = 'role_permissions'

    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20), nullable=False)
    permission = db.Column(db.String(100), nullable=False)
    allowed = db.Column(db.Boolean, default=True, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('role', 'permission', name='uq_role_permission'),
    )

    def __repr__(self):
        return f'<RolePermission {self.role}:{self.permission}={self.allowed}>'
