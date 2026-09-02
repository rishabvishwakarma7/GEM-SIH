"""
Risk Intelligence Service (Upgrade — Task 6).

Calculates a deterministic, fully transparent bidder-level risk score
by aggregating signals from:
  - Compliance engine results  (+25 max per mandatory failure category)
  - Government verification mismatches
  - Document-level risk analyses
  - Identity consistency status
  - Missing documents
  - Duplicate document matches

AI (Gemini) is called ONLY at the end to produce a 2–4 sentence narrative.
The narrative is advisory — it never modifies risk_score, risk_level, or
any compliance verdict.

Risk level thresholds (same as DocumentRiskAnalysis):
  0–25   LOW
  26–50  MEDIUM
  51–75  HIGH
  76–100 CRITICAL
"""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.bidder import Bidder, BidderConsistencyStatus
from app.models.compliance import ComplianceResult, ComplianceStatus
from app.models.risk import DocumentRiskAnalysis, DuplicateDocumentMatch
from app.models.verification import VerificationResult, VerificationStatus
from app.core.logging_config import logger

# ---------------------------------------------------------------------------
# Score contribution weights (all deterministic, no AI)
# ---------------------------------------------------------------------------
WEIGHTS = {
    "mandatory_failure": 25,          # per failed mandatory requirement (capped at 25)
    "non_compliant_result": 20,       # overall NON_COMPLIANT verdict
    "needs_review_result": 10,        # overall NEEDS_REVIEW verdict
    "registry_mismatch": 15,          # per MISMATCH verification (capped at 20)
    "registry_not_found": 10,         # per NOT_FOUND verification
    "suspicious_document_high": 18,   # document risk level HIGH
    "suspicious_document_critical": 25,
    "identity_inconsistency": 10,
    "missing_documents": 8,           # per missing required doc (capped at 16)
    "duplicate_document": 8,          # per duplicate match (capped at 16)
}

RISK_THRESHOLDS = [
    (76, "critical"),
    (51, "high"),
    (26, "medium"),
    (0, "low"),
]


def _risk_level(score: float) -> str:
    for threshold, level in RISK_THRESHOLDS:
        if score >= threshold:
            return level
    return "low"


def _clamp(v: float) -> float:
    return max(0.0, min(100.0, v))


