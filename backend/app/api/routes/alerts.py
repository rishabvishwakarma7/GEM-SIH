"""
Smart Alert API routes (Upgrade — Task 10).

GET  /api/alerts            — list all alerts (paginated + filtered)
GET  /api/alerts/unread     — unread count + latest unread alerts
POST /api/alerts/{id}/read  — mark an alert as read
POST /api/alerts/{id}/dismiss — dismiss an alert
"""
import math
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.alert import Alert, AlertSeverity, AlertEventType
from app.core.deps import get_current_user

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


def _serialize_alert(a: Alert) -> dict:
    return {
        "id": str(a.id),
        "event_type": a.event_type.value if hasattr(a.event_type, "value") else str(a.event_type),
        "severity": a.severity.value if hasattr(a.severity, "value") else str(a.severity),
        "title": a.title,
        "description": a.description,
        "tender_id": str(a.tender_id) if a.tender_id else None,
        "bidder_id": str(a.bidder_id) if a.bidder_id else None,
        "requirement_id": str(a.requirement_id) if a.requirement_id else None,
        "document_id": str(a.document_id) if a.document_id else None,
        "action_required": a.action_required,
        "read_at": a.read_at,
        "dismissed": a.dismissed,
        "created_at": a.created_at,
    }


@router.get("/")
def list_alerts(
    severity: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    bidder_id: Optional[str] = Query(None),
    tender_id: Optional[str] = Query(None),
    unread_only: bool = Query(False),
    action_required: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns paginated alerts.  Global alerts (target_user_id=None) are visible
    to everyone; personal alerts are only visible to the target user or admins.
    """
    from app.models.user import UserRole
    q = db.query(Alert).filter(Alert.dismissed == False)  # noqa: E712

    # Scope: admins see all; others see global + their own
    if current_user.role != UserRole.ADMIN:
        q = q.filter(
            or_(
                Alert.target_user_id.is_(None),
                Alert.target_user_id == current_user.id,
            )
        )

    if severity:
        q = q.filter(Alert.severity == severity)
    if event_type:
        q = q.filter(Alert.event_type == event_type)
    if bidder_id:
        q = q.filter(Alert.bidder_id == bidder_id)
    if tender_id:
        q = q.filter(Alert.tender_id == tender_id)
    if unread_only:
        q = q.filter(Alert.read_at.is_(None))
    if action_required is not None:
        q = q.filter(Alert.action_required == action_required)

    total = q.count()
    unread_count = q.filter(Alert.read_at.is_(None)).count()
    rows = q.order_by(Alert.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [_serialize_alert(a) for a in rows],
        "total": total,
        "unread_count": unread_count,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, math.ceil(total / page_size)),
    }


@router.get("/unread")
def get_unread_alerts(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Quick-access endpoint for the notification bell — returns count + latest N unread."""
    from app.models.user import UserRole
    q = db.query(Alert).filter(
        Alert.dismissed == False,  # noqa: E712
        Alert.read_at.is_(None),
    )
    if current_user.role != UserRole.ADMIN:
        q = q.filter(
            or_(
                Alert.target_user_id.is_(None),
                Alert.target_user_id == current_user.id,
            )
        )
    total_unread = q.count()
    latest = q.order_by(Alert.created_at.desc()).limit(limit).all()
    return {
        "unread_count": total_unread,
        "alerts": [_serialize_alert(a) for a in latest],
    }


@router.post("/{alert_id}/read")
def mark_read(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if alert.read_at is None:
        alert.read_at = datetime.utcnow()
        db.commit()
    return {"id": alert_id, "read_at": alert.read_at}


@router.post("/{alert_id}/dismiss")
def dismiss_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Marks an alert as dismissed (hidden from UI).  The row is never deleted
    so it remains in the audit history.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.dismissed = True
    if alert.read_at is None:
        alert.read_at = datetime.utcnow()
    db.commit()
    return {"id": alert_id, "dismissed": True}
