from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from app.core.security import get_current_user
from app.domains.authentication.models import User

router = APIRouter()

@router.get("")
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
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
        "suspicious_hours_end": 5,
    }

@router.patch("")
async def update_settings(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in ["SUPER_ADMIN", "ADMIN", "ORG_ADMIN", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only administrators can update system settings."
        )

    sets = []
    for k, v in data.items():
        sets.append(f"{k} = :{k}")

    if not sets:
        return await get_settings(current_user=current_user, db=db)

    query = text(f"UPDATE system_settings SET {', '.join(sets)}")
    await db.execute(query, data)
    await db.commit()

    return await get_settings(current_user=current_user, db=db)