def _build_risk_breakdown(
    bidder: Bidder,
    compliance: Optional[ComplianceResult],
    verifications: List[VerificationResult],
    doc_risks: List[DocumentRiskAnalysis],
    duplicates: List[DuplicateDocumentMatch],
) -> Dict[str, Any]:
    """
    Returns a structured breakdown dict AND the final numeric score.
    Every point is traceable to a specific signal.
    """
    breakdown: Dict[str, Any] = {
        "compliance_failures": 0,
        "government_mismatches": 0,
        "suspicious_documents": 0,
        "missing_documents": 0,
        "identity_inconsistency": 0,
        "duplicate_documents": 0,
    }
    factors: List[Dict[str, Any]] = []
    total = 0.0

    # 1. Compliance failures
    if compliance:
        req_results = []
        try:
            req_results = json.loads(compliance.requirement_results or "[]")
        except (json.JSONDecodeError, TypeError):
            req_results = []

        mandatory_failures = [
            r for r in req_results
            if r.get("status") == "NON_COMPLIANT" and r.get("mandatory")
        ]
        if mandatory_failures:
            contrib = min(WEIGHTS["mandatory_failure"] * len(mandatory_failures), 25)
            breakdown["compliance_failures"] += contrib
            total += contrib
            factors.append({
                "factor": "Mandatory Requirement Failures",
                "severity": "high",
                "score_contribution": contrib,
                "detail": f"{len(mandatory_failures)} mandatory requirement(s) failed: "
                          + ", ".join(r["requirement"] for r in mandatory_failures[:3]),
            })

        if compliance.overall_status == ComplianceStatus.NON_COMPLIANT:
            contrib = WEIGHTS["non_compliant_result"]
            breakdown["compliance_failures"] += contrib
            total += contrib
            factors.append({
                "factor": "Overall Non-Compliant Verdict",
                "severity": "high",
                "score_contribution": contrib,
                "detail": f"Compliance score: {compliance.compliance_score:.1f}%",
            })
        elif compliance.overall_status == ComplianceStatus.NEEDS_REVIEW:
            contrib = WEIGHTS["needs_review_result"]
            breakdown["compliance_failures"] += contrib
            total += contrib
            factors.append({
                "factor": "Compliance Needs Review",
                "severity": "medium",
                "score_contribution": contrib,
                "detail": f"Compliance score: {compliance.compliance_score:.1f}% — manual review needed",
            })

    # 2. Government verification mismatches
    mismatch_count = sum(
        1 for v in verifications if v.status == VerificationStatus.MISMATCH
    )
    not_found_count = sum(
        1 for v in verifications if v.status == VerificationStatus.NOT_FOUND
    )
    if mismatch_count:
        contrib = min(WEIGHTS["registry_mismatch"] * mismatch_count, 20)
        breakdown["government_mismatches"] += contrib
        total += contrib
        factors.append({
            "factor": "Government Registry Mismatch",
            "severity": "high",
            "score_contribution": contrib,
            "detail": f"{mismatch_count} registry check(s) returned MISMATCH",
        })
    if not_found_count:
        contrib = min(WEIGHTS["registry_not_found"] * not_found_count, 15)
        breakdown["government_mismatches"] += contrib
        total += contrib
        factors.append({
            "factor": "Identifier Not Found in Registry",
            "severity": "medium",
            "score_contribution": contrib,
            "detail": f"{not_found_count} identifier(s) not found in registry",
        })

    # 3. Suspicious documents
    high_risk_docs = [d for d in doc_risks if d.risk_level.value in ("high", "critical")]
    if high_risk_docs:
        for dr in high_risk_docs:
            w_key = "suspicious_document_critical" if dr.risk_level.value == "critical" else "suspicious_document_high"
            contrib = WEIGHTS[w_key]
            breakdown["suspicious_documents"] += contrib
            total += contrib
        factors.append({
            "factor": "Suspicious Document(s) Detected",
            "severity": "high",
            "score_contribution": breakdown["suspicious_documents"],
            "detail": f"{len(high_risk_docs)} document(s) flagged as suspicious",
        })

    # 4. Identity inconsistency
    if bidder.consistency_status in (
        BidderConsistencyStatus.INCONSISTENT,
        BidderConsistencyStatus.NEEDS_REVIEW,
    ):
        contrib = WEIGHTS["identity_inconsistency"]
        breakdown["identity_inconsistency"] = contrib
        total += contrib
        factors.append({
            "factor": "Identity Inconsistency",
            "severity": "medium" if bidder.consistency_status == BidderConsistencyStatus.NEEDS_REVIEW else "high",
            "score_contribution": contrib,
            "detail": f"Cross-document identity consistency status: {bidder.consistency_status.value}",
        })

    # 5. Missing documents
    missing = bidder.missing_document_types or []
    if missing:
        contrib = min(WEIGHTS["missing_documents"] * len(missing), 16)
        breakdown["missing_documents"] = contrib
        total += contrib
        factors.append({
            "factor": "Missing Required Documents",
            "severity": "medium",
            "score_contribution": contrib,
            "detail": f"{len(missing)} required document type(s) not uploaded: {', '.join(missing[:3])}",
        })

    # 6. Duplicate documents
    if duplicates:
        contrib = min(WEIGHTS["duplicate_document"] * len(duplicates), 16)
        breakdown["duplicate_documents"] = contrib
        total += contrib
        factors.append({
            "factor": "Duplicate Document(s) Detected",
            "severity": "medium",
            "score_contribution": contrib,
            "detail": f"{len(duplicates)} potential duplicate match(es) found",
        })

    return {
        "breakdown": breakdown,
        "factors": factors,
        "total_score": _clamp(total),
    }


