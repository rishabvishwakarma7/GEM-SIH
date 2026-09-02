"""
Compliance rule engine (Day 4) - THE core decision engine for PS 26100.

Design principle (explicitly required by the problem statement): AI is used
upstream only, for understanding/extraction (Day 2 tender-requirement
extraction, Day 3 bidder-document classification & field extraction, and the
mock-registry lookups in verification_service). The actual COMPLIANT /
NON_COMPLIANT / NEEDS_REVIEW decision for every requirement is made here by
deterministic Python rules - confidence scores and mock verification results
are *inputs* to those rules, never a substitute for them.

evaluate_bidder(tender_id, bidder_id) combines, per TenderRequirement:
    Tender Requirement + Bidder Extracted Data + Verification Data
    => one requirement-level result (status/reason/evidence/...)
then aggregates all requirement-level results into a single ComplianceResult
with a compliance_score, a risk_level, and a final overall_status - where a
single FAILED mandatory requirement forces overall_status = NON_COMPLIANT
regardless of how high the score is.
"""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.bidder import Bidder
from app.models.compliance import ComplianceResult, ComplianceStatus, RiskLevel
from app.models.tender import Tender, TenderRequirement, VerificationType
from app.models.verification import VerificationResult, VerificationStatus
from app.services.requirement_matching import find_matching_document
from app.services.verification_providers import get_provider
from app.services.verification_service import verification_service
from app.services.audit_service import log_action
from app.services.ai_service import ai_service
from app.services.notification_service import notification_service
from app.core.logging_config import logger

# Requirement categories the engine evaluates as a numeric-threshold rule
# (minimum_value on the requirement compared against an extracted document field).
THRESHOLD_FIELD_BY_CATEGORY: Dict[str, str] = {
    "turnover": "turnover_amount",
    "financial": "turnover_amount",
    "make_in_india": "local_content_percentage",
}

# Below this AI extraction confidence, even a numerically-passing threshold
# value is downgraded to NEEDS_REVIEW rather than trusted outright - this is
# the "don't let AI alone decide" safeguard for threshold rules specifically.
MIN_TRUSTED_CONFIDENCE = 0.5

REGISTRY_CATEGORIES = {
    "gst", "pan", "identity", "udyam_msme", "company_registration", "bis",
    "epfo", "esic", "startup_dpiit", "nsic", "digilocker", "income_tax",
    "blacklist_debarment",
}


def _category_value(requirement: TenderRequirement) -> str:
    return requirement.category.value if hasattr(requirement.category, "value") else str(requirement.category)


def _verification_type_value(requirement: TenderRequirement) -> str:
    return requirement.verification_type.value if hasattr(requirement.verification_type, "value") else str(requirement.verification_type)


def _base_result(requirement: TenderRequirement, category: str) -> Dict[str, Any]:
    return {
        "requirement_id": str(requirement.id),
        "requirement": requirement.title,
        "category": category,
        "mandatory": bool(requirement.mandatory),
        "required_value": None,
        "actual_value": None,
        "status": "NEEDS_REVIEW",
        "reason": "No deterministic rule is configured for this requirement category yet.",
        "evidence": requirement.evidence,
        "source_document": None,
        "verification_provider": None,
        "clause_reference": requirement.clause_reference,
    }


