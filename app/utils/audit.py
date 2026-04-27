import json

from app import db
from app.models.audit_log import OperationAuditLog


def log_audit_event(actor_user_id, action, entity_type, entity_id=None, details=None):
    """Persist audit events without interrupting main request flow."""
    payload = None
    if details is not None:
        try:
            payload = json.dumps(details, default=str)
        except Exception:
            payload = str(details)

    entry = OperationAuditLog(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=payload,
    )
    db.session.add(entry)
