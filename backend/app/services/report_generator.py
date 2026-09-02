"""
Compliance report generation service (Day 5).

Builds a professional PDF compliance report per bidder using ReportLab, and
a CSV export of the same requirement-wise data. Both pull directly from the
persisted ComplianceResult / VerificationResult / AuditLog rows so the report
always reflects the latest evaluation -- nothing here re-derives compliance
logic, it only renders what compliance_engine.py already computed.
"""
import csv
import io
import json
from datetime import datetime
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from sqlalchemy.orm import Session

from app.models.tender import Tender
from app.models.bidder import Bidder
from app.models.compliance import ComplianceResult
from app.models.verification import VerificationResult
from app.models.audit import AuditLog

STATUS_COLORS = {
    "COMPLIANT": colors.HexColor("#15803d"),
    "NON_COMPLIANT": colors.HexColor("#b91c1c"),
    "NEEDS_REVIEW": colors.HexColor("#b45309"),
    "compliant": colors.HexColor("#15803d"),
    "non_compliant": colors.HexColor("#b91c1c"),
    "needs_review": colors.HexColor("#b45309"),
}

STATUS_ICON = {
    "COMPLIANT": "COMPLIANT",
    "NON_COMPLIANT": "NON-COMPLIANT",
    "NEEDS_REVIEW": "NEEDS REVIEW",
    "compliant": "COMPLIANT",
    "non_compliant": "NON-COMPLIANT",
    "needs_review": "NEEDS REVIEW",
}


def _fmt(v: Any) -> str:
    if v is None or v == "":
        return "-"
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, float):
        # Whole-number floats (e.g. 45000000.0 from a threshold comparison)
        # render as a comma-separated integer instead of a raw float string,
        # matching the "Minimum 20,000,000 INR" style used for required_value.
        if v == int(v):
            return f"{int(v):,}"
        return f"{v:,.2f}"
    if isinstance(v, int):
        return f"{v:,}"
    return str(v)


def _gather_report_data(bidder_id: str, db: Session) -> Dict[str, Any]:
    bidder = db.query(Bidder).filter(Bidder.id == bidder_id).first()
    if not bidder:
        raise ValueError("Bidder not found")

    tender = db.query(Tender).filter(Tender.id == bidder.tender_id).first()

    compliance = (
        db.query(ComplianceResult).filter(ComplianceResult.bidder_id == bidder_id).first()
    )
    if not compliance:
        raise ValueError("No compliance evaluation exists yet for this bidder -- run verification first")

    try:
        requirement_results = (
            json.loads(compliance.requirement_results) if compliance.requirement_results else []
        )
    except (json.JSONDecodeError, TypeError):
        requirement_results = []

    verification_results = (
        db.query(VerificationResult).filter(VerificationResult.bidder_id == bidder_id).all()
    )

    audit_logs = (
        db.query(AuditLog)
        .filter(AuditLog.entity_type == "bidder", AuditLog.entity_id == str(bidder_id))
        .order_by(AuditLog.created_at.desc())
        .limit(20)
        .all()
    )

    failed = [r for r in requirement_results if r.get("status") == "NON_COMPLIANT"]
    review = [r for r in requirement_results if r.get("status") == "NEEDS_REVIEW"]

    return {
        "tender": tender,
        "bidder": bidder,
        "compliance": compliance,
        "requirement_results": requirement_results,
        "failed": failed,
        "review": review,
        "verification_results": verification_results,
        "audit_logs": audit_logs,
    }


