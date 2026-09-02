"""Tiny helper for writing AuditLog rows consistently across services."""
import json
from typing import Any, Dict, Optional

from app.models.audit import AuditLog


def log_action(
    db,
    action: str,
    entity_type: str,
    entity_id: str,
    user_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        details=json.dumps(details) if details is not None else None,
    )
    db.add(entry)
    db.commit()
