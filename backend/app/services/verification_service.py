"""
Verification service (Day 4).

Orchestrates, for every TenderRequirement whose category maps to a mock
external-registry provider (GST / PAN / Udyam / company registration / BIS /
blacklist), finding the bidder's matching extracted document field and
calling the corresponding VerificationProvider, then persisting one
VerificationResult row per (bidder, requirement).

This module deliberately does NOT decide COMPLIANT/NON_COMPLIANT/NEEDS_REVIEW
- that is the compliance_engine's job. This module only answers "what did the
(mock) external registry say about this identifier", which the rule engine
then combines with the tender requirement and the bidder's own document data.

Threshold-style requirements (turnover, make_in_india local content) and
plain document-existence requirements (income_tax, startup_dpiit, nsic, ...)
have no external registry to check against, so no VerificationResult is
created for them here - the compliance_engine reads their extracted document
fields directly.
"""
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.bidder import Bidder
from app.models.tender import Tender, TenderRequirement
from app.models.verification import VerificationResult, VerificationStatus
from app.services.requirement_matching import find_matching_document, bidder_identity_context
from app.services.verification_providers import get_provider, IDENTIFIER_FIELD_BY_CATEGORY
from app.services.audit_service import log_action
from app.core.logging_config import logger
import json


class VerificationService:
    def verify_bidder_against_tender(
        self,
        bidder_id: str,
        db: Optional[Session] = None,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        owns_session = db is None
        if owns_session:
            db = SessionLocal()

        try:
            bidder = db.query(Bidder).filter(Bidder.id == bidder_id).first()
            if not bidder:
                raise ValueError(f"Bidder {bidder_id} not found")

            tender: Tender = bidder.tender
            identity_context = bidder_identity_context(bidder)

            results: List[Dict[str, Any]] = []

            for requirement in tender.requirements:
                category_value = (
                    requirement.category.value
                    if hasattr(requirement.category, "value")
                    else str(requirement.category)
                )
                provider = get_provider(category_value)
                if not provider:
                    # No external registry for this category (threshold /
                    # plain-document-existence requirement) - nothing to verify here.
                    continue

                doc, extracted, fields = find_matching_document(bidder, requirement)
                field_name = IDENTIFIER_FIELD_BY_CATEGORY.get(category_value)
                identifier = fields.get(field_name) if field_name else None

                # Blacklist check falls back to identity context if the bidder
                # never uploaded a dedicated "blacklist" document.
                if category_value == "blacklist_debarment" and not identifier:
                    identifier = identity_context.get("company_name")

                provider_result = provider.verify(identifier, {**identity_context, **fields})

                # Upsert: replace any prior VerificationResult for this (bidder, requirement).
                existing = (
                    db.query(VerificationResult)
                    .filter(
                        VerificationResult.bidder_id == bidder.id,
                        VerificationResult.requirement_id == requirement.id,
                    )
                    .first()
                )
                if existing:
                    record = existing
                else:
                    record = VerificationResult(bidder_id=bidder.id, requirement_id=requirement.id)
                    db.add(record)

                record.bidder_document_id = doc.id if doc else None
                record.status = provider_result.status
                record.provider_name = provider_result.provider_name
                record.identifier_checked = str(identifier) if identifier else None
                record.raw_response = json.dumps(provider_result.data)
                record.is_mock = provider_result.is_mock
                record.evidence_snippet = extracted.evidence if extracted else None
                record.notes = provider_result.note

                db.commit()
                db.refresh(record)

                results.append({
                    "requirement_id": str(requirement.id),
                    "requirement_title": requirement.title,
                    "category": category_value,
                    "provider": provider_result.provider_name,
                    "identifier_checked": record.identifier_checked,
                    "status": record.status.value,
                    "note": provider_result.note,
                    "source_document": doc.original_filename if doc else None,
                })

            log_action(
                db,
                action="verification_run",
                entity_type="bidder",
                entity_id=str(bidder.id),
                user_id=user_id,
                details={"tender_id": str(tender.id), "checks_run": len(results)},
            )
            logger.info(f"Verification run for bidder {bidder.id}: {len(results)} registry checks executed")
            return results

        finally:
            if owns_session:
                db.close()


verification_service = VerificationService()