def _evaluate_registry_requirement(
    requirement: TenderRequirement, category: str, bidder: Bidder, db: Session
) -> Dict[str, Any]:
    """GST / PAN / Udyam / company_registration / BIS / blacklist_debarment."""
    result = _base_result(requirement, category)

    verification: Optional[VerificationResult] = (
        db.query(VerificationResult)
        .filter(VerificationResult.bidder_id == bidder.id, VerificationResult.requirement_id == requirement.id)
        .first()
    )

    doc, extracted, _fields = find_matching_document(bidder, requirement)
    result["source_document"] = doc.original_filename if doc else None

    if not verification:
        result["status"] = "NEEDS_REVIEW"
        result["reason"] = "Verification has not been run yet for this requirement. Run verification first."
        result["required_value"] = "Registry check pending"
        return result

    result["verification_provider"] = verification.provider_name
    result["actual_value"] = verification.identifier_checked
    try:
        raw = json.loads(verification.raw_response) if verification.raw_response else {}
    except (json.JSONDecodeError, TypeError):
        raw = {}
    status_from_registry = raw.get("status")
    if status_from_registry:
        result["actual_value"] = f"{verification.identifier_checked} (status: {status_from_registry})"

    if category == "blacklist_debarment":
        result["required_value"] = "Not present in the configured blacklist dataset"
        if verification.status == VerificationStatus.MISMATCH:
            result["status"] = "NON_COMPLIANT"
            result["reason"] = verification.notes or "Bidder identifier found in the configured blacklist dataset."
        elif verification.status == VerificationStatus.VERIFIED:
            result["status"] = "COMPLIANT"
            result["reason"] = verification.notes or "Bidder not found in the configured blacklist dataset."
        else:
            result["status"] = "NEEDS_REVIEW"
            result["reason"] = verification.notes or "Could not confidently check the blacklist dataset."
        return result

    required_label = {
        "gst": "GST status = Active",
        "pan": "Valid PAN matching bidder identity",
        "identity": "Valid PAN matching bidder identity",
        "udyam_msme": "Active Udyam/MSME registration",
        "company_registration": "Active company registration (MCA)",
        "bis": "Valid BIS certificate/license",
        "epfo": "Active EPFO establishment registration",
        "esic": "Active ESIC registration",
        "startup_dpiit": "Recognized DPIIT Startup India certificate",
        "nsic": "Valid NSIC single-point registration",
        "digilocker": "Verified DigiLocker document",
        "income_tax": "Processed Income Tax e-filing acknowledgement",
    }.get(category, "Verified against registry")
    result["required_value"] = required_label

    if verification.status == VerificationStatus.VERIFIED:
        result["status"] = "COMPLIANT"
        result["reason"] = verification.notes or "Verified successfully against the (mock) government registry."
    elif verification.status == VerificationStatus.MISMATCH:
        result["status"] = "NON_COMPLIANT" if requirement.mandatory else "NEEDS_REVIEW"
        result["reason"] = verification.notes or "Registry record does not satisfy the requirement."
    else:  # NOT_FOUND / PENDING
        result["status"] = "NEEDS_REVIEW"
        result["reason"] = verification.notes or "Required evidence could not be confidently verified."

    result["evidence"] = verification.evidence_snippet or result["evidence"]
    return result


def _evaluate_threshold_requirement(requirement: TenderRequirement, category: str, bidder: Bidder) -> Dict[str, Any]:
    """turnover / financial / make_in_india - numeric minimum_value comparison."""
    result = _base_result(requirement, category)
    field_name = THRESHOLD_FIELD_BY_CATEGORY[category]

    doc, extracted, fields = find_matching_document(bidder, requirement)
    result["source_document"] = doc.original_filename if doc else None

    unit = "%" if category == "make_in_india" else (requirement.currency or "INR")
    result["required_value"] = (
        f"Minimum {requirement.minimum_value:,.0f} {unit}" if requirement.minimum_value is not None else "Not specified"
    )

    if requirement.minimum_value is None:
        result["status"] = "NEEDS_REVIEW"
        result["reason"] = "Tender did not specify a numeric minimum for this requirement."
        return result

    raw_value = fields.get(field_name) if fields else None
    if raw_value is None:
        result["status"] = "NEEDS_REVIEW"
        result["reason"] = (
            "Required evidence could not be confidently verified: no matching bidder document "
            f"provided a value for '{field_name}'."
        )
        return result

    try:
        actual_value = float(raw_value)
    except (TypeError, ValueError):
        result["status"] = "NEEDS_REVIEW"
        result["reason"] = f"Extracted value '{raw_value}' for '{field_name}' is not a usable number."
        return result

    result["actual_value"] = actual_value
    result["evidence"] = extracted.evidence if extracted else requirement.evidence

    meets_threshold = actual_value >= requirement.minimum_value
    low_confidence = bool(extracted) and (extracted.confidence is None or extracted.confidence < MIN_TRUSTED_CONFIDENCE)

    if low_confidence:
        result["status"] = "NEEDS_REVIEW"
        result["reason"] = (
            f"Extracted value ({actual_value:,.0f} {unit}) has low AI extraction confidence "
            f"({(extracted.confidence or 0):.2f}) and needs manual confirmation before it can decide compliance."
        )
    elif meets_threshold:
        result["status"] = "COMPLIANT"
        result["reason"] = f"Verified value ({actual_value:,.0f} {unit}) satisfies the minimum requirement."
    else:
        result["status"] = "NON_COMPLIANT" if requirement.mandatory else "NEEDS_REVIEW"
        result["reason"] = f"Verified value ({actual_value:,.0f} {unit}) is below the mandatory threshold."

    return result


