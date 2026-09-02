"""Read-only audit log endpoints (Day 4-5)."""
import math
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.audit import AuditLog
from app.core.deps import require_roles

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/")
def list_audit_logs(
    action: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.EVALUATOR)),
):
    """Global, filterable, paginated audit log for the Audit Logs page."""
    q = db.query(AuditLog)

    if action:
        q = q.filter(AuditLog.action == action)
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    if date_from:
        q = q.filter(AuditLog.created_at >= date_from)
    if date_to:
        q = q.filter(AuditLog.created_at <= date_to)

    total = q.count()
    q = q.order_by(AuditLog.created_at.desc())
    rows = q.offset((page - 1) * page_size).limit(page_size).all()

    user_ids = {log.user_id for log in rows if log.user_id}
    names = {}
    if user_ids:
        for u in db.query(User).filter(User.id.in_(user_ids)).all():
            names[u.id] = u.full_name

    items = [
        {
            "id": str(log.id),
            "user_id": str(log.user_id) if log.user_id else None,
            "user_name": names.get(log.user_id),
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "details": log.details,
            "created_at": log.created_at,
        }
        for log in rows
    ]

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": max(1, math.ceil(total / page_size)),
    }


@router.get("/entity/{entity_type}/{entity_id}")
def get_audit_logs_for_entity(
    entity_type: str,
    entity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.EVALUATOR)),
):
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
        .order_by(AuditLog.created_at.desc())
        .all()
    )
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "details": log.details,
            "created_at": log.created_at,
        }
        for log in logs
    ]
