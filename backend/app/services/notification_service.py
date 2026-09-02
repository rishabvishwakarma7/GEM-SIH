"""
Notification service (Day 6).

Sends the bidder an alert when their compliance evaluation comes back
NON_COMPLIANT or NEEDS_REVIEW (missing/unverifiable documents), and records
every attempt as a Notification row regardless of whether the underlying
channel actually delivered anything.

Modular by design, mirroring verification_providers.py: NotificationProvider
is the interface; EmailNotificationProvider is a real (SMTP) implementation
that no-ops safely when NOTIFICATIONS_ENABLED/SMTP_HOST are not configured;
SMSNotificationProvider is a stub raising NotImplementedError, since a real
SMS send needs a paid third-party gateway (Twilio / MSG91 / etc.) and
credentials this project does not have - wiring it in later means writing one
class here, same pattern as adding a real VerificationProvider.
"""
import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.core.logging_config import logger
from app.models.bidder import Bidder
from app.models.compliance import ComplianceResult
from app.models.notification import Notification, NotificationChannel, NotificationStatus


@dataclass
class NotificationOutcome:
    status: NotificationStatus
    reason: Optional[str] = None


class NotificationProvider(ABC):
    channel: NotificationChannel

    @abstractmethod
    def send(self, recipient: Optional[str], subject: str, message: str) -> NotificationOutcome:
        raise NotImplementedError


class EmailNotificationProvider(NotificationProvider):
    channel = NotificationChannel.EMAIL

    def send(self, recipient: Optional[str], subject: str, message: str) -> NotificationOutcome:
        if not recipient:
            return NotificationOutcome(NotificationStatus.SKIPPED, "Bidder has no contact_email on file.")
        if not settings.NOTIFICATIONS_ENABLED:
            return NotificationOutcome(
                NotificationStatus.SKIPPED,
                "NOTIFICATIONS_ENABLED=false - set it and configure SMTP_* in backend/.env to send real emails.",
            )
        if not settings.SMTP_HOST:
            return NotificationOutcome(NotificationStatus.SKIPPED, "SMTP_HOST is not configured in backend/.env.")

        msg = MIMEText(message)
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = recipient

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                if settings.SMTP_USE_TLS:
                    server.starttls()
                if settings.SMTP_USERNAME:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM_EMAIL, [recipient], msg.as_string())
            return NotificationOutcome(NotificationStatus.SENT)
        except Exception as e:
            logger.error(f"Email notification failed to {recipient}: {e}")
            return NotificationOutcome(NotificationStatus.FAILED, str(e))


class SMSNotificationProvider(NotificationProvider):
    channel = NotificationChannel.SMS

    def send(self, recipient: Optional[str], subject: str, message: str) -> NotificationOutcome:
        if not settings.SMS_ENABLED:
            return NotificationOutcome(
                NotificationStatus.SKIPPED,
                "SMS is not implemented - requires a paid gateway (Twilio/MSG91/etc). "
                "Wire a real provider here (same pattern as EmailNotificationProvider) when one is available.",
            )
        raise NotImplementedError("SMS gateway integration not implemented")


class NotificationService:
    def __init__(self):
        self.email_provider = EmailNotificationProvider()
        self.sms_provider = SMSNotificationProvider()

    def _compose(self, bidder: Bidder, compliance_result: ComplianceResult, requirement_results: List[Dict[str, Any]]) -> Dict[str, str]:
        status_label = compliance_result.overall_status.value.replace("_", " ").upper()
        failed = [r["requirement"] for r in requirement_results if r["status"] == "NON_COMPLIANT"]
        review = [r["requirement"] for r in requirement_results if r["status"] == "NEEDS_REVIEW"]

        subject = f"GeM Tender Compliance Update - {status_label}"
        lines = [
            f"Dear {bidder.company_name},",
            "",
            f"Your bid compliance status has been evaluated as: {status_label} "
            f"(score: {compliance_result.compliance_score}%).",
        ]
        if failed:
            lines.append("")
            lines.append("The following mandatory requirement(s) were NOT met:")
            lines.extend(f"  - {title}" for title in failed)
        if review:
            lines.append("")
            lines.append("The following item(s) need additional/clearer documents before a final decision:")
            lines.extend(f"  - {title}" for title in review)
        lines.append("")
        lines.append("Please upload corrected/additional documents at your earliest convenience.")
        lines.append("")
        lines.append("This is an automated message from the GeM Bid Compliance Verification Platform.")
        return {"subject": subject, "message": "\n".join(lines)}

    def send_compliance_alert(
        self,
        bidder: Bidder,
        compliance_result: ComplianceResult,
        requirement_results: List[Dict[str, Any]],
        db: Session,
        user_id: Optional[str] = None,
    ) -> Notification:
        content = self._compose(bidder, compliance_result, requirement_results)
        outcome = self.email_provider.send(bidder.contact_email, content["subject"], content["message"])

        record = Notification(
            bidder_id=bidder.id,
            tender_id=bidder.tender_id,
            channel=NotificationChannel.EMAIL,
            status=outcome.status,
            recipient=bidder.contact_email,
            subject=content["subject"],
            message=content["message"],
            reason=outcome.reason,
            triggered_by=user_id,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        logger.info(f"Compliance alert for bidder {bidder.id}: status={outcome.status.value} reason={outcome.reason}")
        return record


notification_service = NotificationService()