def _evaluate_document_existence_requirement(requirement: TenderRequirement, category: str, bidder: Bidder) -> Dict[str, Any]:
    """
    income_tax / startup_dpiit / nsic / epfo / esic / digilocker / other /
    declaration-type requirements with no dedicated mock registry: pass if a
    completed, readable, non-review-flagged matching document exists.
    """
    result = _base_result(requirement, category)
    result["required_value"] = "Matching document must be present and readable"

    doc, extracted, _fields = find_matching_document(bidder, requirement)
    result["source_document"] = doc.original_filename if doc else None

    if not doc or not extracted:
        result["actual_value"] = "No matching document uploaded"
        result["status"] = "NON_COMPLIANT" if requirement.mandatory else "NEEDS_REVIEW"
        result["reason"] = "No matching bidder document was found for this requirement."
        return result

    result["actual_value"] = f"Document '{doc.original_filename}' uploaded and processed"
    result["evidence"] = extracted.evidence or requirement.evidence

    if extracted.needs_review or extracted.type_mismatch or (extracted.confidence or 0) < MIN_TRUSTED_CONFIDENCE:
        result["status"] = "NEEDS_REVIEW"
        result["reason"] = "Required evidence could not be confidently verified from the uploaded document."
    else:
        result["status"] = "COMPLIANT"
        result["reason"] = "Matching document found and confidently extracted."

    return result


def _evaluate_requirement(requirement: TenderRequirement, bidder: Bidder, db: Session) -> Dict[str, Any]:
    category = _category_value(requirement)
    if category in REGISTRY_CATEGORIES:
        return _evaluate_registry_requirement(requirement, category, bidder, db)
    if category in THRESHOLD_FIELD_BY_CATEGORY:
        return _evaluate_threshold_requirement(requirement, category, bidder)
    return _evaluate_document_existence_requirement(requirement, category, bidder)


def _risk_level_for(status: str) -> RiskLevel:
    return {
        "NON_COMPLIANT": RiskLevel.HIGH,
        "NEEDS_REVIEW": RiskLevel.MEDIUM,
        "COMPLIANT": RiskLevel.LOW,
    }[status]


def _assign_reason_code(result: dict) -> str:
    """
    Maps a requirement result dict to a machine-readable reason code.
    Reason codes are deterministic — never AI-generated.
    """
    status = result.get("status", "")
    reason = (result.get("reason") or "").lower()

    if status == "COMPLIANT":
        return "COMPLIANT"

    if status == "NON_COMPLIANT":
        if "threshold" in reason or "below" in reason or "minimum" in reason:
            return "THRESHOLD_NOT_MET"
        if "blacklist" in reason or "found in" in reason:
            return "REGISTRY_VERIFICATION_FAILED"
        if "mismatch" in reason or "does not satisfy" in reason:
            return "REGISTRY_VERIFICATION_FAILED"
        if "not found" in reason:
            return "REGISTRY_NOT_FOUND"
        if "document" in reason and ("missing" in reason or "no matching" in reason):
            return "DOCUMENT_MISSING"
        return "MANDATORY_REQUIREMENT_FAILED"

    if status == "NEEDS_REVIEW":
        if "confidence" in reason:
            return "LOW_AI_CONFIDENCE"
        if "no matching" in reason or "no document" in reason:
            return "DOCUMENT_MISSING"
        if "not run" in reason or "pending" in reason:
            return "MANUAL_REVIEW_REQUIRED"
        if "unreadable" in reason or "readable" in reason:
            return "DOCUMENT_UNREADABLE"
        if "mismatch" in reason or "identity" in reason:
            return "IDENTITY_MISMATCH"
        if "expired" in reason:
            return "DOCUMENT_EXPIRED"
        return "MANUAL_REVIEW_REQUIRED"

    return "MANUAL_REVIEW_REQUIRED"


