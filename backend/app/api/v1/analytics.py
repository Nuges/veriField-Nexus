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

router = APIRouter(prefix="/analytics", tags=["Analytics"])


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

    # Total submissions
    total_sub = await db.execute(select(func.count(Activity.id)))
    # Total users
    total_users = await db.execute(select(func.count(User.id)))
    # Total properties
    total_props = await db.execute(select(func.count(Property.id)))
    # Average trust score
    avg_trust = await db.execute(
        select(func.avg(Activity.trust_score)).where(Activity.trust_score.isnot(None))
    )
    # Flagged activities
    flagged = await db.execute(
        select(func.count(Activity.id)).where(Activity.status == "flagged")
    )
    # Today's submissions
    today_sub = await db.execute(
        select(func.count(Activity.id)).where(Activity.created_at >= today_start)
    )
    # This week's submissions
    week_sub = await db.execute(
        select(func.count(Activity.id)).where(Activity.created_at >= week_start)
    )

    avg_score = avg_trust.scalar()

    return AnalyticsOverview(
        total_submissions=total_sub.scalar() or 0,
        total_users=total_users.scalar() or 0,
        total_properties=total_props.scalar() or 0,
        avg_trust_score=round(avg_score, 1) if avg_score else None,
        flagged_activities=flagged.scalar() or 0,
        submissions_today=today_sub.scalar() or 0,
        submissions_this_week=week_sub.scalar() or 0,
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
