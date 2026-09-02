"""
Demo data seeder — SIH 2026, PS 26100 (Upgrade: 5 bidder scenarios).

Creates one fully-processed demo tender with FIVE bidders covering every
major scenario the judges need to see:

  1. COMPLIANT TRADERS PVT LTD         -> COMPLIANT    (all green, score 100%)
  2. STRUGGLING SUPPLIES LLP            -> NON_COMPLIANT (mandatory GST cancelled)
  3. RELIABLE ENGINEERING WORKS         -> NEEDS_REVIEW  (low-confidence turnover)
  4. SHADOW TECH SOLUTIONS PVT LTD      -> HIGH_RISK     (suspicious doc + registry mismatch)
  5. DUPLICATE DOC ENTERPRISES LTD      -> NEEDS_REVIEW + duplicate document flag

This intentionally bypasses the live Gemini calls and writes the SAME rows
those AI stages would have produced, then runs the REAL, unmodified
verification_service and compliance_engine so what you see in the UI is the
actual rule engine deciding the verdicts.

ALL data is fictional. Run with: python seed_demo_data.py
Safe to re-run (removes previous demo data first).
"""
import json
import uuid
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models.user import User
from app.models.tender import (
    Tender, TenderRequirement, TenderStatus, ProcessingStatus,
    RequirementCategory, VerificationType,
)
from app.models.bidder import (
    Bidder, BidderDocument, BidderDocumentType, DocumentProcessingStatus,
    BidderConsistencyStatus,
)
from app.models.document import ExtractedDocumentData
from app.models.verification import VerificationResult
from app.models.compliance import ComplianceResult
from app.services.verification_service import verification_service
from app.services.compliance_engine import compliance_engine
from app.services.bidder_consistency_service import analyze_bidder

DEMO_TENDER_REF = "GEM/2026/B/6541278"


def _mk_requirement(tender_id, seq, **kw):
    defaults = dict(
        id=uuid.uuid4(), tender_id=tender_id, sequence_no=seq,
        extracted_by_ai=True, needs_review=False, confidence=0.9,
        created_at=datetime.utcnow(),
    )
    defaults.update(kw)
    return TenderRequirement(**defaults)


def _mk_document(bidder_id, doc_type, filename, **kw):
    defaults = dict(
        id=uuid.uuid4(), bidder_id=bidder_id, document_type=doc_type,
        file_path=f"./uploads/demo/{filename}", original_filename=filename,
        file_kind="pdf", uploaded_at=datetime.utcnow(),
        processing_status=DocumentProcessingStatus.COMPLETED,
        extraction_method="pymupdf", page_count=1,
    )
    defaults.update(kw)
    return BidderDocument(**defaults)


def _mk_extracted(document_id, fields, **kw):
    defaults = dict(
        id=uuid.uuid4(), bidder_document_id=document_id,
        structured_fields=json.dumps(fields), missing_fields=[],
        is_readable=True, needs_review=False, type_mismatch=False,
        confidence=0.92, page_number=1, extracted_at=datetime.utcnow(),
    )
    defaults.update(kw)
    return ExtractedDocumentData(**defaults)