def _ensure_review_case(
    db: Session,
    bidder,
    tender,
    overall_status: ComplianceStatus,
    mandatory_failed: bool,
    compliance_score: float,
    created_by=None,
) -> None:
    """
    Auto-creates (or updates) a ReviewCase whenever a bidder evaluates as
    NON_COMPLIANT or NEEDS_REVIEW.  Escalation rules:
      - mandatory_failed → SENIOR_EVALUATOR + HIGH priority
      - score < 50      → SENIOR_EVALUATOR + HIGH priority
      - otherwise       → EVALUATOR + MEDIUM priority
    Idempotent: if an open case already exists it is updated, not duplicated.
    """
    from app.models.review import (
        ReviewCase, ReviewStatus, ReviewLevel, ReviewPriority, ReviewActionType,
    )

    existing = (
        db.query(ReviewCase)
        .filter(
            ReviewCase.bidder_id == bidder.id,
            ReviewCase.status.notin_([ReviewStatus.CLOSED]),
        )
        .first()
    )

    if mandatory_failed or compliance_score < 50:
        level = ReviewLevel.SENIOR_EVALUATOR
        priority = ReviewPriority.HIGH
    else:
        level = ReviewLevel.EVALUATOR
        priority = ReviewPriority.MEDIUM

    if overall_status == ComplianceStatus.NON_COMPLIANT and mandatory_failed:
        reason = (
            "Bidder is NON-COMPLIANT: one or more mandatory requirements failed. "
            "Senior evaluator review required."
        )
        triggers = ["mandatory_requirement_failed", "compliance_non_compliant"]
    elif overall_status == ComplianceStatus.NON_COMPLIANT:
        reason = f"Bidder is NON-COMPLIANT (score {compliance_score:.1f}%). Review required."
        triggers = ["compliance_non_compliant"]
    else:
        reason = (
            f"Bidder requires review (score {compliance_score:.1f}%). "
            "Some requirements could not be confidently verified."
        )
        triggers = ["human_review_required"]

    if existing:
        # Escalate if the new evaluation is worse
        if priority == ReviewPriority.HIGH and existing.priority != ReviewPriority.HIGH:
            existing.priority = priority
            existing.review_level = level
            existing.reason = reason
            db.commit()
        return

    case = ReviewCase(
        tender_id=tender.id,
        bidder_id=bidder.id,
        status=ReviewStatus.OPEN,
        priority=priority,
        review_level=level,
        reason=reason,
        trigger_events=json.dumps(triggers),
        created_by=created_by,
    )
    db.add(case)
    db.commit()
    logger.info(
        f"Auto review case created for bidder {bidder.id}: "
        f"level={level.value} priority={priority.value}"
    )


