"""
Dashboard aggregation endpoints (Day 5).
Read-only rollups over tenders/bidders/compliance_results for the main
dashboard: summary cards + a searchable/filterable/sortable/paginated
bidder table.
"""
import math
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.tender import Tender
from app.models.bidder import Bidder
from app.models.compliance import ComplianceResult, ComplianceStatus
from app.core.deps import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_tenders = db.query(func.count(Tender.id)).scalar() or 0
    total_bidders = db.query(func.count(Bidder.id)).scalar() or 0

    status_counts = dict(
        db.query(ComplianceResult.overall_status, func.count(ComplianceResult.id))
        .group_by(ComplianceResult.overall_status)
        .all()
    )
    compliant = status_counts.get(ComplianceStatus.COMPLIANT, 0)
    non_compliant = status_counts.get(ComplianceStatus.NON_COMPLIANT, 0)
    needs_review = status_counts.get(ComplianceStatus.NEEDS_REVIEW, 0)

    avg_score = db.query(func.avg(ComplianceResult.compliance_score)).scalar()

    return {
        "total_tenders": total_tenders,
        "total_bidders": total_bidders,
        "compliant_bidders": compliant,
        "non_compliant_bidders": non_compliant,
        "needs_review_bidders": needs_review,
        "average_compliance_score": round(float(avg_score), 1) if avg_score is not None else None,
        "evaluated_bidders": compliant + non_compliant + needs_review,
    }


@router.get("/bidders")
def get_dashboard_bidder_table(
    search: Optional[str] = Query(None, description="Search bidder company name or GeM seller ID"),
    status: Optional[str] = Query(None, description="compliant | non_compliant | needs_review | not_evaluated"),
    tender_id: Optional[str] = Query(None),
    sort_by: str = Query("company_name", description="company_name | compliance_score | status"),
    sort_dir: str = Query("asc", description="asc | desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Bidder, ComplianceResult, Tender).join(
        Tender, Tender.id == Bidder.tender_id
    ).outerjoin(
        ComplianceResult, ComplianceResult.bidder_id == Bidder.id
    )

    if tender_id:
        q = q.filter(Bidder.tender_id == tender_id)

    if search:
        like = f"%{search}%"
        q = q.filter(or_(Bidder.company_name.ilike(like), Bidder.gem_seller_id.ilike(like)))

    if status:
        if status == "not_evaluated":
            q = q.filter(ComplianceResult.id.is_(None))
        else:
            q = q.filter(ComplianceResult.overall_status == status)

    total = q.count()

    sort_col = {
        "company_name": Bidder.company_name,
        "compliance_score": ComplianceResult.compliance_score,
        "status": ComplianceResult.overall_status,
    }.get(sort_by, Bidder.company_name)
    q = q.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())

    offset = (page - 1) * page_size
    rows = q.offset(offset).limit(page_size).all()

    items = []
    for bidder, cr, tender in rows:
        failed_count = int(cr.non_compliant_count) if cr and cr.non_compliant_count else 0
        review_count = int(cr.needs_review_count) if cr and cr.needs_review_count else 0
        items.append({
            "bidder_id": str(bidder.id),
            "company_name": bidder.company_name,
            "gem_seller_id": bidder.gem_seller_id,
            "tender_id": str(tender.id),
            "tender_ref_no": tender.tender_ref_no,
            "compliance_score": cr.compliance_score if cr else None,
            "status": cr.overall_status.value if cr and cr.overall_status else "not_evaluated",
            "risk_level": cr.risk_level.value if cr and cr.risk_level else None,
            "failed_requirements": failed_count,
            "review_items": review_count,
            "evaluated_at": cr.evaluated_at.isoformat() if cr and cr.evaluated_at else None,
        })

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": max(1, math.ceil(total / page_size)),
    }
