from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.activities.models import Activity
from app.domains.assets.models import Asset
from app.domains.authentication.models import User
from app.domains.projects.models import Project

router = APIRouter()


@router.get("/daily")
async def get_daily_analytics(
    days: int = Query(30, ge=1, le=365),
    sector: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns daily submission counts scoped to the caller's organization.
    Super Admin callers receive global platform metrics.
    Dialect-agnostic: groups by date in application layer.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = select(Activity.submitted_at).where(Activity.submitted_at >= cutoff)

    if current_user.role != "SUPER_ADMIN":
        stmt = stmt.where(Activity.organization_id == current_user.organization_id)

    if sector:
        stmt = (
            stmt.outerjoin(Asset, Activity.asset_id == Asset.id)
            .outerjoin(Project, Asset.project_id == Project.id)
            .where(Project.sector_id == sector)
        )

    stmt = stmt.order_by(Activity.submitted_at.asc())
    res = await db.execute(stmt)
    timestamps = res.scalars().all()

    counts_by_day = defaultdict(int)
    for ts in timestamps:
        if ts:
            day_str = ts.strftime("%Y-%m-%d")
            counts_by_day[day_str] += 1

    data = [{"date": day, "count": count} for day, count in sorted(counts_by_day.items())]
    return data


@router.get("/trust-distribution")
async def get_trust_distribution(
    sector: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Calculates trust score distribution (High, Medium, Low) scoped to tenant.
    """
    stmt = select(Activity.trust_score).where(Activity.trust_score.isnot(None))

    if current_user.role != "SUPER_ADMIN":
        stmt = stmt.where(Activity.organization_id == current_user.organization_id)

    if sector:
        stmt = (
            stmt.outerjoin(Asset, Activity.asset_id == Asset.id)
            .outerjoin(Project, Asset.project_id == Project.id)
            .where(Project.sector_id == sector)
        )

    res = await db.execute(stmt)
    scores = res.scalars().all()

    high = sum(1 for s in scores if s is not None and s >= 80)
    medium = sum(1 for s in scores if s is not None and 50 <= s < 80)
    low = sum(1 for s in scores if s is not None and s < 50)

    return {
        "high": high,
        "medium": medium,
        "low": low,
        "unscored": 0,
    }


@router.get("/global")
async def get_global_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns platform-wide metrics for Super Admins or organization-scoped metrics for tenant users.
    """
    from app.domains.reporting.services.analytics import AnalyticsService

    analytics_service = AnalyticsService(db)
    if current_user.role == "SUPER_ADMIN":
        return await analytics_service.get_global_analytics()
    return await analytics_service.get_dashboard_metrics(org_id=current_user.organization_id)


@router.get("/agents")
async def get_agent_performance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns field agent performance leaderboard scoped strictly to the caller's organization.
    Super Admins can view all agents across the platform.
    """
    user_stmt = select(User).where(User.role.in_(["field_agent", "agent", "FIELD_AGENT"]))
    if current_user.role != "SUPER_ADMIN":
        user_stmt = user_stmt.where(User.organization_id == current_user.organization_id)

    users_res = await db.execute(user_stmt)
    agents = users_res.scalars().all()

    leaderboard = []
    for agent in agents:
        act_stmt = select(Activity).where(Activity.user_id == agent.id)
        if current_user.role != "SUPER_ADMIN":
            act_stmt = act_stmt.where(Activity.organization_id == current_user.organization_id)
        act_res = await db.execute(act_stmt)
        acts = act_res.scalars().all()

        total = len(acts)
        approved = sum(1 for a in acts if a.status in ("approved", "verified"))
        scores = [a.trust_score for a in acts if a.trust_score is not None]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

        tier = "Gold" if avg_score > 90 else "Silver" if avg_score > 70 else "Bronze"
        badges = ["Top Verifier"] if avg_score > 90 else []

        leaderboard.append(
            {
                "id": str(agent.id),
                "name": agent.full_name or "Unknown Agent",
                "score": avg_score,
                "trend": None,
                "submissions": total,
                "approved": approved,
                "rejections": max(0, total - approved),
                "tier": tier,
                "badges": badges,
                "status": agent.status or "active",
            }
        )

    leaderboard.sort(key=lambda x: x["submissions"], reverse=True)
    return {
        "leaderboard": leaderboard,
        "total_agents": len(leaderboard),
        "avg_agent_score": (sum([a["score"] for a in leaderboard]) / max(len(leaderboard), 1)) if leaderboard else 0.0,
        "active_today": len(leaderboard),
    }
