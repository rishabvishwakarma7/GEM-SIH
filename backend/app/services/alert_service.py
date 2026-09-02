"""
Smart Alert Engine (Upgrade — Task 5).

Event-driven: callers invoke emit_alert() with an event_type and context.
The engine determines severity, composes the alert, persists it in the
`alerts` table, and optionally triggers the existing notification_service
for email delivery.

Rules:
- AI never generates alerts.
- Every alert is persisted even if email is disabled.
- Alerts are never permanently deleted (dismissed flag only).
- One alert per (event_type, bidder_id, document_id) per evaluation cycle
  to avoid spam — use upsert_alert() helper.
"""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.alert import Alert, AlertEventType, AlertSeverity
from app.core.logging_config import logger


# ---------------------------------------------------------------------------
# Severity mapping
# ---------------------------------------------------------------------------
EVENT_SEVERITY: Dict[AlertEventType, AlertSeverity] = {
    AlertEventType.COMPLIANCE_NON_COMPLIANT: AlertSeverity.HIGH,
    AlertEventType.MANDATORY_REQUIREMENT_FAILED: AlertSeverity.CRITICAL,
    AlertEventType.HIGH_RISK_BIDDER: AlertSeverity.HIGH,
    AlertEventType.SUSPICIOUS_DOCUMENT: AlertSeverity.HIGH,
    AlertEventType.DUPLICATE_DOCUMENT: AlertSeverity.MEDIUM,
    AlertEventType.REGISTRY_MISMATCH: AlertSeverity.HIGH,
    AlertEventType.IDENTITY_INCONSISTENCY: AlertSeverity.MEDIUM,
    AlertEventType.DOCUMENT_MISSING: AlertSeverity.MEDIUM,
    AlertEventType.DOCUMENT_EXPIRED: AlertSeverity.MEDIUM,
    AlertEventType.LOW_AI_CONFIDENCE: AlertSeverity.LOW,
    AlertEventType.HUMAN_REVIEW_REQUIRED: AlertSeverity.MEDIUM,
    AlertEventType.REVIEW_ESCALATED: AlertSeverity.HIGH,
    AlertEventType.FINAL_DECISION_SUBMITTED: AlertSeverity.INFO,
}

ACTION_REQUIRED_EVENTS = {
    AlertEventType.MANDATORY_REQUIREMENT_FAILED,
    AlertEventType.SUSPICIOUS_DOCUMENT,
    AlertEventType.REGISTRY_MISMATCH,
    AlertEventType.HUMAN_REVIEW_REQUIRED,
    AlertEventType.REVIEW_ESCALATED,
    AlertEventType.DUPLICATE_DOCUMENT,
    AlertEventType.IDENTITY_INCONSISTENCY,
}


