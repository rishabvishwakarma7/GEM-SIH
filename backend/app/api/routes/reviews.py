"""
Multi-level human review workflow API routes (Upgrade — Task 10).

GET  /api/reviews               — list all review cases (paginated + filtered)
GET  /api/reviews/{id}          — get single case with actions
POST /api/reviews               — create a review case manually
POST /api/reviews/{id}/assign   — assign to a reviewer
POST /api/reviews/{id}/action   — add a review action (note, approve evidence, etc.)
POST /api/reviews/{id}/escalate — escalate to higher review level
"""
import json
import math
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.bidder import Bidder
from app.models.review import (
    ReviewCase, ReviewAction, ReviewStatus, ReviewLevel,
    ReviewPriority, ReviewActionType,
)
from app.schemas.review import (
    ReviewCaseOut, AssignCaseRequest, ReviewActionRequest, EscalateRequest,
)
from app.core.deps import get_current_user, require_roles
from app.services.audit_service import log_action
from app.core.logging_config import logger

router = APIRouter(prefix="/api/reviews", tags=["reviews"])

# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

def _serialize_action(a: ReviewAction) -> dict:
    try:
        details = json.loads(a.details) if a.details else {}
    except (json.JSONDecodeError, TypeError):
        details = {}
    return {
        "id": str(a.id),
        "case_id": str(a.case_id),
        "action_type": a.action_type.value if hasattr(a.action_type, "value") else str(a.action_type),
        "actor_id": str(a.actor_id),
        "actor_role": a.actor_role,
        "notes": a.notes,
        "details": details,
        "created_at": a.created_at,
    }


def _serialize_case(case: ReviewCase) -> dict:
    try:
        triggers = json.loads(case.trigger_events) if case.trigger_events else []
    except (json.JSONDecodeError, TypeError):
        triggers = []
    return {
        "id": str(case.id),
        "tender_id": str(case.tender_id),
        "bidder_id": str(case.bidder_id),
        "status": case.status.value if hasattr(case.status, "value") else str(case.status),
        "priority": case.priority.value if hasattr(case.priority, "value") else str(case.priority),
        "review_level": case.review_level.value if hasattr(case.review_level, "value") else str(case.review_level),
        "reason": case.reason,
        "trigger_events": triggers,
        "assigned_to": str(case.assigned_to) if case.assigned_to else None,
        "assigned_at": case.assigned_at,
        "created_at": case.created_at,
        "reviewed_at": case.reviewed_at,
        "resolved_at": case.resolved_at,
        "actions": [_serialize_action(a) for a in (case.actions or [])],
    }


# ---------------------------------------------------------------------------
# Escalation rules (configurable)
# ---------------------------------------------------------------------------

