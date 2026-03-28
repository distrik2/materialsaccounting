from __future__ import annotations

from flask_login import current_user

from ..extensions import db
from ..models import AuditLog


def log_action(action: str, entity_type: str, entity_id: int | None = None, details: str | None = None):
    user_id = None
    try:
        if current_user.is_authenticated:
            user_id = getattr(current_user, "id", None)
    except Exception:
        user_id = None

    log = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )
    db.session.add(log)
