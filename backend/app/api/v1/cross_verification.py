from fastapi import APIRouter, Depends, HTTPException, Request, Form, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, String
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
from app.models.activity import Activity

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


# =============================================================================
# Twilio SMS Webhook Verification
# =============================================================================

@router.post("/sms/webhook", summary="Twilio SMS validation webhook")
async def sms_webhook(
    request: Request,
    From: str = Form(...),
    Body: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Twilio Webhook: Receives SMS response from beneficiaries to confirm stove
    or energy installations. Automatically adjusts trust scores.
    """
    # 1. Retrieve Twilio signature
    signature = request.headers.get("X-Twilio-Signature", "")
    
    # Extract request URL and body parameters
    form_data = await request.form()
    params = {k: v for k, v in form_data.items()}
    
    # Get request URL as it is configured in Twilio
    proto = request.headers.get("x-forwarded-proto", "http")
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "localhost:8000")
    request_url = f"{proto}://{host}{request.url.path}"
    
    # 2. Validate request signature
    from app.services.sms_service import verify_twilio_signature
    if not verify_twilio_signature(request_url, params, signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
    
    # 3. Parse the body for YES/NO response and optional verification code
    import re
    body_text = Body.strip().lower()
    
    # Check for pattern like "yes abc123de" or just "yes"
    match = re.match(r"^(yes|no)(?:\s+(\w{8}))?", body_text)
    
    response_val = None
    code = None
    if match:
        response_val = match.group(1)
        code = match.group(2)
    else:
        if "yes" in body_text:
            response_val = "yes"
        elif "no" in body_text:
            response_val = "no"
            
    if not response_val:
        xml_content = (
            "<Response>"
            "<Message>Invalid response. Reply YES to confirm installation, or NO if you did not receive it.</Message>"
            "</Response>"
        )
        return Response(content=xml_content, media_type="text/xml")
        
    # 4. Resolve the property/asset
    property_id = None
    
    if code:
        # Match code to the beginning of Property UUID
        prop_query = await db.execute(
            select(Property).where(func.cast(Property.id, String).like(f"{code}%"))
        )
        prop = prop_query.scalar_one_or_none()
        if prop:
            property_id = prop.id
            
    if not property_id:
        # Match user by phone number
        norm_phone = From.strip()
        user_query = await db.execute(
            select(User).where(
                (User.phone == norm_phone) |
                (User.phone.like(f"%{norm_phone[-10:]}"))
            ).order_by(User.created_at.desc())
        )
        user = user_query.scalar_one_or_none()
        
        if user:
            # Get the user's most recently updated property/asset
            prop_query = await db.execute(
                select(Property)
                .where(Property.owner_id == user.id)
                .order_by(Property.updated_at.desc())
                .limit(1)
            )
            prop = prop_query.scalar_one_or_none()
            if prop:
                property_id = prop.id
                
    if not property_id:
        xml_content = (
            "<Response>"
            "<Message>Could not locate your asset profile. Please contact support.</Message>"
            "</Response>"
        )
        return Response(content=xml_content, media_type="text/xml")

    # 5. Determine Validator User ID
    prop_query = await db.execute(select(Property).where(Property.id == property_id))
    property_obj = prop_query.scalar_one()
    
    validator_id = property_obj.owner_id
    user_query = await db.execute(select(User).where(User.phone == From.strip()))
    user_obj = user_query.scalar_one_or_none()
    if user_obj:
        validator_id = user_obj.id

    # 6. Check for duplicate validation in last 24 hours to prevent storms/replays
    from datetime import timedelta, timezone
    limit_time = datetime.now(timezone.utc) - timedelta(hours=24)
    existing_query = await db.execute(
        select(CommunityValidation).where(
            and_(
                CommunityValidation.asset_id == property_id,
                CommunityValidation.validator_id == validator_id,
                CommunityValidation.timestamp >= limit_time
            )
        )
    )
    existing = existing_query.scalar_one_or_none()
    
    if existing:
        existing.response = response_val
        existing.timestamp = datetime.now(timezone.utc)
        validation = existing
    else:
        validation = CommunityValidation(
            asset_id=property_id,
            validator_id=validator_id,
            response=response_val,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(validation)
        
    await db.commit()

    # 7. Recalculate related activity trust scores (+5 for YES, -10 for NO)
    bonus = 5.0 if response_val == "yes" else (-10.0 if response_val == "no" else 0.0)
    
    act_result = await db.execute(
        select(Activity).where(
            and_(
                Activity.property_id == property_id,
                Activity.status.in_(["pending", "review", "verified"]),
            )
        )
    )
    related_activities = act_result.scalars().all()

    for act in related_activities:
        if act.trust_score is not None:
            new_score = max(0.0, min(100.0, act.trust_score + bonus))
            act.trust_score = new_score
            
            # Re-evaluate status
            if new_score >= 80:
                act.status = "verified"
            elif new_score >= 50:
                act.status = "review"
            else:
                act.status = "flagged"
            
            flags = act.trust_flags or {}
            flags[f"sms_community_{response_val}"] = True
            flags["sms_bonus_applied"] = bonus
            act.trust_flags = flags

    if related_activities:
        await db.commit()

    # 8. Return TwiML XML Response acknowledging validation
    response_msg = (
        "Your stove installation has been verified successfully. Thank you!"
        if response_val == "yes" else
        "Your report has been logged. We will audit this installation shortly."
    )
    xml_content = (
        "<Response>"
        f"<Message>{response_msg}</Message>"
        "</Response>"
    )
    return Response(content=xml_content, media_type="text/xml")
