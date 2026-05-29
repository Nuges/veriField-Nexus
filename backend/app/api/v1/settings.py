from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.db.session import get_db
from app.core.security import require_admin
from app.models.system_setting import SystemSetting
from app.models.user import User

router = APIRouter(prefix="/settings", tags=["settings"])

class SettingsUpdate(BaseModel):
    gps_weight: float
    image_weight: float
    frequency_weight: float
    gps_max_distance_km: float
    max_submissions_per_hour: int
    image_hash_threshold: int
    suspicious_hours_start: int
    suspicious_hours_end: int

@router.get("", summary="Get system settings")
async def get_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SystemSetting).where(SystemSetting.id == 1))
    setting = result.scalar_one_or_none()
    if not setting:
        setting = SystemSetting(
            id=1,
            gps_weight=30.0,
            image_weight=40.0,
            frequency_weight=30.0,
            gps_max_distance_km=5.0,
            max_submissions_per_hour=10,
            image_hash_threshold=12,
            suspicious_hours_start=2,
            suspicious_hours_end=5
        )
        db.add(setting)
        await db.commit()
        await db.refresh(setting)
        
    return {
        "gps_weight": setting.gps_weight,
        "image_weight": setting.image_weight,
        "frequency_weight": setting.frequency_weight,
        "gps_max_distance_km": setting.gps_max_distance_km,
        "max_submissions_per_hour": setting.max_submissions_per_hour,
        "image_hash_threshold": setting.image_hash_threshold,
        "suspicious_hours_start": setting.suspicious_hours_start,
        "suspicious_hours_end": setting.suspicious_hours_end,
    }

@router.patch("", summary="Update system settings")
async def update_settings(
    payload: SettingsUpdate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(SystemSetting).where(SystemSetting.id == 1))
    setting = result.scalar_one_or_none()
    if not setting:
        setting = SystemSetting(id=1)
        db.add(setting)
        
    setting.gps_weight = payload.gps_weight
    setting.image_weight = payload.image_weight
    setting.frequency_weight = payload.frequency_weight
    setting.gps_max_distance_km = payload.gps_max_distance_km
    setting.max_submissions_per_hour = payload.max_submissions_per_hour
    setting.image_hash_threshold = payload.image_hash_threshold
    setting.suspicious_hours_start = payload.suspicious_hours_start
    setting.suspicious_hours_end = payload.suspicious_hours_end
    
    # Normalize weights so they add up to exactly 100
    total = setting.gps_weight + setting.image_weight + setting.frequency_weight
    if total > 0 and total != 100.0:
        setting.gps_weight = round((setting.gps_weight / total) * 100, 1)
        setting.image_weight = round((setting.image_weight / total) * 100, 1)
        setting.frequency_weight = round((setting.frequency_weight / total) * 100, 1)
        
    await db.commit()
    return {"status": "success", "message": "Settings updated successfully"}