def analyze_bidder_risk(
    bidder_id: str,
    db: Optional[Session] = None,
    generate_ai_summary: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Computes and persists bidder-level risk score and breakdown.
    Returns a dict with risk_score, risk_level, factors, breakdown, ai_summary.
    """
    owns_session = db is None
    if owns_session:
        db = SessionLocal()

    try:
        bidder: Optional[Bidder] = db.query(Bidder).filter(Bidder.id == bidder_id).first()
        if not bidder:
            logger.warning(f"Risk analysis: bidder {bidder_id} not found")
            return None

        # Gather all relevant data
        compliance: Optional[ComplianceResult] = (
            db.query(ComplianceResult).filter(ComplianceResult.bidder_id == bidder_id).first()
        )
        verifications: List[VerificationResult] = (
            db.query(VerificationResult).filter(VerificationResult.bidder_id == bidder_id).all()
        )
        doc_risks: List[DocumentRiskAnalysis] = [
            doc.risk_analysis
            for doc in bidder.documents
            if doc.risk_analysis is not None
        ]
        duplicates: List[DuplicateDocumentMatch] = (
            db.query(DuplicateDocumentMatch)
            .filter(
                (DuplicateDocumentMatch.source_bidder_id == bidder_id)
                | (DuplicateDocumentMatch.target_bidder_id == bidder_id)
            )
            .all()
        )

        # Deterministic risk calculation
        result = _build_risk_breakdown(
            bidder, compliance, verifications, doc_risks, duplicates
        )
        score = result["total_score"]
        level = _risk_level(score)
        factors = result["factors"]
        breakdown = result["breakdown"]

        # Optional AI narrative — never modifies score/level
        ai_summary = None
        if generate_ai_summary and factors:
            try:
                from app.services.ai_service import ai_service
                ai_summary = _generate_ai_risk_summary(
                    ai_service, bidder.company_name, score, level, factors, compliance
                )
            except Exception as e:
                logger.warning(f"AI risk summary skipped for bidder {bidder_id}: {e}")

        # Persist on Bidder row
        bidder.risk_score = score
        bidder.risk_level = level
        bidder.risk_factors = json.dumps(factors)
        bidder.risk_summary = ai_summary
        bidder.risk_analyzed_at = datetime.utcnow()

        # Persist breakdown on ComplianceResult if available
        if compliance:
            compliance.risk_breakdown = json.dumps(breakdown)

        db.commit()

        logger.info(
            f"Risk analysis for bidder {bidder.id}: score={score:.1f} "
            f"level={level} factors={len(factors)}"
        )

        return {
            "bidder_id": str(bidder_id),
            "company_name": bidder.company_name,
            "risk_score": score,
            "risk_level": level,
            "factors": factors,
            "breakdown": breakdown,
            "ai_summary": ai_summary,
            "analyzed_at": bidder.risk_analyzed_at.isoformat(),
        }

    except Exception as e:
        logger.error(f"Risk analysis failed for bidder {bidder_id}: {e}", exc_info=True)
        if db:
            db.rollback()
        return None
    finally:
        if owns_session and db:
            db.close()


def _generate_ai_risk_summary(
    ai_service,
    company_name: str,
    risk_score: float,
    risk_level: str,
    factors: List[Dict[str, Any]],
    compliance: Optional[ComplianceResult],
) -> Optional[str]:
    """
    One focused LLM call to produce 2–4 sentences of plain-English risk
    explanation.  The prompt makes it explicit that the score is already
    decided and must not be changed.
    """
    from app.config import settings
    if not settings.GEMINI_API_KEY:
        return None

    factor_lines = "\n".join(
        f"- {f['factor']} ({f['severity'].upper()}): {f['detail']}"
        for f in factors[:5]
    )
    compliance_info = ""
    if compliance:
        compliance_info = (
            f"Compliance status: {compliance.overall_status.value}, "
            f"score: {compliance.compliance_score:.1f}%."
        )

    prompt = f"""A deterministic rule engine has ALREADY calculated the following risk assessment
for a GeM tender bidder. Do NOT change or re-derive the risk score or level.

Bidder: {company_name}
Risk Score (already decided, do not change): {risk_score:.0f}/100
Risk Level (already decided, do not change): {risk_level.upper()}
{compliance_info}

Top risk factors (already identified, do not change):
{factor_lines}

Write EXACTLY 2–4 sentences in plain English explaining why this bidder is at {risk_level.upper()} risk
and what the procurement officer should specifically review. Be concrete about the factors above.
Do NOT add any new risk factors not listed. Do NOT repeat raw numbers verbatim if you can phrase
them naturally. No headings, no bullet points, no markdown."""

    try:
        from google import genai
        from app.config import settings
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        model_name = settings.AI_MODEL.strip().strip('"').strip("'")
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config={"max_output_tokens": 350},
        )
        text = (response.text or "").strip()
        return text if text else None
    except Exception as e:
        logger.warning(f"AI risk summary generation failed: {e}")
        return None


def build_risk_timeline(bidder_id: str, db: Session) -> List[Dict[str, Any]]:
    """
    Constructs a chronological event timeline for the Risk Intelligence view
    by reading AuditLog entries for this bidder.
    """
    from app.models.audit import AuditLog
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.entity_type == "bidder", AuditLog.entity_id == str(bidder_id))
        .order_by(AuditLog.created_at.asc())
        .limit(50)
        .all()
    )

    # Also include document-level events
    from app.models.bidder import BidderDocument
    doc_logs = (
        db.query(AuditLog)
        .join(BidderDocument, AuditLog.entity_id == BidderDocument.id.cast(str))
        .filter(BidderDocument.bidder_id == bidder_id, AuditLog.entity_type == "document")
        .order_by(AuditLog.created_at.asc())
        .limit(20)
        .all()
    )

    all_events = []
    for log in logs + doc_logs:
        try:
            details = json.loads(log.details) if log.details else {}
        except (json.JSONDecodeError, TypeError):
            details = {}
        all_events.append({
            "timestamp": log.created_at.isoformat() if log.created_at else None,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "details": details,
        })

    all_events.sort(key=lambda x: x["timestamp"] or "")
    return all_events


risk_intelligence_service = type(
    "_Svc", (),
    {
        "analyze": staticmethod(analyze_bidder_risk),
        "timeline": staticmethod(build_risk_timeline),
    },
)()
