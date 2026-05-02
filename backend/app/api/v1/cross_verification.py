from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.db.session import get_db
from app.core.security import require_admin, get_current_user
from app.models.user import User
from app.models.sensor_reading import SensorReading
from app.models.community_validation import CommunityValidation
from app.models.audit_task import AuditTask
from app.models.property import Property

router = APIRouter(prefix="/verification", tags=["Cross Verification"])

# --- Schemas ---
class SensorReadingCreate(BaseModel):
    asset_id: str
    device_id: str
    temperature: Optional[float] = None
    usage_flag: bool = False

class CommunityValidationCreate(BaseModel):
    asset_id: str
    response: str # 'yes' or 'no'

class AuditTaskCreate(BaseModel):
    asset_id: str
    assigned_agent: str
    deadline: Optional[datetime] = None

class AuditTaskUpdate(BaseModel):
    status: str # 'completed', 'failed'

# =============================================================================
# Sensor Integration
# =============================================================================

@router.post("/sensors/sync", summary="Sync Bluetooth sensor readings")
async def sync_sensor_data(
    readings: List[SensorReadingCreate],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Sync batched sensor readings from the mobile app via Bluetooth."""
    records = []
    for r in readings:
        reading = SensorReading(
            asset_id=r.asset_id,
            device_id=r.device_id,
            temperature=r.temperature,
            usage_flag=r.usage_flag
        )
        db.add(reading)
        records.append(reading)
    
    await db.commit()
    return {"message": f"Successfully synced {len(records)} sensor readings"}

@router.get("/sensors/{asset_id}", summary="Get sensor readings for an asset")
async def get_sensor_readings(
    asset_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(SensorReading)
        .where(SensorReading.asset_id == asset_id)
        .order_by(SensorReading.timestamp.desc())
        .limit(100)
    )
    return result.scalars().all()

# =============================================================================
# Community Validation
# =============================================================================

@router.post("/community/validate", summary="Submit community validation response")
async def submit_community_validation(
    data: CommunityValidationCreate,
    user: User = Depends(get_current_user), # The validator
    db: AsyncSession = Depends(get_db)
):
    """Used by validators (or via SMS webhook) to confirm asset usage."""
    validation = CommunityValidation(
        asset_id=data.asset_id,
        validator_id=user.id,
        response=data.response.lower()
    )
    db.add(validation)
    await db.commit()
    await db.refresh(validation)
    return validation

@router.get("/community/{asset_id}", summary="Get community validations for an asset")
async def get_community_validations(
    asset_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(CommunityValidation)
        .where(CommunityValidation.asset_id == asset_id)
        .order_by(CommunityValidation.timestamp.desc())
    )
    return result.scalars().all()

# =============================================================================
# Random Audit System
# =============================================================================

@router.post("/audits", summary="Create a random audit task")
async def create_audit_task(
    data: AuditTaskCreate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Admin endpoint to randomly assign audits."""
    audit = AuditTask(
        asset_id=data.asset_id,
        assigned_agent=data.assigned_agent,
        deadline=data.deadline
    )
    db.add(audit)
    await db.commit()
    await db.refresh(audit)
    return audit

@router.patch("/audits/{audit_id}", summary="Complete or fail an audit task")
async def update_audit_task(
    audit_id: str,
    data: AuditTaskUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(AuditTask).where(AuditTask.id == audit_id))
    audit = result.scalar_one_or_none()
    
    if not audit:
        raise HTTPException(status_code=404, detail="Audit task not found")
        
    audit.status = data.status
    await db.commit()
    await db.refresh(audit)
    return audit

@router.get("/audits/my-tasks", summary="Get audit tasks assigned to the current agent")
async def get_my_audit_tasks(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(AuditTask)
        .where(AuditTask.assigned_agent == user.id)
        .order_by(AuditTask.created_at.desc())
    )
    return result.scalars().all()
