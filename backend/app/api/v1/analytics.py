"""
=============================================================================
VeriField Nexus — Analytics API Routes
=============================================================================
Dashboard analytics endpoints providing overview stats, daily trends,
activity breakdowns, and trust score distributions.
=============================================================================
"""

from fastapi import APIRouter, Depends, Query
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

    import asyncio
    from app.db.session import async_session_factory

    async def fetch_scalar(stmt):
        # Checkout a dedicated connection from QueuePool for concurrent execution
        async with async_session_factory() as temp_db:
            res = await temp_db.execute(stmt)
            return res.scalar()
            
    # Execute all 7 queries concurrently using 7 separate connections from the pool
    # This reduces total latency from ~17s to ~2s
    results = await asyncio.gather(
        fetch_scalar(select(func.count(Activity.id))),
        fetch_scalar(select(func.count(User.id))),
        fetch_scalar(select(func.count(Property.id))),
        fetch_scalar(select(func.avg(Activity.trust_score)).where(Activity.trust_score.isnot(None))),
        fetch_scalar(select(func.count(Activity.id)).where(Activity.status == "flagged")),
        fetch_scalar(select(func.count(Activity.id)).where(Activity.created_at >= today_start)),
        fetch_scalar(select(func.count(Activity.id)).where(Activity.created_at >= week_start)),
    )
    
    total_sub, total_users, total_props, avg_score, flagged, today_sub, week_sub = results

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
)
async def get_daily_submissions(
    days: int = Query(30, ge=1, le=365),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Daily submission counts for the last N days."""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            cast(Activity.created_at, Date).label("date"),
            func.count(Activity.id).label("count"),
            func.avg(Activity.trust_score).label("avg_trust"),
        )
        .where(Activity.created_at >= start_date)
        .group_by(cast(Activity.created_at, Date))
        .order_by(cast(Activity.created_at, Date))
    )

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

    # Daily submissions
    daily_result = await db.execute(
        select(
            cast(Activity.created_at, Date).label("date"),
            func.count(Activity.id).label("count"),
            func.avg(Activity.trust_score).label("avg_trust"),
        )
        .where(Activity.created_at >= start_date)
        .group_by(cast(Activity.created_at, Date))
        .order_by(cast(Activity.created_at, Date))
    )
    daily = [
        DailySubmission(date=str(r.date), count=r.count, avg_trust_score=round(r.avg_trust, 1) if r.avg_trust else None)
        for r in daily_result.all()
    ]

    # Activity type breakdown
    total_count_result = await db.execute(
        select(func.count(Activity.id)).where(Activity.created_at >= start_date)
    )
    total_count = total_count_result.scalar() or 1

    type_result = await db.execute(
        select(
            Activity.activity_type,
            func.count(Activity.id).label("count"),
            func.avg(Activity.trust_score).label("avg_trust"),
        )
        .where(Activity.created_at >= start_date)
        .group_by(Activity.activity_type)
    )
    types = [
        ActivityTypeSummary(
            activity_type=r.activity_type, count=r.count,
            percentage=round((r.count / total_count) * 100, 1),
            avg_trust_score=round(r.avg_trust, 1) if r.avg_trust else None,
        )
        for r in type_result.all()
    ]

    # Trust distribution
    high = await db.execute(select(func.count(Activity.id)).where(Activity.trust_score >= 80))
    medium = await db.execute(select(func.count(Activity.id)).where(Activity.trust_score.between(50, 79.99)))
    low = await db.execute(select(func.count(Activity.id)).where(Activity.trust_score < 50, Activity.trust_score.isnot(None)))
    unscored = await db.execute(select(func.count(Activity.id)).where(Activity.trust_score.is_(None)))

    distribution = TrustDistribution(
        high=high.scalar() or 0, medium=medium.scalar() or 0,
        low=low.scalar() or 0, unscored=unscored.scalar() or 0,
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
    """Trust score distribution across all activities."""
    high = await db.execute(select(func.count(Activity.id)).where(Activity.trust_score >= 80))
    medium = await db.execute(select(func.count(Activity.id)).where(Activity.trust_score.between(50, 79.99)))
    low = await db.execute(select(func.count(Activity.id)).where(Activity.trust_score < 50, Activity.trust_score.isnot(None)))
    unscored = await db.execute(select(func.count(Activity.id)).where(Activity.trust_score.is_(None)))

    return TrustDistribution(
        high=high.scalar() or 0, medium=medium.scalar() or 0,
        low=low.scalar() or 0, unscored=unscored.scalar() or 0,
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
    result = await db.execute(
        select(
            User.id,
            User.full_name,
            User.email,
            User.role,
            User.organization,
            func.count(Activity.id).label("total_submissions"),
            func.avg(Activity.trust_score).label("avg_trust_score"),
        )
        .outerjoin(Activity, User.id == Activity.user_id)
        .group_by(User.id)
        .order_by(func.count(Activity.id).desc())
    )

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
    result = await db.execute(
        select(AnomalyFlag, Activity)
        .join(Activity, AnomalyFlag.activity_id == Activity.id)
        .order_by(AnomalyFlag.created_at.desc())
        .limit(limit)
    )
    
    anomalies = []
    for flag, activity in result.all():
        anomalies.append({
            "id": str(flag.id),
            "activity_id": str(flag.activity_id),
            "user_id": str(flag.user_id),
            "flag_type": flag.flag_type,
            "severity": flag.severity,
            "description": flag.description,
            "created_at": flag.created_at.isoformat() if flag.created_at else None,
            "activity_type": activity.activity_type,
            "activity_status": activity.status,
            "image_url": activity.image_url,
        })

    return {"anomalies": anomalies, "total": len(anomalies)}

