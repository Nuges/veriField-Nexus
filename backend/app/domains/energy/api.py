from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter()

@router.get("/portfolio")
async def get_energy_portfolio(db: AsyncSession = Depends(get_db)):
    # Calculate energy portfolio metrics from activities
    query = text("""
        SELECT activity_data
        FROM activities
        WHERE status IN ('verified', 'approved')
    """)
    res = await db.execute(query)
    rows = res.mappings().all()
    
    total_sites = 0
    total_generation_kwh = 0.0
    total_diesel_avoided_l = 0.0
    active_inverters = 0
    total_inverters = 0
    
    for r in rows:
        ad = r.activity_data or {}
        # Simple check to see if it's an energy installation
        if ad.get("system_installed") is not None or "solar_capacity_kwp" in ad:
            total_sites += 1
            if ad.get("system_operational") is True and ad.get("tamper_signs") is False:
                cap = float(ad.get("solar_capacity_kwp", ad.get("solar_kwp", 0)))
                sun = float(ad.get("avg_sun_hours", ad.get("sun_hours", 5.0)))
                eff = float(ad.get("system_efficiency", ad.get("efficiency", 0.8)))
                kwh = cap * sun * eff * 365
                total_generation_kwh += kwh
                total_diesel_avoided_l += (kwh / 3.6)
                active_inverters += 1
            total_inverters += 1
            
    return {
        "total_sites": total_sites,
        "total_generation_mwh": total_generation_kwh / 1000.0,
        "total_diesel_avoided_liters": total_diesel_avoided_l,
        "uptime_percentage": (active_inverters / total_inverters * 100) if total_inverters > 0 else 0
    }

@router.get("/activities")
async def get_energy_activities(page: int = 1, per_page: int = 50, status: str = None, db: AsyncSession = Depends(get_db)):
    offset = (page - 1) * per_page
    status_filter = f"AND status = '{status}'" if status else ""
    query = text(f"""
        SELECT id, name, status, activity_data, captured_at
        FROM activities
        WHERE (activity_data ? 'solar_capacity_kwp' OR activity_data ? 'solar_kwp') {status_filter}
        ORDER BY captured_at DESC
        LIMIT :limit OFFSET :offset
    """)
    res = await db.execute(query, {"limit": per_page, "offset": offset})
    rows = [dict(r) for r in res.mappings().all()]
    
    count_query = text(f"""
        SELECT COUNT(*)
        FROM activities
        WHERE (activity_data ? 'solar_capacity_kwp' OR activity_data ? 'solar_kwp') {status_filter}
    """)
    total = (await db.execute(count_query)).scalar() or 0
    
    return {
        "activities": rows,
        "total": total,
        "page": page,
        "per_page": per_page
    }

@router.get("/telemetry/{site_id}")
async def get_site_telemetry(site_id: str, limit: int = 30, db: AsyncSession = Depends(get_db)):
    return {
        "site_id": site_id,
        "telemetry": [],
        "note": "Telemetry TSDB connection pending"
    }