ESCALATION_MAP = {
    ReviewLevel.EVALUATOR: ReviewLevel.SENIOR_EVALUATOR,
    ReviewLevel.SENIOR_EVALUATOR: ReviewLevel.PROCUREMENT_OFFICER,
    ReviewLevel.PROCUREMENT_OFFICER: ReviewLevel.PROCUREMENT_OFFICER,  # ceiling
}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/")
def list_review_cases(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    review_level: Optional[str] = Query(None),
    tender_id: Optional[str] = Query(None),
    bidder_id: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(ReviewCase)
    if status:
        q = q.filter(ReviewCase.status == status)
    if priority:
        q = q.filter(ReviewCase.priority == priority)
    if review_level:
        q = q.filter(ReviewCase.review_level == review_level)
    if tender_id:
        q = q.filter(ReviewCase.tender_id == tender_id)
    if bidder_id:
        q = q.filter(ReviewCase.bidder_id == bidder_id)
    if assigned_to:
        q = q.filter(ReviewCase.assigned_to == assigned_to)

    total = q.count()
    rows = (
        q.order_by(ReviewCase.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [_serialize_case(c) for c in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, math.ceil(total / page_size)),
    }


@router.get("/{case_id}", response_model=ReviewCaseOut)
def get_review_case(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = db.query(ReviewCase).filter(ReviewCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Review case not found")
    return _serialize_case(case)


@router.post("/")
def create_review_case(
    bidder_id: str,
    reason: str,
    priority: str = "medium",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.EVALUATOR)),
):
    """Manually creates a review case for a bidder."""
    bidder = db.query(Bidder).filter(Bidder.id == bidder_id).first()
    if not bidder:
        raise HTTPException(status_code=404, detail="Bidder not found")

    # Upsert: only one active case per bidder
    existing = (
        db.query(ReviewCase)
        .filter(ReviewCase.bidder_id == bidder_id, ReviewCase.status != ReviewStatus.CLOSED)
        .first()
    )
    if existing:
        return _serialize_case(existing)

    try:
        priority_enum = ReviewPriority(priority)
    except ValueError:
        priority_enum = ReviewPriority.MEDIUM

    case = ReviewCase(
        tender_id=bidder.tender_id,
        bidder_id=bidder_id,
        status=ReviewStatus.OPEN,
        priority=priority_enum,
        review_level=ReviewLevel.EVALUATOR,
        reason=reason,
        created_by=current_user.id,
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    log_action(
        db, action="review_case_created", entity_type="bidder",
        entity_id=str(bidder_id), user_id=str(current_user.id),
        details={"case_id": str(case.id), "reason": reason},
    )
    return _serialize_case(case)


@router.post("/{case_id}/assign")
def assign_case(
    case_id: str,
    payload: AssignCaseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.EVALUATOR)),
):
    case = db.query(ReviewCase).filter(ReviewCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Review case not found")

    # Verify the target user exists
    target_user = db.query(User).filter(User.id == payload.assigned_to).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Assignee user not found")

    case.assigned_to = payload.assigned_to
    case.assigned_at = datetime.utcnow()
    case.status = ReviewStatus.ASSIGNED

    action = ReviewAction(
        case_id=case.id,
        action_type=ReviewActionType.ASSIGNED,
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        notes=f"Assigned to {target_user.full_name}",
        details=json.dumps({"assigned_to": str(payload.assigned_to)}),
    )
    db.add(action)
    db.commit()

    log_action(
        db, action="review_case_assigned", entity_type="bidder",
        entity_id=str(case.bidder_id), user_id=str(current_user.id),
        details={"case_id": str(case_id), "assigned_to": str(payload.assigned_to)},
    )
    return _serialize_case(case)


@router.post("/{case_id}/action")
def add_review_action(
    case_id: str,
    payload: ReviewActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.EVALUATOR)),
):
    """Adds a review action (note, evidence approval, clarification request, etc.)."""
    case = db.query(ReviewCase).filter(ReviewCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Review case not found")

    try:
        action_type = ReviewActionType(payload.action_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action_type '{payload.action_type}'. "
                   f"Valid values: {[e.value for e in ReviewActionType]}",
        )

    # Update case status to IN_REVIEW on first substantive action
    if case.status in (ReviewStatus.OPEN, ReviewStatus.ASSIGNED):
        case.status = ReviewStatus.IN_REVIEW
        case.reviewed_at = datetime.utcnow()

    action = ReviewAction(
        case_id=case.id,
        action_type=action_type,
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        notes=payload.notes,
        details=json.dumps(payload.details or {}),
    )
    db.add(action)

    # Status transitions based on action
    if action_type == ReviewActionType.RESOLVED:
        case.status = ReviewStatus.CLOSED
        case.resolved_at = datetime.utcnow()
    elif action_type == ReviewActionType.CLARIFICATION_REQUESTED:
        case.status = ReviewStatus.CLARIFICATION_REQUIRED

    db.commit()

    log_action(
        db, action=f"review_{action_type.value}", entity_type="bidder",
        entity_id=str(case.bidder_id), user_id=str(current_user.id),
        details={"case_id": case_id, "notes": (payload.notes or "")[:200]},
    )
    return _serialize_case(case)


@router.post("/{case_id}/escalate")
def escalate_case(
    case_id: str,
    payload: EscalateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.EVALUATOR)),
):
    """Escalates a review case to a higher review level."""
    case = db.query(ReviewCase).filter(ReviewCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Review case not found")

    try:
        target_level = ReviewLevel(payload.target_level)
    except ValueError:
        # Auto-escalate one step if not specified correctly
        target_level = ESCALATION_MAP.get(case.review_level, ReviewLevel.PROCUREMENT_OFFICER)

    case.review_level = target_level
    case.status = ReviewStatus.ESCALATED
    case.assigned_to = None  # clear — must be re-assigned at new level

    action = ReviewAction(
        case_id=case.id,
        action_type=ReviewActionType.ESCALATED,
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        notes=payload.reason,
        details=json.dumps({"escalated_to": target_level.value}),
    )
    db.add(action)
    db.commit()

    # Emit escalation alert
    from app.services.alert_service import emit_alert_once
    from app.models.alert import AlertEventType
    emit_alert_once(
        db=db,
        event_type=AlertEventType.REVIEW_ESCALATED,
        title=f"Review Escalated to {target_level.value.replace('_', ' ').title()}",
        description=payload.reason,
        tender_id=str(case.tender_id),
        bidder_id=str(case.bidder_id),
        triggered_by=str(current_user.id),
    )

    log_action(
        db, action="review_case_escalated", entity_type="bidder",
        entity_id=str(case.bidder_id), user_id=str(current_user.id),
        details={"case_id": case_id, "level": target_level.value, "reason": payload.reason},
    )
    return _serialize_case(case)