def seed():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@cpcl.gem").first()
        if not admin:
            raise SystemExit("Run init_db.py first (no admin user found).")

        # --- clean slate ---
        existing = db.query(Tender).filter(Tender.tender_ref_no == DEMO_TENDER_REF).first()
        if existing:
            print(f"Removing previous demo tender {DEMO_TENDER_REF}...")
            old_bidder_ids = [b.id for b in existing.bidders]
            old_req_ids = [r.id for r in existing.requirements]
            if old_req_ids:
                db.query(VerificationResult).filter(
                    VerificationResult.requirement_id.in_(old_req_ids)
                ).delete(synchronize_session=False)
            if old_bidder_ids:
                db.query(ComplianceResult).filter(
                    ComplianceResult.bidder_id.in_(old_bidder_ids)
                ).delete(synchronize_session=False)
            db.delete(existing)
            db.commit()

        print("Creating demo tender...")
        tender = Tender(
            id=uuid.uuid4(),
            tender_ref_no=DEMO_TENDER_REF,
            title="Supply, Installation and Commissioning of Laptops",
            department="Information Technology Division",
            organization="Chennai Petroleum Corporation Limited (CPCL)",
            description=(
                "GeM tender for supply of 250 business-grade laptops with 3-year "
                "onsite warranty for CPCL Manali Refinery IT infrastructure upgrade."
            ),
            status=TenderStatus.UNDER_EVALUATION,
            tender_date=datetime.utcnow() - timedelta(days=21),
            deadline=datetime.utcnow() + timedelta(days=9),
            document_path="./sample-data/sample_tender_GEM_2026_B_6541278.pdf",
            extraction_method="pymupdf",
            page_count=5,
            processing_status=ProcessingStatus.COMPLETED,
            created_by=admin.id,
        )
        db.add(tender)
        db.flush()

        reqs = [
            _mk_requirement(
                tender.id, 1, category=RequirementCategory.GST, title="Valid & Active GST Registration",
                description="Bidder must hold a valid, Active GST registration in India.",
                clause_reference="Clause 3.1", mandatory=True,
                required_documents=["GST Registration Certificate"],
                verification_type=VerificationType.DATABASE_CHECK,
                evidence="The bidder shall furnish a valid GST registration certificate; the GSTIN must be Active.",
                page_number=2,
            ),
            _mk_requirement(
                tender.id, 2, category=RequirementCategory.PAN, title="Valid PAN of the Bidder",
                description="Bidder must possess a valid Permanent Account Number (PAN).",
                clause_reference="Clause 3.2", mandatory=True,
                required_documents=["PAN Card"],
                verification_type=VerificationType.DATABASE_CHECK,
                evidence="Bidders shall submit a copy of their PAN card.",
                page_number=2,
            ),
            _mk_requirement(
                tender.id, 3, category=RequirementCategory.TURNOVER, title="Minimum Annual Turnover",
                description="Bidder must have a minimum average annual turnover of Rs. 2 crore over the last 3 FYs.",
                clause_reference="Clause 4.1", mandatory=True,
                minimum_value=20000000, currency="INR", period="last 3 financial years",
                required_documents=["Audited Financial Statements", "Turnover Certificate from CA"],
                verification_type=VerificationType.THRESHOLD,
                evidence="Minimum average annual turnover of Rs. 2 crore during the last three financial years.",
                page_number=3,
            ),
            _mk_requirement(
                tender.id, 4, category=RequirementCategory.COMPANY_REGISTRATION,
                title="Company Registration / Incorporation",
                description="Bidder firm must be legally registered/incorporated in India.",
                clause_reference="Clause 3.3", mandatory=True,
                required_documents=["Certificate of Incorporation"],
                verification_type=VerificationType.DOCUMENT,
                evidence="The bidder must be a legally registered entity in India.",
                page_number=2,
            ),
            _mk_requirement(
                tender.id, 5, category=RequirementCategory.UDYAM_MSME,
                title="MSME / Udyam Registration (if applicable)",
                description="MSME bidders claiming EMD exemption must submit a valid Udyam registration.",
                clause_reference="Clause 5.4", mandatory=False,
                required_documents=["Udyam Registration Certificate"],
                verification_type=VerificationType.DATABASE_CHECK,
                evidence="MSME bidders seeking EMD exemption must submit a valid Udyam Registration Certificate.",
                page_number=4, confidence=0.81,
            ),
            _mk_requirement(
                tender.id, 6, category=RequirementCategory.BLACKLIST_DEBARMENT,
                title="Not Blacklisted / Debarred",
                description="Bidder must not be currently blacklisted or debarred.",
                clause_reference="Clause 3.6", mandatory=True,
                required_documents=[],
                verification_type=VerificationType.DATABASE_CHECK,
                evidence="Bidders who are currently blacklisted are not eligible to participate.",
                page_number=2,
            ),
        ]
        db.add_all(reqs)
        db.flush()

        # =================================================================
        # Bidder 1 — COMPLIANT TRADERS PVT LTD -> COMPLIANT (score ~100%)
        # =================================================================
        b1 = Bidder(
            id=uuid.uuid4(), tender_id=tender.id,
            company_name="Compliant Traders Private Limited",
            gem_seller_id="GEM-SLR-2019-0004521",
            contact_email="tenders@compliant-traders.example.in",
            contact_phone="+91-9840012345",
            created_by=admin.id,
        )
        db.add(b1); db.flush()
        for doc_type, filename, fields, detected in [
            (BidderDocumentType.GST, "GST_Certificate.pdf", {"company_name": "COMPLIANT TRADERS PRIVATE LIMITED", "gstin": "33AAACC1206D1ZM", "status": "Active", "registration_date": "2019-07-01"}, "gst"),
            (BidderDocumentType.PAN, "PAN_Card.pdf", {"company_name": "COMPLIANT TRADERS PRIVATE LIMITED", "pan": "AAACC1206D", "status": "Valid"}, "pan"),
            (BidderDocumentType.COMPANY_REGISTRATION, "Cert_Incorporation.pdf", {"company_name": "COMPLIANT TRADERS PRIVATE LIMITED", "cin": "U29100TN2015PTC098765", "registration_date": "2015-09-14", "registered_address": "Guindy, Chennai"}, "company_registration"),
            (BidderDocumentType.TURNOVER_CERTIFICATE, "Turnover_Certificate_CA.pdf", {"company_name": "COMPLIANT TRADERS PRIVATE LIMITED", "turnover_amount": 45000000, "currency": "INR", "period": "FY 2022-23", "certifying_authority": "R. Krishnan & Co, CA"}, "turnover_certificate"),
            (BidderDocumentType.UDYAM_MSME, "Udyam_Cert.pdf", {"company_name": "COMPLIANT TRADERS PRIVATE LIMITED", "udyam_registration_number": "UDYAM-TN-03-0012345", "enterprise_category": "Small", "registration_date": "2021-02-11"}, "udyam_msme"),
        ]:
            doc = _mk_document(b1.id, doc_type, filename)
            db.add(doc); db.flush()
            db.add(_mk_extracted(doc.id, fields, detected_document_type=detected, confidence=0.95))

        # =================================================================
        # Bidder 2 — STRUGGLING SUPPLIES LLP -> NON_COMPLIANT
        # (mandatory GST requirement fails: registry status = Cancelled)
        # =================================================================
        b2 = Bidder(
            id=uuid.uuid4(), tender_id=tender.id,
            company_name="Struggling Supplies LLP",
            gem_seller_id="GEM-SLR-2018-0009981",
            contact_email="accounts@strugglingsupplies.example.in",
            contact_phone="+91-9884456789",
            created_by=admin.id,
        )
        db.add(b2); db.flush()
        for doc_type, filename, fields, detected in [
            (BidderDocumentType.GST, "GST_Certificate.pdf", {"company_name": "STRUGGLING SUPPLIES LLP", "gstin": "07AABCU9603R1ZM", "status": "Cancelled", "registration_date": "2018-03-10"}, "gst"),
            (BidderDocumentType.PAN, "PAN_Card.pdf", {"company_name": "STRUGGLING SUPPLIES LLP", "pan": "AABCU9603R", "status": "Valid"}, "pan"),
            (BidderDocumentType.COMPANY_REGISTRATION, "Cert_Incorporation.pdf", {"company_name": "STRUGGLING SUPPLIES LLP", "cin": "U27100MH2010PLC112233", "registration_date": "2010-04-02", "registered_address": "MIDC Andheri, Mumbai"}, "company_registration"),
            (BidderDocumentType.TURNOVER_CERTIFICATE, "Turnover_Certificate_CA.pdf", {"company_name": "STRUGGLING SUPPLIES LLP", "turnover_amount": 8500000, "currency": "INR", "period": "FY 2022-23", "certifying_authority": "M. Iyer & Associates"}, "turnover_certificate"),
        ]:
            doc = _mk_document(b2.id, doc_type, filename)
            db.add(doc); db.flush()
            db.add(_mk_extracted(doc.id, fields, detected_document_type=detected, confidence=0.93))

        # =================================================================
        # Bidder 3 — RELIABLE ENGINEERING WORKS -> NEEDS_REVIEW
        # (turnover doc uploaded but scan quality poor → low confidence)
        # =================================================================
        b3 = Bidder(
            id=uuid.uuid4(), tender_id=tender.id,
            company_name="Reliable Engineering Works",
            gem_seller_id="GEM-SLR-2020-0002214",
            contact_email="info@reliableeng.example.in",
            contact_phone="+91-9791122334",
            created_by=admin.id,
        )
        db.add(b3); db.flush()
        for doc_type, filename, fields, detected, conf, nr in [
            (BidderDocumentType.GST, "GST_Certificate.pdf", {"company_name": "RELIABLE ENGINEERING WORKS", "gstin": "27AAAPL2356Q1Z7", "status": "Active", "registration_date": "2020-01-15"}, "gst", 0.94, False),
            (BidderDocumentType.PAN, "PAN_Card.pdf", {"company_name": "RELIABLE ENGINEERING WORKS", "pan": "AAAPL2356Q", "status": "Valid"}, "pan", 0.94, False),
            (BidderDocumentType.COMPANY_REGISTRATION, "Partnership_Deed.pdf", {"company_name": "RELIABLE ENGINEERING WORKS", "cin": None, "registration_date": "2020-01-10", "registered_address": "Ambattur, Chennai"}, "company_registration", 0.88, False),
        ]:
            doc = _mk_document(b3.id, doc_type, filename)
            db.add(doc); db.flush()
            db.add(_mk_extracted(doc.id, fields, detected_document_type=detected, confidence=conf, needs_review=nr))
        # Low-confidence turnover doc
        rew_t = _mk_document(b3.id, BidderDocumentType.TURNOVER_CERTIFICATE, "Turnover_Scan_Poor.pdf")
        db.add(rew_t); db.flush()
        db.add(_mk_extracted(rew_t.id, {"company_name": "RELIABLE ENGINEERING WORKS", "turnover_amount": 26000000, "currency": "INR", "period": "FY 2022-23", "certifying_authority": None}, detected_document_type="turnover_certificate", confidence=0.38, needs_review=True, missing_fields=["certifying_authority"], evidence="Turnover figure partially legible; certifying authority stamp illegible."))

        # =================================================================
        # Bidder 4 — SHADOW TECH SOLUTIONS PVT LTD -> HIGH RISK
        # Suspicious document + registry mismatch on both GST and PAN
        # (demonstrates risk intelligence, document risk, alert generation)
        # =================================================================
        b4 = Bidder(
            id=uuid.uuid4(), tender_id=tender.id,
            company_name="Shadow Tech Solutions Private Limited",
            gem_seller_id="GEM-SLR-2021-0007782",
            contact_email="bid@shadowtech.example.in",
            contact_phone="+91-9922334455",
            created_by=admin.id,
        )
        db.add(b4); db.flush()
        # GST: company name in doc differs from bidder name (identity mismatch signal)
        st_gst = _mk_document(b4.id, BidderDocumentType.GST, "GST_Certificate.pdf")
        db.add(st_gst); db.flush()
        db.add(_mk_extracted(st_gst.id, {
            "company_name": "SHADOW TECHNOLOGIES PVT LTD",   # name differs!
            "gstin": "29AAPCS4321B1ZK", "status": "Active", "registration_date": "2021-05-20",
        }, detected_document_type="gst", confidence=0.71, needs_review=True,
            evidence="GSTIN: 29AAPCS4321B1ZK ... company name appears altered in document header"))
        # PAN: type mismatch (declared PAN, detected as financial_statement)
        st_pan = _mk_document(b4.id, BidderDocumentType.PAN, "PAN_Card.pdf")
        db.add(st_pan); db.flush()
        db.add(_mk_extracted(st_pan.id, {
            "company_name": "SHADOW TECH SOLUTIONS PRIVATE LIMITED", "pan": "AAPCS4321B", "status": "Valid",
        }, detected_document_type="financial_statement", confidence=0.44,   # type mismatch
            type_mismatch=True, needs_review=True))
        # Turnover: plausible but low confidence
        st_to = _mk_document(b4.id, BidderDocumentType.TURNOVER_CERTIFICATE, "Turnover_Certificate.pdf")
        db.add(st_to); db.flush()
        db.add(_mk_extracted(st_to.id, {
            "company_name": "SHADOW TECH SOLUTIONS PRIVATE LIMITED", "turnover_amount": 22500000,
            "currency": "INR", "period": "FY 2022-23", "certifying_authority": "B. Sharma & Associates",
        }, detected_document_type="turnover_certificate", confidence=0.52, needs_review=True))
        # Company registration
        st_reg = _mk_document(b4.id, BidderDocumentType.COMPANY_REGISTRATION, "Cert_Incorporation.pdf")
        db.add(st_reg); db.flush()
        db.add(_mk_extracted(st_reg.id, {
            "company_name": "SHADOW TECH SOLUTIONS PRIVATE LIMITED", "cin": "U72900KA2021PTC144566",
            "registration_date": "2021-04-12", "registered_address": "Whitefield, Bengaluru",
        }, detected_document_type="company_registration", confidence=0.88))

        # =================================================================
        # Bidder 5 — DUPLICATE DOC ENTERPRISES LTD -> NEEDS_REVIEW + DUPLICATE
        # Uses the SAME turnover certificate as Bidder 1 (same filename + hash simulation)
        # Demonstrates duplicate document detection across bidders
        # =================================================================
        b5 = Bidder(
            id=uuid.uuid4(), tender_id=tender.id,
            company_name="Duplicate Doc Enterprises Limited",
            gem_seller_id="GEM-SLR-2022-0011230",
            contact_email="contact@duplic-doc.example.in",
            contact_phone="+91-9600001122",
            created_by=admin.id,
        )
        db.add(b5); db.flush()
        for doc_type, filename, fields, detected, conf in [
            (BidderDocumentType.GST, "GST_Certificate.pdf", {"company_name": "DUPLICATE DOC ENTERPRISES LIMITED", "gstin": "33AACCD9871F1ZP", "status": "Active", "registration_date": "2022-01-10"}, "gst", 0.91),
            (BidderDocumentType.PAN, "PAN_Card.pdf", {"company_name": "DUPLICATE DOC ENTERPRISES LIMITED", "pan": "AACCD9871F", "status": "Valid"}, "pan", 0.91),
            (BidderDocumentType.COMPANY_REGISTRATION, "Cert_Incorporation.pdf", {"company_name": "DUPLICATE DOC ENTERPRISES LIMITED", "cin": "U51900TN2022PTC198812", "registration_date": "2022-01-05", "registered_address": "Anna Nagar, Chennai"}, "company_registration", 0.89),
        ]:
            doc = _mk_document(b5.id, doc_type, filename)
            db.add(doc); db.flush()
            db.add(_mk_extracted(doc.id, fields, detected_document_type=detected, confidence=conf))
        # Turnover: same extracted content as Bidder 1 (simulates duplicate)
        dup_to = _mk_document(b5.id, BidderDocumentType.TURNOVER_CERTIFICATE, "Turnover_Certificate_CA.pdf",
                              file_path="./uploads/demo/Turnover_Certificate_CA.pdf")  # same path as B1 doc!
        db.add(dup_to); db.flush()
        db.add(_mk_extracted(dup_to.id, {
            "company_name": "DUPLICATE DOC ENTERPRISES LIMITED",
            "turnover_amount": 45000000,   # same value as B1
            "currency": "INR", "period": "FY 2022-23",
            "certifying_authority": "R. Krishnan & Co, CA",  # same CA as B1!
        }, detected_document_type="turnover_certificate", confidence=0.93,
            evidence="Average annual turnover of Rs. 4.5 crore..."))
        # Give it a fingerprint that matches B1's turnover doc closely
        dup_to.document_fingerprint = "averageannualturnoverofrs45croreduringfythreeyearscertifiedbyrkrishnancoca"
        db.commit()

        # --- Run the REAL pipeline stages ---
        print("Running bidder consistency analysis...")
        for bidder in (b1, b2, b3, b4, b5):
            analyze_bidder(str(bidder.id), db=db)

        print("Running verification checks (mock registries)...")
        for bidder in (b1, b2, b3, b4, b5):
            verification_service.verify_bidder_against_tender(str(bidder.id), db=db, user_id=str(admin.id))

        print("Running compliance engine...")
        for bidder in (b1, b2, b3, b4, b5):
            result = compliance_engine.evaluate_bidder(str(tender.id), str(bidder.id), db=db, user_id=str(admin.id))
            cr = result["compliance_result"]
            print(f"  {bidder.company_name}: {cr.overall_status.value.upper()} "
                  f"(score {cr.compliance_score:.1f}%, mandatory_failed={cr.mandatory_failed})")

        # Run risk analysis for each bidder
        print("Running risk intelligence analysis...")
        try:
            from app.services.risk_intelligence_service import analyze_bidder_risk
            for bidder in (b1, b2, b3, b4, b5):
                r = analyze_bidder_risk(str(bidder.id), db=db, generate_ai_summary=False)
                if r:
                    print(f"  {bidder.company_name}: risk={r['risk_level']} score={r['risk_score']:.1f}")
        except Exception as e:
            print(f"  Risk analysis skipped: {e}")

        # Run duplicate detection across the whole tender
        print("Running duplicate document detection...")
        try:
            from app.services.duplicate_detection_service import run_duplicate_check_for_tender
            matches = run_duplicate_check_for_tender(str(tender.id), db=db)
            print(f"  {len(matches)} duplicate/similar pair(s) found")
        except Exception as e:
            print(f"  Duplicate detection skipped: {e}")

        print("\nDemo dataset ready. 5 bidders seeded.")
        print(f"Tender ref: {DEMO_TENDER_REF}  (id={tender.id})")
        print("Scenarios:")
        print("  B1 Compliant Traders       -> COMPLIANT")
        print("  B2 Struggling Supplies     -> NON_COMPLIANT (GST cancelled)")
        print("  B3 Reliable Engineering    -> NEEDS_REVIEW  (low-confidence turnover)")
        print("  B4 Shadow Tech Solutions   -> HIGH_RISK     (name mismatch + type mismatch)")
        print("  B5 Duplicate Doc Ent.      -> NEEDS_REVIEW  (duplicate turnover cert)")
        print("\nLogin: admin@cpcl.gem / Admin@123")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
