from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter()

@router.get("/daily")
async def get_daily_analytics(days: int = 30, sector: str = None, db: AsyncSession = Depends(get_db)):
    # Simple query for daily submissions count based on activities
    query = text("""
        SELECT date_trunc('day', timestamp) as date, count(*) as count
        FROM activities
        WHERE timestamp > now() - interval '30 days'
        GROUP BY 1
        ORDER BY 1 ASC
    """)
    res = await db.execute(query)
    data = [{"date": r.date.isoformat(), "count": r.count} for r in res.mappings().all()]
    return data

@router.get("/trust-distribution")
async def get_trust_distribution(sector: str = None, db: AsyncSession = Depends(get_db)):
    # Calculate trust distribution from activities
    query = text("""
        SELECT trust_score
        FROM activities
        WHERE trust_score IS NOT NULL
    """)
    res = await db.execute(query)
    
    high = 0
    medium = 0
    low = 0
    
    for row in res.mappings().all():
        score = row.trust_score
        if score >= 80:
            high += 1
        elif score >= 50:
            medium += 1
        else:
            low += 1
            
    return {
        "high": high,
        "medium": medium,
        "low": low,
        "unscored": 0
    }


@router.get("/global")
async def get_global_analytics(db: AsyncSession = Depends(get_db)):
    from app.domains.reporting.services.analytics import AnalyticsService
    analytics_service = AnalyticsService(db)
    return await analytics_service.get_global_analytics()

@router.get("/agents")
async def get_agent_performance(db: AsyncSession = Depends(get_db)):
    # Get top agents based on activity count
    query = text("""
        SELECT 
            u.id, 
            u.full_name as name, 
            COUNT(a.id) as total_submissions,
            AVG(a.trust_score) as avg_trust_score,
            SUM(CASE WHEN a.status = 'approved' THEN 1 ELSE 0 END) as approved_submissions
        FROM users u
        LEFT JOIN activities a ON u.id = a.agent_id
        WHERE u.role = 'field_agent' OR u.role = 'agent'
        GROUP BY u.id, u.full_name
        ORDER BY total_submissions DESC
    """)
    res = await db.execute(query)
    
    leaderboard = []
    for r in res.all():
        leaderboard.append({
            "id": str(r[0]),
            "name": r[1] or "Unknown Agent",
            "score": round(r[3] or 0, 1),
            "trend": "+0%", # Placeholder for trend as it requires complex temporal query
            "submissions": r[2],
            "approved": r[4] or 0,
            "rejections": r[2] - (r[4] or 0),
            "tier": "Gold" if (r[3] or 0) > 90 else "Silver" if (r[3] or 0) > 70 else "Bronze",
            "badges": ["Top Verifier"] if (r[3] or 0) > 90 else [],
            "status": "active"
        })
        
    return {
        "leaderboard": leaderboard,
        "total_agents": len(leaderboard),
        "avg_agent_score": sum([a["score"] for a in leaderboard]) / max(len(leaderboard), 1),
        "active_today": len(leaderboard) # Simplified
    }