def emit_alert(
    db: Session,
    event_type: AlertEventType,
    title: str,
    description: str,
    tender_id: Optional[str] = None,
    bidder_id: Optional[str] = None,
    requirement_id: Optional[str] = None,
    document_id: Optional[str] = None,
    target_user_id: Optional[str] = None,
    triggered_by: Optional[str] = None,
) -> Alert:
    """
    Creates and persists one Alert.  Does NOT deduplicate — callers should
    use emit_alert_once() if idempotency per evaluation cycle is needed.
    """
    severity = EVENT_SEVERITY.get(event_type, AlertSeverity.MEDIUM)
    action_required = event_type in ACTION_REQUIRED_EVENTS

    alert = Alert(
        event_type=event_type,
        severity=severity,
        title=title,
        description=description,
        tender_id=tender_id,
        bidder_id=bidder_id,
        requirement_id=requirement_id,
        document_id=document_id,
        target_user_id=target_user_id,
        action_required=action_required,
        triggered_by=triggered_by,
        created_at=datetime.utcnow(),
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    logger.info(
        f"Alert emitted: {event_type.value} severity={severity.value} "
        f"bidder={bidder_id} tender={tender_id}"
    )
    return alert


def emit_alert_once(
    db: Session,
    event_type: AlertEventType,
    title: str,
    description: str,
    tender_id: Optional[str] = None,
    bidder_id: Optional[str] = None,
    requirement_id: Optional[str] = None,
    document_id: Optional[str] = None,
    triggered_by: Optional[str] = None,
) -> Alert:
    """
    Idempotent version: only creates the alert if no unread/undismissed alert
    with the same (event_type, bidder_id, document_id) exists within the last
    24 hours.  Prevents duplicate spam alerts on re-runs.
    """
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(hours=24)

    q = db.query(Alert).filter(
        Alert.event_type == event_type,
        Alert.dismissed == False,   # noqa: E712
        Alert.created_at >= cutoff,
    )
    if bidder_id:
        q = q.filter(Alert.bidder_id == bidder_id)
    if document_id:
        q = q.filter(Alert.document_id == document_id)

    existing = q.first()
    if existing:
        logger.debug(f"Alert {event_type.value} already exists for bidder={bidder_id}, skipping")
        return existing

    return emit_alert(
        db=db,
        event_type=event_type,
        title=title,
        description=description,
        tender_id=tender_id,
        bidder_id=bidder_id,
        requirement_id=requirement_id,
        document_id=document_id,
        triggered_by=triggered_by,
    )


# ---------------------------------------------------------------------------
# High-level alert composers — called after compliance / risk evaluation
# ---------------------------------------------------------------------------

def emit_compliance_alerts(
    db: Session,
    bidder_id: str,
    tender_id: str,
    overall_status: str,
    mandatory_failed: bool,
    compliance_score: float,
    risk_level: str,
    requirement_results: List[Dict[str, Any]],
    triggered_by: Optional[str] = None,
) -> List[Alert]:
    """Emits all relevant compliance-triggered alerts for a bidder."""
    alerts_created: List[Alert] = []

    if mandatory_failed:
        failed_names = [
            r["requirement"] for r in requirement_results
            if r.get("status") == "NON_COMPLIANT" and r.get("mandatory")
        ]
        a = emit_alert_once(
            db=db,
            event_type=AlertEventType.MANDATORY_REQUIREMENT_FAILED,
            title="Mandatory Requirement(s) Failed",
            description=(
                f"Bidder has failed {len(failed_names)} mandatory requirement(s): "
                + ", ".join(failed_names[:3])
                + (" and more." if len(failed_names) > 3 else ".")
            ),
            tender_id=tender_id,
            bidder_id=bidder_id,
            triggered_by=triggered_by,
        )
        alerts_created.append(a)

    if overall_status == "non_compliant":
        a = emit_alert_once(
            db=db,
            event_type=AlertEventType.COMPLIANCE_NON_COMPLIANT,
            title="Bidder Marked Non-Compliant",
            description=(
                f"Compliance score: {compliance_score:.1f}%. "
                f"Risk level: {risk_level.upper()}."
            ),
            tender_id=tender_id,
            bidder_id=bidder_id,
            triggered_by=triggered_by,
        )
        alerts_created.append(a)

    if risk_level in ("high", "critical"):
        a = emit_alert_once(
            db=db,
            event_type=AlertEventType.HIGH_RISK_BIDDER,
            title=f"High-Risk Bidder Detected ({risk_level.upper()})",
            description=(
                f"Bidder risk level is {risk_level.upper()} with compliance score "
                f"{compliance_score:.1f}%."
            ),
            tender_id=tender_id,
            bidder_id=bidder_id,
            triggered_by=triggered_by,
        )
        alerts_created.append(a)

    return alerts_created


def emit_document_risk_alerts(
    db: Session,
    bidder_id: str,
    tender_id: str,
    document_id: str,
    risk_score: float,
    risk_level: str,
    signals: List[Dict[str, Any]],
    triggered_by: Optional[str] = None,
) -> List[Alert]:
    """Emits alerts after document risk analysis."""
    alerts_created: List[Alert] = []

    if risk_level in ("high", "critical"):
        signal_names = [s.get("signal", "") for s in signals]
        a = emit_alert_once(
            db=db,
            event_type=AlertEventType.SUSPICIOUS_DOCUMENT,
            title=f"Suspicious Document Detected (Risk: {risk_level.upper()})",
            description=(
                f"Document risk score: {risk_score:.0f}/100. "
                f"Signals: {', '.join(signal_names[:3])}."
            ),
            tender_id=tender_id,
            bidder_id=bidder_id,
            document_id=document_id,
            triggered_by=triggered_by,
        )
        alerts_created.append(a)

    # Check for registry mismatch signal
    if any(s.get("signal") == "REGISTRY_MISMATCH" for s in signals):
        a = emit_alert_once(
            db=db,
            event_type=AlertEventType.REGISTRY_MISMATCH,
            title="Government Registry Mismatch Detected",
            description="Document information does not match government registry records.",
            tender_id=tender_id,
            bidder_id=bidder_id,
            document_id=document_id,
            triggered_by=triggered_by,
        )
        alerts_created.append(a)

    return alerts_created


def emit_duplicate_alerts(
    db: Session,
    tender_id: str,
    bidder_id: str,
    match_type: str,
    similarity: float,
    other_bidder_id: str,
    triggered_by: Optional[str] = None,
) -> Alert:
    return emit_alert_once(
        db=db,
        event_type=AlertEventType.DUPLICATE_DOCUMENT,
        title="Potential Duplicate Document Detected",
        description=(
            f"Document similarity: {similarity:.1f}% ({match_type}). "
            f"Matches another bidder's document in this tender."
        ),
        tender_id=tender_id,
        bidder_id=bidder_id,
        triggered_by=triggered_by,
    )


def emit_review_required_alert(
    db: Session,
    bidder_id: str,
    tender_id: str,
    reason: str,
    triggered_by: Optional[str] = None,
) -> Alert:
    return emit_alert_once(
        db=db,
        event_type=AlertEventType.HUMAN_REVIEW_REQUIRED,
        title="Human Review Required",
        description=reason,
        tender_id=tender_id,
        bidder_id=bidder_id,
        triggered_by=triggered_by,
    )


alert_service = type(
    "_Svc", (),
    {
        "emit": staticmethod(emit_alert),
        "emit_once": staticmethod(emit_alert_once),
        "emit_compliance_alerts": staticmethod(emit_compliance_alerts),
        "emit_document_risk_alerts": staticmethod(emit_document_risk_alerts),
        "emit_duplicate_alerts": staticmethod(emit_duplicate_alerts),
        "emit_review_required": staticmethod(emit_review_required_alert),
    },
)()
