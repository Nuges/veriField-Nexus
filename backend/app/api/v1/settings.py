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

@router.get("", summary="Get system settings")
async def get_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SystemSetting).where(SystemSetting.id == 1))
    setting = result.scalar_one_or_none()
    if not setting:
        setting = SystemSetting(id=1, gps_weight=30.0, image_weight=40.0, frequency_weight=30.0)
        db.add(setting)
        await db.commit()
        await db.refresh(setting)
        
    return {
        "gps_weight": setting.gps_weight,
        "image_weight": setting.image_weight,
        "frequency_weight": setting.frequency_weight,
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
    
    # Normalize weights so they add up to exactly 100
    total = setting.gps_weight + setting.image_weight + setting.frequency_weight
    if total > 0 and total != 100.0:
        setting.gps_weight = round((setting.gps_weight / total) * 100, 1)
        setting.image_weight = round((setting.image_weight / total) * 100, 1)
        setting.frequency_weight = round((setting.frequency_weight / total) * 100, 1)
        
    await db.commit()
    return {"status": "success", "message": "Settings updated successfully"}
