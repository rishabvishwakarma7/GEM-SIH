"""
Notification endpoints (Day 6).
List alert history for a bidder, and manually (re)send a compliance alert.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.bidder import Bidder
from app.models.compliance import ComplianceResult
from app.models.notification import Notification
from app.schemas.notification import NotificationOut
from app.core.deps import get_current_user, require_roles
from app.services.notification_service import notification_service
import json

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("/bidder/{bidder_id}", response_model=List[NotificationOut])
def list_bidder_notifications(
    bidder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Notification)
        .filter(Notification.bidder_id == bidder_id)
        .order_by(Notification.created_at.desc())
        .all()
    )


@router.post("/bidder/{bidder_id}/send", response_model=NotificationOut)
def send_bidder_alert(
    bidder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.EVALUATOR)),
):
    """
    Manually (re)send a non-compliance / missing-document alert for a bidder
    that has already been evaluated at least once. Useful for a bidder whose
    compliance status hasn't changed but who still needs to be notified/
    reminded, or to retry a previously SKIPPED/FAILED send after fixing SMTP
    configuration.
    """
    bidder = db.query(Bidder).filter(Bidder.id == bidder_id).first()
    if not bidder:
        raise HTTPException(status_code=404, detail="Bidder not found")

    compliance_result = db.query(ComplianceResult).filter(ComplianceResult.bidder_id == bidder_id).first()
    if not compliance_result:
        raise HTTPException(status_code=404, detail="Bidder has not been evaluated yet - run compliance evaluation first")

    try:
        requirement_results = json.loads(compliance_result.requirement_results) if compliance_result.requirement_results else []
    except (json.JSONDecodeError, TypeError):
        requirement_results = []

    return notification_service.send_compliance_alert(
        bidder=bidder,
        compliance_result=compliance_result,
        requirement_results=requirement_results,
        db=db,
        user_id=str(current_user.id),
    )
