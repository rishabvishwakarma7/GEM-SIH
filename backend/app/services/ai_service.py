"""
Modular AI service (LLM abstraction layer).

Wraps the Gemini API behind a stable interface so other modules
(requirement_extraction_service today; verification_service later) don't
need to change if the underlying model or prompt strategy changes.
"""
import json
import re
from typing import List, Dict, Any, Optional

from google import genai

from app.config import settings
from app.core.logging_config import logger

SUPPORTED_CATEGORIES = [
    "identity", "pan", "gst", "udyam_msme", "company_registration",
    "financial", "turnover", "income_tax", "startup_dpiit", "nsic",
    "epfo", "esic", "blacklist_debarment", "digilocker", "bis",
    "make_in_india", "other",
]

SUPPORTED_VERIFICATION_TYPES = ["document", "threshold", "declaration", "database_check", "other"]

SYSTEM_PROMPT = f"""You are a compliance requirement extraction engine for Indian government
e-procurement (GeM) tender documents. You read tender text and extract ONLY the bidder
eligibility and compliance requirements that are explicitly stated in the text.

STRICT RULES — violating any of these makes your output unusable:
1. NEVER invent a requirement that is not explicitly supported by the tender text.
2. Extract only information that is actually present in the text below.
3. If a field's value is not stated in the text, output null for that field. Do not guess.
4. Every requirement MUST include an "evidence" field: the exact supporting text snippet
   from the tender, quoted as literally as possible and trimmed to the relevant sentence(s).
5. Every requirement MUST include a "page_number" field, determined from the "[PAGE n]"
   markers present in the text. Use null if you cannot determine it.
6. Assign a "confidence" score from 0.0 to 1.0 reflecting how clearly the tender text
   supports this requirement. If you are unsure, give a LOW confidence score rather than
   omitting the requirement or overstating certainty.
7. Do NOT make legal interpretations or assumptions beyond what is written in the text.
8. "category" MUST be exactly one of: {", ".join(SUPPORTED_CATEGORIES)}
9. "verification_type" MUST be exactly one of: {", ".join(SUPPORTED_VERIFICATION_TYPES)}
10. "mandatory" must be true, false, or null (null only if the text genuinely does not make
    this clear).

Respond with ONLY a single JSON object — no markdown code fences, no commentary before or
after — of exactly this shape:

{{
  "requirements": [
    {{
      "category": "financial",
      "title": "Minimum Annual Turnover",
      "description": "Bidder must have minimum annual turnover of Rs. 5 crore",
      "minimum_value": 50000000,
      "currency": "INR",
      "period": "last 3 financial years",
      "mandatory": true,
      "required_documents": ["audited financial statements"],
      "verification_type": "document",
      "confidence": 0.94,
      "evidence": "The bidder must have a minimum average annual turnover of Rs. 5 crore...",
      "page_number": 4
    }}
  ]
}}

If the tender text contains no identifiable compliance requirements, respond with exactly:
{{"requirements": []}}
"""


# ---------------------------------------------------------------------------
# Bidder Document Intelligence (Day 3)
# ---------------------------------------------------------------------------

BIDDER_DOCUMENT_TYPES = [
    "pan", "gst", "udyam_msme", "company_registration", "income_tax",
    "startup_dpiit", "nsic", "epfo", "esic", "digilocker", "bis",
    "financial_statement", "turnover_certificate", "make_in_india", "other",
]

# Fields the extraction pipeline expects for each document type, used to
# compute `missing_fields` deterministically (never trusting the model's
# self-report alone). "company_name" is expected on virtually every
# certificate/registration document and is used for identity cross-checks.
EXPECTED_FIELDS_BY_TYPE: Dict[str, List[str]] = {
    "pan": ["company_name", "pan", "status"],
    "gst": ["company_name", "gstin", "status", "registration_date"],
    "udyam_msme": ["company_name", "udyam_registration_number", "enterprise_category", "registration_date"],
    "company_registration": ["company_name", "cin", "registration_date", "registered_address"],
    "income_tax": ["company_name", "pan", "assessment_year", "acknowledgement_number"],
    "startup_dpiit": ["company_name", "dpiit_certificate_number", "registration_date"],
    "nsic": ["company_name", "nsic_certificate_number", "valid_upto"],
    "epfo": ["company_name", "epfo_establishment_id", "status"],
    "esic": ["company_name", "esic_registration_number", "status"],
    "digilocker": ["company_name", "document_reference_number", "issued_by"],
    "bis": ["company_name", "bis_license_number", "valid_upto"],
    "financial_statement": ["company_name", "financial_year", "turnover_amount", "currency"],
    "turnover_certificate": ["company_name", "turnover_amount", "currency", "period", "certifying_authority"],
    "make_in_india": ["company_name", "local_content_percentage", "certifying_authority"],
    "other": ["company_name"],
}

