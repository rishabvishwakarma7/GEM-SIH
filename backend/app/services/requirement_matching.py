"""
Shared helper: for a given TenderRequirement, find the bidder's best matching
uploaded document + its AI-extracted structured fields.

Used by both verification_service (to find the identifier to check against a
mock registry) and compliance_engine (to read threshold/existence values).
Deterministic, no AI call here - the AI already ran during document
extraction (Day 3); this just picks the best already-extracted candidate.
"""
import json
from typing import Any, Dict, Optional, Tuple

from app.models.bidder import Bidder, BidderDocument, DocumentProcessingStatus
from app.models.document import ExtractedDocumentData
from app.models.tender import TenderRequirement

MatchResult = Tuple[Optional[BidderDocument], Optional[ExtractedDocumentData], Dict[str, Any]]

# A TenderRequirement.category doesn't always share its literal string with the
# BidderDocumentType it should be checked against (e.g. a "turnover" or
# "financial" requirement is satisfied by a "financial_statement" or
# "turnover_certificate" document, and an "identity" requirement by a "pan"
# document). This maps each requirement category to the set of acceptable
# document types, defaulting to "just match the category name itself".
CATEGORY_TO_DOCUMENT_TYPES: Dict[str, set] = {
    "identity": {"pan"},
    "turnover": {"turnover_certificate", "financial_statement"},
    "financial": {"financial_statement", "turnover_certificate"},
    "blacklist_debarment": {"pan", "gst", "company_registration"},  # identity docs used for the identifier
}


def _parse_fields(extracted: ExtractedDocumentData) -> Dict[str, Any]:
    try:
        return json.loads(extracted.structured_fields) if extracted.structured_fields else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def find_matching_document(bidder: Bidder, requirement: TenderRequirement) -> MatchResult:
    """
    Returns (document, extracted_data, structured_fields) for the bidder
    document that best matches this requirement's category, preferring:
      1. COMPLETED + is_readable documents
      2. AI-detected document_type matching the requirement category
         (falls back to the uploader's declared document_type)
      3. highest extraction confidence
    Returns (None, None, {}) if nothing matches.
    """
    category_value = requirement.category.value if hasattr(requirement.category, "value") else str(requirement.category)
    acceptable_types = CATEGORY_TO_DOCUMENT_TYPES.get(category_value, {category_value})

    candidates = []
    for doc in bidder.documents:
        if doc.processing_status != DocumentProcessingStatus.COMPLETED:
            continue
        extracted = doc.extracted_data
        if not extracted or not extracted.is_readable:
            continue
        effective_type = extracted.detected_document_type or doc.document_type.value
        if effective_type in acceptable_types:
            candidates.append((doc, extracted))

    if not candidates:
        return None, None, {}

    # Prefer the highest-confidence, most-recently-uploaded match.
    candidates.sort(key=lambda pair: (pair[1].confidence or 0.0, pair[0].uploaded_at), reverse=True)
    best_doc, best_extracted = candidates[0]
    return best_doc, best_extracted, _parse_fields(best_extracted)


def bidder_identity_context(bidder: Bidder) -> Dict[str, Any]:
    """
    Best-effort company_name / pan / gstin for this bidder, pulled from
    whichever of their documents mention it - used to cross-check identity
    during verification (e.g. blacklist check, PAN name match).
    """
    context: Dict[str, Any] = {"company_name": bidder.company_name}
    for doc in bidder.documents:
        extracted = doc.extracted_data
        if not extracted or not extracted.is_readable:
            continue
        fields = _parse_fields(extracted)
        for key in ("pan", "gstin"):
            if key not in context and fields.get(key):
                context[key] = fields[key]
    return context