class ComplianceEngine:
    def evaluate_bidder(
        self,
        tender_id: str,
        bidder_id: str,
        db: Optional[Session] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        owns_session = db is None
        if owns_session:
            db = SessionLocal()

        try:
            bidder = db.query(Bidder).filter(Bidder.id == bidder_id, Bidder.tender_id == tender_id).first()
            if not bidder:
                raise ValueError(f"Bidder {bidder_id} not found under tender {tender_id}")
            tender: Tender = bidder.tender

            requirement_results: List[Dict[str, Any]] = [
                _evaluate_requirement(req, bidder, db) for req in tender.requirements
            ]

            total = len(requirement_results)
            compliant = sum(1 for r in requirement_results if r["status"] == "COMPLIANT")
            non_compliant = sum(1 for r in requirement_results if r["status"] == "NON_COMPLIANT")
            needs_review = sum(1 for r in requirement_results if r["status"] == "NEEDS_REVIEW")

            compliance_score = round((compliant / total) * 100, 2) if total else 0.0

            mandatory_results = [r for r in requirement_results if r["mandatory"]]
            mandatory_failed = any(r["status"] == "NON_COMPLIANT" for r in mandatory_results)
            failed_mandatory_titles = [r["requirement"] for r in mandatory_results if r["status"] == "NON_COMPLIANT"]

            # --- Final status: mandatory failure overrides everything else ---
            if mandatory_failed:
                overall_status = ComplianceStatus.NON_COMPLIANT
            elif needs_review > 0:
                overall_status = ComplianceStatus.NEEDS_REVIEW
            else:
                overall_status = ComplianceStatus.COMPLIANT

            status_label = {
                ComplianceStatus.COMPLIANT: "COMPLIANT",
                ComplianceStatus.NON_COMPLIANT: "NON_COMPLIANT",
                ComplianceStatus.NEEDS_REVIEW: "NEEDS_REVIEW",
            }[overall_status]
            risk_level = _risk_level_for(status_label)

            if mandatory_failed:
                explanation = (
                    f"Compliance score {compliance_score}% ({compliant}/{total} requirements compliant), "
                    f"but mandatory requirement(s) FAILED: {', '.join(failed_mandatory_titles)}. "
                    f"Final status is NON_COMPLIANT regardless of the overall score."
                )
            elif overall_status == ComplianceStatus.NEEDS_REVIEW:
                explanation = (
                    f"Compliance score {compliance_score}% ({compliant}/{total} requirements compliant). "
                    f"{needs_review} requirement(s) need manual review before a final verdict can be issued."
                )
            else:
                explanation = (
                    f"All {total} requirements compliant. Compliance score {compliance_score}%. "
                    f"Bidder meets all mandatory and optional requirements."
                )

            existing: Optional[ComplianceResult] = (
                db.query(ComplianceResult).filter(ComplianceResult.bidder_id == bidder.id).first()
            )
            record = existing or ComplianceResult(tender_id=tender.id, bidder_id=bidder.id)
            record.tender_id = tender.id
            record.overall_status = overall_status
            record.risk_level = risk_level
            record.compliance_score = compliance_score
            record.mandatory_failed = mandatory_failed
            record.explanation = explanation
            record.requirement_results = json.dumps(requirement_results)
            record.total_requirements = str(total)
            record.compliant_count = str(compliant)
            record.non_compliant_count = str(non_compliant)
            record.needs_review_count = str(needs_review)
            record.evaluated_by = user_id
            record.evaluated_at = datetime.utcnow()

            # --- Day 6: AI Recommendation Engine -------------------------------
            # One extra LLM call, strictly downstream of the deterministic
            # verdict above. Never allowed to block or change the verdict
            # itself - if the AI call fails (no API key, network, etc.) we log
            # it and keep whatever recommendation (if any) was already stored.
            try:
                failed_reqs = [
                    {"requirement": r["requirement"], "reason": r["reason"]}
                    for r in requirement_results if r["status"] == "NON_COMPLIANT"
                ]
                review_reqs = [
                    {"requirement": r["requirement"], "reason": r["reason"]}
                    for r in requirement_results if r["status"] == "NEEDS_REVIEW"
                ]
                recommendation = ai_service.generate_compliance_recommendation({
                    "company_name": bidder.company_name,
                    "overall_status": status_label,
                    "compliance_score": compliance_score,
                    "risk_level": risk_level.value,
                    "mandatory_failed": mandatory_failed,
                    "failed_requirements": failed_reqs,
                    "needs_review_requirements": review_reqs,
                })
                record.ai_recommendation = recommendation
                record.ai_recommendation_generated_at = datetime.utcnow()
            except Exception as e:
                logger.warning(f"AI recommendation generation skipped for bidder {bidder.id}: {e}")

            if not existing:
                db.add(record)
            db.commit()
            db.refresh(record)

            log_action(
                db,
                action="compliance_evaluated",
                entity_type="bidder",
                entity_id=str(bidder.id),
                user_id=user_id,
                details={
                    "tender_id": str(tender.id),
                    "overall_status": overall_status.value,
                    "compliance_score": compliance_score,
                    "mandatory_failed": mandatory_failed,
                },
            )
            logger.info(
                f"Compliance evaluated for bidder {bidder.id}: status={overall_status.value} "
                f"score={compliance_score}% mandatory_failed={mandatory_failed}"
            )

            # --- Day 6: non-compliance / missing-document alert ----------------
            try:
                if overall_status in (ComplianceStatus.NON_COMPLIANT, ComplianceStatus.NEEDS_REVIEW):
                    notification_service.send_compliance_alert(
                        bidder=bidder,
                        compliance_result=record,
                        requirement_results=requirement_results,
                        db=db,
                        user_id=user_id,
                    )
            except Exception as e:
                logger.warning(f"Compliance alert notification skipped for bidder {bidder.id}: {e}")

            # --- Upgrade: enrich requirement_results with reason_codes --------
            # Add machine-readable reason_code to every requirement result so
            # the evidence chain API and frontend can display structured explanations
            # without re-parsing the free-text reason string.
            try:
                for r in requirement_results:
                    r["reason_code"] = _assign_reason_code(r)
                record.requirement_results = json.dumps(requirement_results)
                db.commit()
            except Exception as e:
                logger.warning(f"Reason code enrichment failed for bidder {bidder.id}: {e}")

            # --- Upgrade: smart compliance alerts ----------------------------
            try:
                from app.services.alert_service import emit_compliance_alerts
                emit_compliance_alerts(
                    db=db,
                    bidder_id=str(bidder.id),
                    tender_id=str(tender.id),
                    overall_status=overall_status.value,
                    mandatory_failed=mandatory_failed,
                    compliance_score=compliance_score,
                    risk_level=risk_level.value,
                    requirement_results=requirement_results,
                    triggered_by=user_id,
                )
            except Exception as e:
                logger.warning(f"Smart alert emission failed for bidder {bidder.id}: {e}")

            # --- Upgrade: auto-create review case for non-compliant/high-risk bidders ---
            try:
                if overall_status in (ComplianceStatus.NON_COMPLIANT, ComplianceStatus.NEEDS_REVIEW):
                    _ensure_review_case(
                        db=db,
                        bidder=bidder,
                        tender=tender,
                        overall_status=overall_status,
                        mandatory_failed=mandatory_failed,
                        compliance_score=compliance_score,
                        created_by=user_id,
                    )
            except Exception as e:
                logger.warning(f"Auto review case creation failed for bidder {bidder.id}: {e}")

            return {
                "compliance_result": record,
                "requirement_results": requirement_results,
            }
        finally:
            if owns_session:
                db.close()

    def get_bidder_comparison(self, tender_id: str, db: Session) -> List[Dict[str, Any]]:
        """Ranked comparison of every bidder on this tender that has been evaluated at least once.
        Upgrade: includes risk score, suspicious doc count, duplicate count, review status.
        """
        from app.models.risk import DocumentRiskAnalysis, DuplicateDocumentMatch
        from app.models.review import ReviewCase
        from app.models.bidder import BidderDocument

        tender = db.query(Tender).filter(Tender.id == tender_id).first()
        if not tender:
            raise ValueError(f"Tender {tender_id} not found")

        rows = []
        for bidder in tender.bidders:
            result: Optional[ComplianceResult] = (
                db.query(ComplianceResult).filter(ComplianceResult.bidder_id == bidder.id).first()
            )
            if not result:
                continue

            # Upgrade: suspicious doc count
            suspicious_count = sum(
                1 for doc in bidder.documents
                if doc.risk_analysis and doc.risk_analysis.suspicious
            )

            # Upgrade: duplicate matches count
            dup_count = (
                db.query(DuplicateDocumentMatch)
                .filter(
                    (DuplicateDocumentMatch.source_bidder_id == bidder.id)
                    | (DuplicateDocumentMatch.target_bidder_id == bidder.id)
                )
                .count()
            )

            # Upgrade: review case status
            review_case = (
                db.query(ReviewCase)
                .filter(ReviewCase.bidder_id == bidder.id)
                .order_by(ReviewCase.created_at.desc())
                .first()
            )

            # Document completeness: completed docs / total docs
            total_docs = len(bidder.documents)
            completed_docs = sum(
                1 for d in bidder.documents
                if d.processing_status.value == "completed"
            )
            doc_completeness = round((completed_docs / total_docs * 100) if total_docs else 0, 1)

            rows.append({
                "bidder_id": str(bidder.id),
                "company_name": bidder.company_name,
                "gem_seller_id": bidder.gem_seller_id,
                "compliance_score": result.compliance_score,
                "overall_status": result.overall_status.value,
                "risk_level": result.risk_level.value,
                "mandatory_failed": result.mandatory_failed,
                "compliant_count": int(result.compliant_count),
                "non_compliant_count": int(result.non_compliant_count),
                "needs_review_count": int(result.needs_review_count),
                "total_requirements": int(result.total_requirements),
                "evaluated_at": result.evaluated_at,
                # Upgrade columns
                "risk_score": bidder.risk_score,
                "bidder_risk_level": bidder.risk_level,
                "suspicious_document_count": suspicious_count,
                "duplicate_document_count": dup_count,
                "document_completeness": doc_completeness,
                "identity_consistency": bidder.consistency_status.value if bidder.consistency_status else "not_analyzed",
                "review_status": review_case.status.value if review_case else "not_required",
                "review_level": review_case.review_level.value if review_case else None,
                "ai_recommendation": result.ai_recommendation,
            })

        rows.sort(key=lambda r: r["compliance_score"], reverse=True)
        return rows

    def evaluate_all_bidders(
        self, tender_id: str, db: Session, user_id: Optional[str] = None, run_verification: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Bulk/batch operation (Day 6): runs verification (optional) + the
        compliance rule engine for every bidder registered under a tender,
        instead of the evaluator doing it one bidder at a time. Returns one
        summary dict per bidder; a single bidder failing does not stop the
        rest of the batch.
        """
        tender = db.query(Tender).filter(Tender.id == tender_id).first()
        if not tender:
            raise ValueError(f"Tender {tender_id} not found")

        summaries: List[Dict[str, Any]] = []
        for bidder in tender.bidders:
            entry: Dict[str, Any] = {"bidder_id": str(bidder.id), "company_name": bidder.company_name}
            try:
                if run_verification:
                    verification_service.verify_bidder_against_tender(
                        bidder_id=str(bidder.id), db=db, user_id=user_id
                    )
                outcome = self.evaluate_bidder(
                    tender_id=tender_id, bidder_id=str(bidder.id), db=db, user_id=user_id
                )
                record = outcome["compliance_result"]
                entry.update({
                    "success": True,
                    "overall_status": record.overall_status.value,
                    "compliance_score": record.compliance_score,
                    "risk_level": record.risk_level.value,
                })
            except Exception as e:
                logger.error(f"Batch evaluation failed for bidder {bidder.id}: {e}")
                entry.update({"success": False, "error": str(e)})
            summaries.append(entry)

        log_action(
            db,
            action="compliance_batch_evaluated",
            entity_type="tender",
            entity_id=str(tender_id),
            user_id=user_id,
            details={"bidders_processed": len(summaries)},
        )
        return summaries


compliance_engine = ComplianceEngine()