SYSTEM_PROMPT_BIDDER_DOC = f"""You are a document classification and structured-data extraction
engine for bidder eligibility documents submitted against Indian government e-procurement (GeM)
tenders. You read OCR/text-extracted content from ONE uploaded document (PAN card, GST
certificate, Udyam/MSME certificate, company registration, financial statement, etc.) and
identify what type of document it is, then extract the structured fields that document contains.

STRICT RULES — violating any of these makes your output unusable:
1. NEVER invent a value that is not explicitly present in the text below.
2. If a field cannot be confidently read from the text, output null for it. Do not guess.
3. "document_type" MUST be exactly one of: {", ".join(BIDDER_DOCUMENT_TYPES)}
   Classify based on the actual content, not any filename hint you may be given.
4. "classification_confidence" (0.0-1.0) reflects how sure you are of the document_type itself.
5. "fields" is a flat object of extracted key/value pairs relevant to this document type
   (e.g. company_name, pan, gstin, cin, registration_date, turnover_amount, valid_upto,
   certifying_authority, status, etc.) — include only fields you found evidence for, plus
   null for any of that document type's standard fields you looked for but could not find.
6. "evidence" MUST be the exact supporting text snippet (or a short representative snippet if
   multiple fields), quoted as literally as possible.
7. "page_number" is taken from the "[PAGE n]" marker nearest the extracted content. Use null if
   undeterminable.
8. "confidence" (0.0-1.0) is your OVERALL confidence in the extraction as a whole. If the text is
   garbled, very short, or clearly not a real document, give a LOW score rather than omitting
   fields or overstating certainty.
9. "is_readable" is false if the input text is too garbled/empty/nonsensical to extract anything
   meaningful from (e.g. a failed OCR pass) — in that case "fields" may be empty and
   "document_type" should be your best guess or "other".
10. Do NOT make legal interpretations. Only report what is written in the text.

Respond with ONLY a single JSON object — no markdown code fences, no commentary before or after —
of exactly this shape:

{{
  "document_type": "gst",
  "classification_confidence": 0.95,
  "fields": {{
    "company_name": "ABC Industries Pvt Ltd",
    "gstin": "23ABCDE1234F1Z5",
    "status": "Active",
    "registration_date": "2022-04-12"
  }},
  "confidence": 0.94,
  "evidence": "GSTIN: 23ABCDE1234F1Z5 ... Status: Active ... Date of Registration: 12/04/2022",
  "page_number": 1,
  "is_readable": true
}}
"""


class AIExtractionError(Exception):
    pass


