"""
=============================================================================
VeriField Nexus — Analytics API Routes
=============================================================================
Dashboard analytics endpoints providing overview stats, daily trends,
activity breakdowns, and trust score distributions.
=============================================================================
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date
from datetime import datetime, timedelta, timezone

from app.db.session import get_db
from app.core.security import require_admin
from app.models.user import User
from app.models.activity import Activity
from app.models.property import Property
from app.models.anomaly_flag import AnomalyFlag
from app.schemas.analytics import (
    AnalyticsOverview, DailySubmission, ActivityTypeSummary,
    AnalyticsTrends, TrustDistribution,
)

router = APIRouter(prefix="/metrics", tags=["Analytics"])


# =============================================================================
# GET /api/v1/analytics/overview — Dashboard overview stats
# =============================================================================
@router.get(
    "/overview",
    response_model=AnalyticsOverview,
    summary="Get dashboard overview statistics",
)
async def get_overview(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """High-level platform statistics for the admin dashboard."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    # Filter all activity queries securely by admin's organization (if set)
    if user.organization:
        q_total_sub = select(func.count(Activity.id)).join(User, Activity.user_id == User.id).where(User.organization == user.organization).scalar_subquery()
        q_total_users = select(func.count(User.id)).where(User.organization == user.organization, User.role == "field_agent").scalar_subquery()
        q_total_props = select(func.count(Property.id)).join(User, Property.owner_id == User.id).where(User.organization == user.organization).scalar_subquery()
        q_avg_score = select(func.avg(Activity.trust_score)).join(User, Activity.user_id == User.id).where(User.organization == user.organization, Activity.trust_score.isnot(None)).scalar_subquery()
        q_flagged = select(func.count(AnomalyFlag.id)).join(Activity, AnomalyFlag.activity_id == Activity.id).join(User, Activity.user_id == User.id).where(User.organization == user.organization, AnomalyFlag.resolved == False).scalar_subquery()
        q_today_sub = select(func.count(Activity.id)).join(User, Activity.user_id == User.id).where(User.organization == user.organization, Activity.created_at >= today_start).scalar_subquery()
        q_week_sub = select(func.count(Activity.id)).join(User, Activity.user_id == User.id).where(User.organization == user.organization, Activity.created_at >= week_start).scalar_subquery()
    else:
        q_total_sub = select(func.count(Activity.id)).join(User, Activity.user_id == User.id).scalar_subquery()
        q_total_users = select(func.count(User.id)).where(User.role == "field_agent").scalar_subquery()
        q_total_props = select(func.count(Property.id)).scalar_subquery()
        q_avg_score = select(func.avg(Activity.trust_score)).join(User, Activity.user_id == User.id).where(Activity.trust_score.isnot(None)).scalar_subquery()
        q_flagged = select(func.count(AnomalyFlag.id)).where(AnomalyFlag.resolved == False).scalar_subquery()
        q_today_sub = select(func.count(Activity.id)).join(User, Activity.user_id == User.id).where(Activity.created_at >= today_start).scalar_subquery()
        q_week_sub = select(func.count(Activity.id)).join(User, Activity.user_id == User.id).where(Activity.created_at >= week_start).scalar_subquery()

    stmt = select(
        q_total_sub.label("total_sub"),
        q_total_users.label("total_users"),
        q_total_props.label("total_props"),
        q_avg_score.label("avg_score"),
        q_flagged.label("flagged"),
        q_today_sub.label("today_sub"),
        q_week_sub.label("week_sub")
    )

    res = await db.execute(stmt)
    row = res.fetchone()

    total_sub = row.total_sub if row else 0
    total_users = row.total_users if row else 0
    total_props = row.total_props if row else 0
    avg_score = row.avg_score if row else None
    flagged = row.flagged if row else 0
    today_sub = row.today_sub if row else 0
    week_sub = row.week_sub if row else 0

    return AnalyticsOverview(
        total_submissions=total_sub or 0,
        total_users=total_users or 0,
        total_properties=total_props or 0,
        avg_trust_score=round(avg_score, 1) if avg_score else None,
        flagged_activities=flagged or 0,
        submissions_today=today_sub or 0,
        submissions_this_week=week_sub or 0,
    )