class ReportGenerator:
    def generate_compliance_report_pdf(self, bidder_id: str, db: Session) -> bytes:
        """Renders the full compliance report PDF for one bidder and returns the raw bytes."""
        data = _gather_report_data(bidder_id, db)
        tender: Tender = data["tender"]
        bidder: Bidder = data["bidder"]
        compliance: ComplianceResult = data["compliance"]

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            topMargin=18 * mm,
            bottomMargin=16 * mm,
            leftMargin=16 * mm,
            rightMargin=16 * mm,
            title=f"Compliance Report - {bidder.company_name}",
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle", parent=styles["Title"], fontSize=16, spaceAfter=2, textColor=colors.HexColor("#1e3a5f")
        )
        subtitle_style = ParagraphStyle(
            "ReportSubtitle", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#555555")
        )
        h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12, spaceBefore=14, spaceAfter=6, textColor=colors.HexColor("#1e3a5f"))
        body = ParagraphStyle("Body", parent=styles["Normal"], fontSize=8.5, leading=11)
        small = ParagraphStyle("Small", parent=styles["Normal"], fontSize=7.5, leading=10, textColor=colors.HexColor("#444444"))

        story: List[Any] = []

        story.append(Paragraph("AI-Powered Bid Compliance Verification Report", title_style))
        story.append(Paragraph(
            "GeM Procurement &middot; Chennai Petroleum Corporation Limited (CPCL) &middot; SIH 2026 &middot; PS 26100",
            subtitle_style,
        ))
        story.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%d %b %Y, %H:%M UTC')}", subtitle_style))
        story.append(Spacer(1, 10))

        story.append(Paragraph("Tender Information", h2))
        tender_rows = [
            ["Reference No.", Paragraph(_fmt(tender.tender_ref_no if tender else None), small), "Organization", Paragraph(_fmt(tender.organization if tender else None), small)],
            ["Title", Paragraph(_fmt(tender.title if tender else None), small), "Department", Paragraph(_fmt(tender.department if tender else None), small)],
            ["Status", Paragraph(_fmt(tender.status.value if tender and tender.status else None), small), "Deadline", Paragraph(_fmt(tender.deadline.strftime("%d %b %Y") if tender and tender.deadline else None), small)],
        ]
        info_table_style = TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#555555")),
            ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor("#555555")),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ])
        t = Table(tender_rows, colWidths=[70, 165, 70, 165])
        t.setStyle(info_table_style)
        story.append(t)

        label_style = ParagraphStyle("InfoLabel", parent=styles["Normal"], fontSize=8, fontName="Helvetica-Bold", textColor=colors.HexColor("#555555"))

        def _label(text: str) -> Paragraph:
            return Paragraph(text, label_style)

        story.append(Paragraph("Bidder Information", h2))
        bidder_rows = [
            [_label("Company Name"), Paragraph(_fmt(bidder.company_name), small), _label("GeM Seller ID"), Paragraph(_fmt(bidder.gem_seller_id), small)],
            [_label("Contact Email"), Paragraph(_fmt(bidder.contact_email), small), _label("Contact Phone"), Paragraph(_fmt(bidder.contact_phone), small)],
            [_label("Identity Consistency"), Paragraph(_fmt(bidder.consistency_status.value if bidder.consistency_status else None), small), _label("Analyzed At"), Paragraph(_fmt(bidder.analyzed_at.strftime("%d %b %Y %H:%M") if bidder.analyzed_at else None), small)],
        ]
        t2 = Table(bidder_rows, colWidths=[70, 165, 70, 165])
        t2.setStyle(info_table_style)
        story.append(t2)

        story.append(Paragraph("Overall Compliance Verdict", h2))
        status_key = compliance.overall_status.value if compliance.overall_status else "needs_review"
        status_label = STATUS_ICON.get(status_key, status_key.upper())
        status_color = STATUS_COLORS.get(status_key, colors.grey)
        verdict_rows = [
            ["Overall Status", "Compliance Score", "Risk Level", "Mandatory Failed"],
            [
                status_label,
                f"{compliance.compliance_score:.1f}%",
                _fmt(compliance.risk_level.value if compliance.risk_level else None).upper(),
                "YES" if compliance.mandatory_failed else "NO",
            ],
        ]
        t3 = Table(verdict_rows, colWidths=[118, 118, 118, 116])
        t3.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2f7")),
            ("TEXTCOLOR", (0, 1), (0, 1), status_color),
            ("FONTNAME", (0, 1), (0, 1), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ]))
        story.append(t3)
        if compliance.explanation:
            story.append(Spacer(1, 6))
            story.append(Paragraph(f"<b>Explanation:</b> {compliance.explanation}", body))

        story.append(Spacer(1, 6))
        story.append(Paragraph(
            f"Total requirements: {compliance.total_requirements} &nbsp;|&nbsp; "
            f"Compliant: {compliance.compliant_count} &nbsp;|&nbsp; "
            f"Non-compliant: {compliance.non_compliant_count} &nbsp;|&nbsp; "
            f"Needs review: {compliance.needs_review_count}",
            body,
        ))

        story.append(Paragraph("Requirement-wise Results", h2))
        req_header = ["Requirement", "Required", "Actual", "Status", "Evidence / Reason"]
        req_rows = [req_header]
        for r in data["requirement_results"]:
            status_lbl = STATUS_ICON.get(r.get("status", ""), r.get("status", ""))
            evidence_text = r.get("evidence") or r.get("reason") or "-"
            source = r.get("source_document")
            if source:
                evidence_text = f"{evidence_text} (Source: {source})"
            req_rows.append([
                Paragraph(_fmt(r.get("requirement")), small),
                Paragraph(_fmt(r.get("required_value")), small),
                Paragraph(_fmt(r.get("actual_value")), small),
                Paragraph(status_lbl, small),
                Paragraph(_fmt(evidence_text), small),
            ])
        t4 = Table(req_rows, colWidths=[88, 55, 55, 82, 190], repeatRows=1)
        req_style = [
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2f7")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]
        for idx, r in enumerate(data["requirement_results"], start=1):
            c = STATUS_COLORS.get(r.get("status", ""), colors.black)
            req_style.append(("TEXTCOLOR", (3, idx), (3, idx), c))
        t4.setStyle(TableStyle(req_style))
        story.append(t4)

        if data["failed"]:
            story.append(Paragraph("Failed Requirements (Non-Compliant)", h2))
            for r in data["failed"]:
                story.append(Paragraph(f"&#8226; <b>{_fmt(r.get('requirement'))}</b> -- {_fmt(r.get('reason'))}", body))

        if data["review"]:
            story.append(Paragraph("Items Needing Manual Review", h2))
            for r in data["review"]:
                story.append(Paragraph(f"&#8226; <b>{_fmt(r.get('requirement'))}</b> -- {_fmt(r.get('reason'))}", body))

        story.append(PageBreak())
        story.append(Paragraph("External Verification Results", h2))
        if data["verification_results"]:
            v_rows = [["Provider", "Identifier Checked", "Status", "Notes"]]
            for v in data["verification_results"]:
                v_rows.append([
                    _fmt(v.provider_name),
                    Paragraph(_fmt(v.identifier_checked), small),
                    _fmt(v.status.value if v.status else None).upper(),
                    Paragraph(_fmt(v.notes or v.evidence_snippet), small),
                ])
            t5 = Table(v_rows, colWidths=[90, 110, 80, 190], repeatRows=1)
            t5.setStyle(TableStyle([
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2f7")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(t5)
            story.append(Paragraph(
                "All verification checks above are performed against mock government-registry "
                "providers for hackathon demonstration purposes.", small,
            ))
        else:
            story.append(Paragraph("No external verification checks have been run for this bidder.", body))

        story.append(Paragraph("Audit Information", h2))
        if data["audit_logs"]:
            a_rows = [["Timestamp (UTC)", "Action", "Details"]]
            for log in data["audit_logs"]:
                a_rows.append([
                    log.created_at.strftime("%d %b %Y %H:%M") if log.created_at else "-",
                    _fmt(log.action),
                    Paragraph(_fmt(log.details)[:180], small),
                ])
            t6 = Table(a_rows, colWidths=[90, 110, 270], repeatRows=1)
            t6.setStyle(TableStyle([
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2f7")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(t6)
        else:
            story.append(Paragraph("No audit log entries recorded for this bidder yet.", body))

        story.append(Spacer(1, 14))
        story.append(Paragraph(
            "This report was generated automatically by the AI-Powered Integrated Bid Compliance "
            "Verification Platform. All AI-derived extractions carry a confidence score and should "
            "be reviewed by an authorized evaluator before final award decisions.",
            small,
        ))

        doc.build(story)
        return buffer.getvalue()

    def generate_compliance_report_csv(self, bidder_id: str, db: Session) -> bytes:
        """Renders a CSV export of the requirement-wise compliance results for one bidder."""
        data = _gather_report_data(bidder_id, db)
        tender: Tender = data["tender"]
        bidder: Bidder = data["bidder"]
        compliance: ComplianceResult = data["compliance"]

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["Tender Ref No.", tender.tender_ref_no if tender else ""])
        writer.writerow(["Tender Title", tender.title if tender else ""])
        writer.writerow(["Bidder", bidder.company_name])
        writer.writerow(["GeM Seller ID", bidder.gem_seller_id or ""])
        writer.writerow(["Overall Status", compliance.overall_status.value if compliance.overall_status else ""])
        writer.writerow(["Compliance Score", f"{compliance.compliance_score:.1f}"])
        writer.writerow(["Risk Level", compliance.risk_level.value if compliance.risk_level else ""])
        writer.writerow(["Mandatory Failed", "Yes" if compliance.mandatory_failed else "No"])
        writer.writerow(["Evaluated At", compliance.evaluated_at.isoformat() if compliance.evaluated_at else ""])
        writer.writerow([])
        writer.writerow([
            "Requirement", "Category", "Mandatory", "Required Value", "Actual Value",
            "Status", "Reason", "Evidence", "Source Document", "Verification Provider",
        ])
        for r in data["requirement_results"]:
            writer.writerow([
                r.get("requirement", ""),
                r.get("category", ""),
                "Yes" if r.get("mandatory") else "No",
                r.get("required_value", ""),
                r.get("actual_value", ""),
                r.get("status", ""),
                r.get("reason", ""),
                r.get("evidence", ""),
                r.get("source_document", ""),
                r.get("verification_provider", ""),
            ])
        return buf.getvalue().encode("utf-8")


report_generator = ReportGenerator()