class AIService:
    def __init__(self):
        self._client: Optional[genai.Client] = None

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            if not settings.GEMINI_API_KEY:
                raise AIExtractionError(
                    "GEMINI_API_KEY is not configured. Set it in backend/.env"
                )
            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return self._client

    def extract_requirements_from_text(self, tender_text: str) -> List[Dict[str, Any]]:
        """
        Sends page-marked tender text to the LLM and returns a list of raw
        requirement dicts (not yet validated/coerced into DB enums — that
        happens in requirement_extraction_service, which owns persistence).
        """
        if not tender_text or not tender_text.strip():
            raise AIExtractionError("No tender text provided for extraction")

        text = tender_text
        if len(text) > settings.MAX_AI_INPUT_CHARS:
            logger.warning(
                f"Tender text truncated from {len(text)} to "
                f"{settings.MAX_AI_INPUT_CHARS} chars for AI extraction"
            )
            text = text[: settings.MAX_AI_INPUT_CHARS]

        # Defensive: strip stray quotes/whitespace some .env parsers leave in,
        # which otherwise trips Gemini's "unexpected model name format" check.
        model_name = settings.AI_MODEL.strip().strip('"').strip("'")

        try:
            response = self.client.models.generate_content(
                model=model_name,
                contents=(
                    "Extract compliance requirements from this tender document "
                    f"text:\n\n{text}"
                ),
                config={
                    "system_instruction": SYSTEM_PROMPT,
                    "max_output_tokens": 8192,
                },
            )
        except Exception as e:
            raise AIExtractionError(f"AI service call failed: {e}") from e

        raw_text = response.text or ""

        parsed = self._parse_json_response(raw_text)
        requirements = parsed.get("requirements", [])
        if not isinstance(requirements, list):
            raise AIExtractionError("AI response 'requirements' field was not a list")

        logger.info(f"AI extraction returned {len(requirements)} candidate requirements")
        return requirements

    def extract_bidder_document_fields(self, document_text: str, declared_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Sends OCR/text-extracted content from a single bidder document to the
        LLM and returns a raw dict with document_type, fields, confidence,
        evidence, page_number, is_readable — not yet validated/coerced (that
        happens in bidder_document_service, which owns persistence).
        """
        if not document_text or not document_text.strip():
            raise AIExtractionError("No document text provided for extraction")

        text = document_text
        if len(text) > settings.MAX_AI_INPUT_CHARS:
            logger.warning(
                f"Bidder document text truncated from {len(text)} to "
                f"{settings.MAX_AI_INPUT_CHARS} chars for AI extraction"
            )
            text = text[: settings.MAX_AI_INPUT_CHARS]

        model_name = settings.AI_MODEL.strip().strip('"').strip("'")

        hint = f" The uploader declared this as a '{declared_type}' document, but verify from content." if declared_type else ""
        prompt = f"Classify and extract structured data from this bidder document text.{hint}\n\n{text}"

        try:
            response = self.client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={
                    "system_instruction": SYSTEM_PROMPT_BIDDER_DOC,
                    "max_output_tokens": 4096,
                },
            )
        except Exception as e:
            raise AIExtractionError(f"AI service call failed: {e}") from e

        raw_text = response.text or ""
        parsed = self._parse_json_response(raw_text)

        if not isinstance(parsed, dict):
            raise AIExtractionError("AI response was not a JSON object")

        logger.info(
            f"AI bidder-document extraction returned type={parsed.get('document_type')} "
            f"confidence={parsed.get('confidence')}"
        )
        return parsed

    def match_requirement_to_evidence(self, requirement_text: str, document_text: str) -> Dict[str, Any]:
        """
        Matches a single tender requirement against a bidder's extracted
        document text. Belongs to the Bidder Verification module — not
        implemented yet by design (Day 2 scope excludes bidder processing).
        """
        raise NotImplementedError("AI evidence matching lands with the Bidder Verification module")

    def generate_compliance_recommendation(self, compliance_data: Dict[str, Any]) -> str:
        """
        AI Recommendation Engine (Day 6).

        Takes the ALREADY-DECIDED, deterministic compliance_engine output
        (overall_status / compliance_score / risk_level / mandatory_failed /
        the list of failed & needs-review requirements) and makes ONE extra
        LLM call to phrase a short, human-readable recommendation for the
        procurement evaluator.

        Design principle (same as the rest of this file): the AI NEVER decides
        or changes the verdict here. compliance_data is read-only input; the
        deterministic overall_status/compliance_score computed by
        compliance_engine.py is final and is passed in as fact, not as
        something the model is asked to re-derive. This call only produces
        2-3 lines of natural-language framing on top of a decision that has
        already been made.
        """
        overall_status = compliance_data.get("overall_status", "NEEDS_REVIEW")
        score = compliance_data.get("compliance_score", 0)
        risk_level = compliance_data.get("risk_level", "medium")
        mandatory_failed = compliance_data.get("mandatory_failed", False)
        failed_requirements = compliance_data.get("failed_requirements", [])
        needs_review_requirements = compliance_data.get("needs_review_requirements", [])
        company_name = compliance_data.get("company_name", "The bidder")

        prompt = f"""A deterministic rule engine (not you) has ALREADY decided the following
compliance verdict for a GeM tender bidder. Do not re-evaluate, second-guess, or change this
verdict — it is final. Your ONLY job is to write a short, plain-English recommendation for a
government procurement evaluator who will read this alongside the full requirement breakdown.

Bidder: {company_name}
Final status (already decided, do not change): {overall_status}
Compliance score (already decided): {score}%
Risk level (already decided): {risk_level}
Mandatory requirement failed: {mandatory_failed}
Failed requirements: {json.dumps(failed_requirements) if failed_requirements else "none"}
Requirements needing manual review: {json.dumps(needs_review_requirements) if needs_review_requirements else "none"}

Write EXACTLY 2-3 sentences (no headings, no bullet points, no markdown) giving the evaluator a
plain-English recommendation: whether to proceed with this bidder, what specifically needs
attention before an award decision, or why they should be rejected. Be concrete about which
requirement(s) drive the recommendation when there are failures or review items. Do not repeat
the raw numbers verbatim if you can phrase them naturally. Do not invent any fact not given
above."""

        model_name = settings.AI_MODEL.strip().strip('"').strip("'")
        try:
            response = self.client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={"max_output_tokens": 400},
            )
        except Exception as e:
            raise AIExtractionError(f"AI recommendation call failed: {e}") from e

        text = (response.text or "").strip()
        if not text:
            raise AIExtractionError("AI recommendation call returned empty text")
        logger.info(f"AI recommendation generated for {company_name} ({len(text)} chars)")
        return text

    @staticmethod
    def _parse_json_response(raw_text: str) -> Dict[str, Any]:
        cleaned = raw_text.strip()
        # Defensive: strip markdown code fences in case the model adds them
        # despite instructions not to.
        fence_match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL)
        if fence_match:
            cleaned = fence_match.group(1)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI JSON response: {e}\nRaw response (truncated): {raw_text[:2000]}")
            raise AIExtractionError(f"AI returned invalid JSON: {e}") from e


ai_service = AIService()