# =============================================================================
# GET /api/v1/analytics/daily — Daily submission counts
# =============================================================================
@router.get(
    "/daily",
    response_model=list[DailySubmission],
    summary="Get daily submission counts",
    response_model_exclude_none=True,
)
async def get_daily_submissions(
    days: int = Query(30, ge=1, le=365),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Daily submission counts for the last N days."""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = select(
        cast(Activity.created_at, Date).label("date"),
        func.count(Activity.id).label("count"),
        func.avg(Activity.trust_score).label("avg_trust"),
    ).join(User, Activity.user_id == User.id)

    if user.organization:
        stmt = stmt.where(User.organization == user.organization)

    stmt = stmt.where(
        Activity.created_at >= start_date
    ).group_by(cast(Activity.created_at, Date)).order_by(cast(Activity.created_at, Date))

    result = await db.execute(stmt)

    return [
        DailySubmission(
            date=str(row.date),
            count=row.count,
            avg_trust_score=round(row.avg_trust, 1) if row.avg_trust else None,
        )
        for row in result.all()
    ]


# =============================================================================
# GET /api/v1/analytics/trends — Comprehensive trend analysis
# =============================================================================
@router.get(
    "/trends",
    response_model=AnalyticsTrends,
    summary="Get comprehensive trend analysis",
)
async def get_trends(
    days: int = Query(30, ge=1, le=365),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Comprehensive analytics including daily counts, type breakdown, and trust distribution."""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    # Daily submissions scoped to admin's organization (if set)
    stmt_daily = select(
        cast(Activity.created_at, Date).label("date"),
        func.count(Activity.id).label("count"),
        func.avg(Activity.trust_score).label("avg_trust"),
    ).join(User, Activity.user_id == User.id)

    if user.organization:
        stmt_daily = stmt_daily.where(User.organization == user.organization)

    stmt_daily = stmt_daily.where(
        Activity.created_at >= start_date
    ).group_by(cast(Activity.created_at, Date)).order_by(cast(Activity.created_at, Date))

    daily_result = await db.execute(stmt_daily)
    daily = [
        DailySubmission(date=str(r.date), count=r.count, avg_trust_score=round(r.avg_trust, 1) if r.avg_trust else None)
        for r in daily_result.all()
    ]

    # Activity type breakdown scoped to admin's organization (if set)
    stmt_total = select(func.count(Activity.id)).join(User, Activity.user_id == User.id)
    if user.organization:
        stmt_total = stmt_total.where(User.organization == user.organization)
    stmt_total = stmt_total.where(
        Activity.created_at >= start_date
    )
    total_count_result = await db.execute(stmt_total)
    total_count = total_count_result.scalar() or 1

    def get_stove_model_label(model_code: str, act_type: str) -> str:
        t = (act_type or "").upper().strip()
        if t == "ENERGY":
            return "Energy Systems"
        if t == "AGRICULTURE" or t == "FARMING":
            return "Agriculture & Farming"
        if t in ("TRANSPORT_MOBILITY", "TRANSPORT"):
            return "Transport & Mobility"
        if t in ("FORESTRY_LAND_USE", "FORESTRY"):
            return "Forestry & Land Use"
        if t == "SUSTAINABILITY":
            return "Sustainability Monitoring"
        
        m = (model_code or "").lower().strip()
        if "baikuc" in m:
            return "Baikuc Gen 1"
        if "tlud" in m or "forced" in m:
            return "TLUD Forced Draft"
        if "rocket" in m:
            return "Rocket Stove"
        if "gasifier" in m:
            return "Gasifier Stove"
        if "jiko" in m:
            return "Kenya Ceramic Jiko"
        if "lpg" in m:
            return "LPG Double Burner"
        if "electric" in m or "ics" in m:
            return "Electric ICS"
        
        if act_type and act_type != "other":
            return act_type.replace("_", " ").title()
        return "Other Methodology"

    stmt_type = select(
        Activity.activity_data,
        Activity.trust_score,
        Activity.activity_type
    ).join(User, Activity.user_id == User.id)

    if user.organization:
        stmt_type = stmt_type.where(User.organization == user.organization)

    stmt_type = stmt_type.where(
        Activity.created_at >= start_date
    )

    type_result = await db.execute(stmt_type)
    
    normalized_groups = {}
    for data_val, trust, act_type in type_result.all():
        raw_model = None
        if isinstance(data_val, dict):
            raw_model = data_val.get("stove_model")
        
        label = get_stove_model_label(raw_model, act_type)
        
        if label not in normalized_groups:
            normalized_groups[label] = {"count": 0, "sum_trust": 0.0, "count_trust": 0}
        normalized_groups[label]["count"] += 1
        if trust is not None:
            normalized_groups[label]["sum_trust"] += trust
            normalized_groups[label]["count_trust"] += 1

    types = [
        ActivityTypeSummary(
            activity_type=name,
            count=data["count"],
            percentage=round((data["count"] / total_count) * 100, 1),
            avg_trust_score=round(data["sum_trust"] / data["count_trust"], 1) if data["count_trust"] > 0 else None,
        )
        for name, data in normalized_groups.items()
    ]

    # Trust distribution scoped to admin's organization (if set)
    from sqlalchemy import case
    stmt_dist = select(
        func.sum(case((Activity.trust_score >= 80, 1), else_=0)).label("high"),
        func.sum(case((Activity.trust_score.between(50, 79.99), 1), else_=0)).label("medium"),
        func.sum(case((Activity.trust_score < 50, 1), else_=0)).label("low"),
        func.sum(case((Activity.trust_score.is_(None), 1), else_=0)).label("unscored")
    ).join(User, Activity.user_id == User.id)

    if user.organization:
        stmt_dist = stmt_dist.where(User.organization == user.organization)

    dist_res = await db.execute(stmt_dist)
    dist_row = dist_res.fetchone()

    distribution = TrustDistribution(
        high=dist_row.high or 0,
        medium=dist_row.medium or 0,
        low=dist_row.low or 0,
        unscored=dist_row.unscored or 0,
    )

    return AnalyticsTrends(daily_submissions=daily, activity_types=types, trust_distribution=distribution)


# =============================================================================
# GET /api/v1/analytics/trust-distribution — Trust score histogram
# =============================================================================
@router.get(
    "/trust-distribution",
    response_model=TrustDistribution,
    summary="Get trust score distribution",
)
async def get_trust_distribution(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import case
    stmt = select(
        func.sum(case((Activity.trust_score >= 80, 1), else_=0)).label("high"),
        func.sum(case((Activity.trust_score.between(50, 79.99), 1), else_=0)).label("medium"),
        func.sum(case((Activity.trust_score < 50, 1), else_=0)).label("low"),
        func.sum(case((Activity.trust_score.is_(None), 1), else_=0)).label("unscored")
    ).join(User, Activity.user_id == User.id)

    if user.organization:
        stmt = stmt.where(User.organization == user.organization)

    dist_res = await db.execute(stmt)
    dist_row = dist_res.fetchone()

    return TrustDistribution(
        high=dist_row.high or 0,
        medium=dist_row.medium or 0,
        low=dist_row.low or 0,
        unscored=dist_row.unscored or 0,
    )


# =============================================================================
# GET /api/v1/metrics/agents — Agent performance analytics
# =============================================================================
@router.get(
    "/agents",
    summary="Get agent performance analytics",
)
async def get_agent_performance(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Per-agent analytics: submission count, avg trust score, flag count,
    and suspicious status (agents with avg trust < 50 or > 20% flagged).
    """
    # Get all agents with their activity stats
    stmt = select(
        User.id,
        User.full_name,
        User.email,
        User.role,
        User.organization,
        User.status,
        func.count(Activity.id).label("total_submissions"),
        func.avg(Activity.trust_score).label("avg_trust_score"),
    ).outerjoin(Activity, User.id == Activity.user_id)

    if user.organization:
        stmt = stmt.where(User.organization == user.organization)

    stmt = stmt.where(User.role == "field_agent").group_by(User.id).order_by(func.count(Activity.id).desc())

    result = await db.execute(stmt)

    # Fallback: use separate queries for flag count since CASE may vary
    agents_raw = result.all()

    agents = []
    for row in agents_raw:
        # Get flagged count separately for reliability
        flag_result = await db.execute(
            select(func.count(Activity.id))
            .where(Activity.user_id == row.id, Activity.status == "flagged")
        )
        flagged_count = flag_result.scalar() or 0

        total = row.total_submissions or 0
        avg_trust = round(row.avg_trust_score, 1) if row.avg_trust_score else None
        flag_rate = round((flagged_count / total * 100), 1) if total > 0 else 0

        # Suspicious if avg trust < 50 or > 20% flagged
        suspicious = False
        if avg_trust is not None and avg_trust < 50:
            suspicious = True
        if flag_rate > 20:
            suspicious = True

        agents.append({
            "id": str(row.id),
            "full_name": row.full_name,
            "email": row.email,
            "role": row.role,
            "organization": row.organization,
            "total_submissions": total,
            "avg_trust_score": avg_trust,
            "flagged_count": flagged_count,
            "flag_rate": flag_rate,
            "suspicious": suspicious,
            "status": getattr(row, "status", "active"),
        })

    return {
        "agents": agents,
        "total_agents": len(agents),
        "suspicious_count": sum(1 for a in agents if a["suspicious"]),
    }


# =============================================================================
# GET /api/v1/metrics/anomalies — Fetch AI-detected anomaly flags
# =============================================================================
@router.get(
    "/anomalies",
    summary="Get recent anomaly flags",
)
async def get_anomalies(
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Fetch the latest anomaly flags detected by the AI."""
    stmt = select(AnomalyFlag, Activity)\
        .join(Activity, AnomalyFlag.activity_id == Activity.id)\
        .join(User, Activity.user_id == User.id)

    if user.organization:
        stmt = stmt.where(User.organization == user.organization)

    stmt = stmt.order_by(AnomalyFlag.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    
    anomalies = []
    for flag, activity in result.all():
        anomalies.append({
            "id": str(flag.id),
            "activity_id": str(flag.activity_id),
            "user_id": str(flag.user_id),
            "flag_type": flag.flag_type,
            "severity": flag.severity,
            "description": flag.description,
            "resolved": flag.resolved,
            "resolved_by": flag.resolved_by,
            "created_at": flag.created_at.isoformat() if flag.created_at else None,
            "activity_type": activity.activity_type,
            "activity_status": activity.status,
            "image_url": activity.image_url,
        })

    return {"anomalies": anomalies, "total": len(anomalies)}

# =============================================================================
# PATCH /api/v1/metrics/anomalies/{flag_id}/resolve — Resolve anomaly
# =============================================================================
from pydantic import BaseModel
import uuid

class AnomalyResolve(BaseModel):
    action: str  # "verify" or "reject"
    notes: str = ""

@router.patch(
    "/anomalies/{flag_id}/resolve",
    summary="Resolve an AI anomaly flag",
)
async def resolve_anomaly(
    flag_id: uuid.UUID,
    payload: AnomalyResolve,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Mark an anomaly as resolved and update the underlying activity."""
    result = await db.execute(select(AnomalyFlag).where(AnomalyFlag.id == flag_id))
    flag = result.scalar_one_or_none()
    if not flag:
        raise HTTPException(status_code=404, detail="Anomaly flag not found")

    act_result = await db.execute(select(Activity).where(Activity.id == flag.activity_id))
    activity = act_result.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="Associated activity not found")

    if payload.action not in ("verify", "reject"):
        raise HTTPException(status_code=400, detail="Action must be 'verify' or 'reject'")

    # Update Flag
    flag.resolved = True
    flag.resolved_by = user.email
    flag.resolution_notes = payload.notes

    # Update Activity
    if payload.action == "verify":
        activity.status = "verified"
        # Since an admin manually verified it, force the trust score to 100 for the ledger
        activity.trust_score = 100.0
    else:
        activity.status = "rejected"

    await db.commit()
    
    # If verified, trigger quantification engine asynchronously
    if payload.action == "verify":
        import asyncio
        from app.services.quantification_engine import QuantificationEngine
        async def run_quantification(act_id):
            try:
                async with app.db.session.async_session_factory() as temp_db:
                    engine = QuantificationEngine(temp_db)
                    await engine.quantify_activity(act_id, None)
            except Exception as e:
                import logging
                logging.getLogger("verifield.api").error(f"Async resolve-quantification failed for {act_id}: {e}")
        
        import app.db.session
        asyncio.create_task(run_quantification(activity.id))

    return {"status": "success", "message": f"Activity {payload.action}ed"}

