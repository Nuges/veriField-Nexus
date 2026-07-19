from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter()

@router.get("")
async def get_settings(db: AsyncSession = Depends(get_db)):
    query = text("SELECT * FROM system_settings LIMIT 1")
    res = await db.execute(query)
    row = res.mappings().first()
    if row:
        return dict(row)
    return {
        "gps_weight": 30,
        "image_weight": 40,
        "frequency_weight": 30,
        "gps_max_distance_km": 5.0,
        "max_submissions_per_hour": 10,
        "image_hash_threshold": 12,
        "suspicious_hours_start": 2,
        "suspicious_hours_end": 5
    }

@router.patch("")
async def update_settings(data: dict, db: AsyncSession = Depends(get_db)):
    # Simple dynamic update
    sets = []
    for k, v in data.items():
        sets.append(f"{k} = :{k}")
    
    if not sets:
        return await get_settings(db)
        
    query = text(f"UPDATE system_settings SET {', '.join(sets)}")
    await db.execute(query, data)
    await db.commit()
    
    return await get_settings(db)
