"""
=============================================================================
VeriField Nexus — Activities API Routes (Smart Installation System)
=============================================================================
CRUD operations for field activity / installation submissions. Supports:
- Single activity submission with GPS duplicate validation
- Batch submission (offline sync)
- Pre-submission duplicate check endpoint
- Filtered listing with pagination
- Activity type schema retrieval for dynamic forms
- Trust score retrieval
=============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks, Request, UploadFile, File
import os
import shutil
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

from app.db.session import get_db
from app.core.security import get_current_user, require_admin
from app.models.user import User
from app.models.activity import Activity
from app.models.trust_log import TrustLog
from app.schemas.activity import (
    ActivityCreate, ActivityBatchCreate,
    ActivityResponse, ActivityListResponse, ActivityBatchResponse,
    ACTIVITY_SCHEMAS,
)
from app.schemas.analytics import TrustScoreResponse

# =============================================================================
# Background SMS Dispatch helper
# =============================================================================

async def dispatch_sms_verification(activity_id: UUID, db_session_factory):
    """
    Asynchronously queries the activity and dispatches a Twilio SMS confirmation
    request to the beneficiary or owner phone number.
    """
    import logging
    logger = logging.getLogger("verifield.jobs.sms_dispatch")
    
    async with db_session_factory() as session:
        # Load activity with user and property relationships
        result = await session.execute(
            select(Activity)
            .options(selectinload(Activity.user), selectinload(Activity.property))
            .where(Activity.id == activity_id)
        )
        act = result.scalar_one_or_none()
        if not act:
            return

        phone = None
        name = "Beneficiary"
        
        # 1. First, check if custom phone number is inside activity_data
        data = act.activity_data or {}
        if data.get("beneficiary_phone"):
            phone = str(data.get("beneficiary_phone")).strip()
            name = data.get("beneficiary_name", "Beneficiary")
        
        # 2. Fall back to property owner/tenant phone number
        elif act.property and act.property.owner_id:
            from app.models.user import User
            owner_res = await session.execute(select(User).where(User.id == act.property.owner_id))
            owner = owner_res.scalar_one_or_none()
            if owner and owner.phone:
                phone = str(owner.phone).strip()
                name = owner.full_name
        
        # 3. Fall back to the agent who logged the activity
        elif act.user and act.user.phone:
            phone = str(act.user.phone).strip()
            name = act.user.full_name
            
        if not phone:
            logger.info(f"No phone number resolved for activity {activity_id}. Skipping SMS.")
            return
            
        # Format outbound SMS with verification code (first 8 characters of property UUID)
        from app.services.sms_service import send_twilio_sms
        code_suffix = f" {str(act.property_id)[:8]}" if act.property_id else ""
        
        body = (
            f"VeriField: Did you receive the {act.activity_type.replace('_', ' ').lower()} installation? "
            f"Reply YES{code_suffix} to verify, or NO{code_suffix} if not."
        )
        
        logger.info(f"Dispatching verification SMS to {name} ({phone}) for activity {activity_id}...")
        await send_twilio_sms(phone, body)


router = APIRouter(prefix="/activities", tags=["Activities"])

async def compute_phash(image_url: str) -> Optional[str]:
    """Download image and compute perceptual hash for similarity detection."""
    if not image_url:
        return None
    try:
        import httpx
        import imagehash
        from PIL import Image
        from io import BytesIO
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(image_url)
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                return str(imagehash.phash(img))
    except Exception as e:
        print(f"Error computing pHash: {e}")
    return None


def activity_to_response(activity: Activity) -> ActivityResponse:
    """Convert Activity ORM model to response, injecting agent_name from user relationship."""
    data = ActivityResponse.model_validate(activity)
    # Inject agent name from the eagerly-loaded user relationship
    if hasattr(activity, 'user') and activity.user is not None:
        data.agent_name = activity.user.full_name
    return data


def calculate_carbon_offset(activity_type: str, data: dict) -> dict:
    """
    Calculate estimated CO2 reduction for activity submissions.
    Supports both cookstove and hybrid energy displacement types.
    """
    activity_type_upper = activity_type.upper()
    
    if activity_type_upper in ("CLEAN_COOKING", "COOKING"):
        household_size = data.get("household_size", 4)
        fuel = data.get("primary_fuel", "wood")
        base_reduction = {"wood": 3.5, "charcoal": 2.8, "pellet": 1.5, "LPG": 0.5}
        return {
            "emission_reduction_value_kg": round(base_reduction.get(fuel, 2.0) * household_size * 0.5, 2),
            "methodology_reference": "Gold Standard TPDDTEC v3.1",
        }
    elif activity_type_upper == "HYBRID_ENERGY":
        # Quick estimate: baseline diesel displacement by solar capacity
        solar_kwp = float(data.get("solar_capacity_kwp", 0.0))
        sun_hours = float(data.get("avg_sun_hours", 5.0))
        efficiency = float(data.get("system_efficiency", 0.80))
        # Annual solar generation displaces grid/diesel at ~0.43 kgCO2/kWh (Nigeria grid factor)
        annual_kwh = solar_kwp * sun_hours * efficiency * 365
        estimated_kg = round(annual_kwh * 0.43, 2)
        return {
            "emission_reduction_value_kg": estimated_kg,
            "methodology_reference": "Verra AMS-I.F / Gold Standard Renewable Energy",
        }
    # Fallback for any legacy data
    return {
        "emission_reduction_value_kg": 0.0,
        "methodology_reference": "Gold Standard TPDDTEC v3.1",
    }


# =============================================================================
# GET /api/v1/activities/schemas — Get form schemas for dynamic forms
# =============================================================================
@router.get(
    "/schemas",
    summary="Get activity type schemas for dynamic forms",
)
async def get_activity_schemas():
    """
    Returns the complete schema definitions for all activity types.
    The mobile app uses this to dynamically render forms.
    """
    return {"schemas": ACTIVITY_SCHEMAS}


# =============================================================================
# POST /api/v1/activities/check-duplicate — Pre-submission GPS check
# =============================================================================
class DuplicateCheckRequest(BaseModel):
    latitude: float
    longitude: float
    activity_type: str

@router.post(
    "/check-duplicate",
    summary="Check for nearby duplicate installations",
)
async def check_duplicate(
    payload: DuplicateCheckRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Pre-submission check: scans for existing installations of the same type
    within the adaptive radius. Returns environment type, radius used, and
    any nearby installations found.
    """
    from app.services.gps_validator import GPSValidator
    validator = GPSValidator(db)
    result = await validator.check_duplicate(
        payload.latitude, payload.longitude, payload.activity_type
    )
    return result


# =============================================================================
# POST /api/v1/activities/upload-proof — Upload installation proof image
# =============================================================================
@router.post(
    "/upload-proof",
    summary="Upload installation proof image",
    description="Uploads a photo proof and returns the hosting static URL.",
)
async def upload_proof(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    # Validate file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPG, JPEG, PNG, GIF, and WEBP images are supported.",
        )
    
    # Create unique filename
    os.makedirs(os.path.join("static", "proofs"), exist_ok=True)
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    target_path = os.path.join("static", "proofs", unique_filename)
    
    # Save the file
    try:
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save uploaded file: {str(e)}",
        )
        
    # Build absolute URL using base_url
    base_url = str(request.base_url).rstrip("/")
    proof_url = f"{base_url}/static/proofs/{unique_filename}"
    
    return {"image_url": proof_url}


# =============================================================================
# POST /api/v1/activities — Submit a single activity
# =============================================================================
@router.post(
    "",
    response_model=ActivityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new field activity / installation",
)
async def create_activity(
    payload: ActivityCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a new field activity with photo, GPS, and timestamp data.
    Automatically triggers GPS duplicate check, trust score calculation,
    and anomaly detection.
    """
    # Check for duplicate client_id (offline sync deduplication)
    if payload.client_id:
        result = await db.execute(
            select(Activity).where(Activity.client_id == payload.client_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            return activity_to_response(existing)
    if payload.activity_type == "HYBRID_ENERGY" and not payload.image_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required Solar PV Installation image proof"
        )

    phash = await compute_phash(payload.image_url)
    
    # Calculate carbon offset
    activity_data = payload.activity_data or {}
    activity_data.update(calculate_carbon_offset(payload.activity_type, activity_data))

    # --- Smart GPS Validation ---
    environment_type = payload.environment_type
    radius_used_m = payload.radius_used_m
    duplicate_flag = payload.duplicate_flag or False
    
    if payload.latitude and payload.longitude and not environment_type:
        # Server-side GPS validation if client didn't pre-check
        try:
            from app.services.gps_validator import GPSValidator
            validator = GPSValidator(db)
            gps_result = await validator.check_duplicate(
                payload.latitude, payload.longitude, payload.activity_type
            )
            environment_type = gps_result["environment_type"]
            radius_used_m = gps_result["radius_used_m"]
            duplicate_flag = gps_result["duplicate_flag"]
        except Exception:
            pass
    
    # Auto-create asset if no property is linked
    property_id = payload.property_id
    if not property_id:
        from app.models.property import Property
        type_label = payload.activity_type.replace("_", " ").title()
        asset_name = activity_data.get("asset_name", f"New {type_label} Installation")
        prop = Property(
            owner_id=user.id,
            name=asset_name,
            address="Field Location",
            property_type=payload.activity_type,
            latitude=payload.latitude,
            longitude=payload.longitude,
            sustainability_metrics={
                "energy_score": activity_data.get("energy_score", "Pending"),
                "carbon_offset_kg": activity_data.get("carbon_offset_kg", "Calculating..."),
                "status": "Awaiting Review"
            }
        )
        db.add(prop)
        await db.flush()
        property_id = prop.id

    # Create the activity record
    activity = Activity(
        user_id=user.id,
        property_id=property_id,
        activity_type=payload.activity_type,
        activity_data=activity_data,
        description=payload.description,
        image_url=payload.image_url,
        image_hash=phash or payload.image_hash,
        latitude=payload.latitude,
        longitude=payload.longitude,
        gps_accuracy=payload.gps_accuracy,
        environment_type=environment_type,
        radius_used_m=radius_used_m,
        duplicate_flag=duplicate_flag,
        override_reason=payload.override_reason,
        captured_at=payload.captured_at,
        client_id=payload.client_id,
    )
    db.add(activity)
    await db.commit()
    await db.refresh(activity)

    # Calculate trust score asynchronously
    try:
        from app.services.trust_engine import TrustEngine
        trust_engine = TrustEngine(db)
        await trust_engine.calculate_trust_score(activity)
    except Exception as e:
        await db.rollback()
        import logging
        logging.getLogger("verifield.api").warning(f"Swallowed trust score calculation error: {e}")

    # Run anomaly detection
    try:
        from app.services.ai_detector import AnomalyDetector
        detector = AnomalyDetector(db)
        anomaly_flags = await detector.analyze_activity(activity)
        if anomaly_flags and activity.status == "verified":
            activity.status = "flagged"
            activity.trust_flags["anomaly_detected"] = True
            await db.commit()
    except Exception as e:
        await db.rollback()
        import logging
        logging.getLogger("verifield.api").warning(f"Swallowed anomaly detection error: {e}")

    # If it passed all automatic checks and is verified, quantify immediately!
    if activity.status == "verified":
        try:
            from app.services.quantification_engine import QuantificationEngine
            quant_engine = QuantificationEngine(db)
            await quant_engine.quantify_activity(activity.id, None)
        except Exception as e:
            import logging
            logging.getLogger("verifield.api").error(f"Auto-quantification failed for {activity.id}: {e}")

        try:
            from app.services.blockchain import anchor_activity_on_chain
            await anchor_activity_on_chain(activity, db)
        except Exception as e:
            import logging
            logging.getLogger("verifield.api").error(f"Auto-blockchain anchoring failed for {activity.id}: {e}")

    # Dispatch SMS verification request to beneficiary
    if activity.activity_type in ("CLEAN_COOKING", "HYBRID_ENERGY"):
        from app.db.session import async_session_factory
        background_tasks.add_task(dispatch_sms_verification, activity.id, async_session_factory)

    await db.refresh(activity)
    return activity_to_response(activity)


# =============================================================================
# POST /api/v1/activities/batch — Batch submit activities (offline sync)
# =============================================================================
@router.post(
    "/batch",
    response_model=ActivityBatchResponse,
    summary="Batch submit activities (offline sync)",
)
async def batch_create_activities(
    payload: ActivityBatchCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit multiple activities at once. Used for offline-first sync
    when the mobile app reconnects to the network.
    Handles deduplication via client_id.
    """
    submitted, duplicates, errors = 0, 0, 0
    results = []

    for activity_data in payload.activities:
        try:
            # Check for duplicate
            if activity_data.client_id:
                result = await db.execute(
                    select(Activity).where(Activity.client_id == activity_data.client_id)
                )
                if result.scalar_one_or_none():
                    duplicates += 1
                    results.append({"client_id": activity_data.client_id, "status": "duplicate"})
                    continue

            if activity_data.activity_type == "HYBRID_ENERGY" and not activity_data.image_url:
                errors += 1
                results.append({
                    "client_id": activity_data.client_id,
                    "status": "error",
                    "error": "Missing required Solar PV Installation image proof"
                })
                continue

            phash = await compute_phash(activity_data.image_url)
            
            # Calculate carbon offset
            a_data = activity_data.activity_data or {}
            a_data.update(calculate_carbon_offset(activity_data.activity_type, a_data))
            
            # GPS validation
            env_type = activity_data.environment_type
            radius = activity_data.radius_used_m
            dup_flag = activity_data.duplicate_flag or False
            
            if activity_data.latitude and activity_data.longitude and not env_type:
                try:
                    from app.services.gps_validator import GPSValidator
                    validator = GPSValidator(db)
                    gps_result = await validator.check_duplicate(
                        activity_data.latitude, activity_data.longitude, activity_data.activity_type
                    )
                    env_type = gps_result["environment_type"]
                    radius = gps_result["radius_used_m"]
                    dup_flag = gps_result["duplicate_flag"]
                except Exception:
                    pass
            
            # Auto-create asset if no property is linked
            property_id = activity_data.property_id
            if not property_id:
                from app.models.property import Property
                type_label = activity_data.activity_type.replace("_", " ").title()
                asset_name = a_data.get("asset_name", f"New {type_label} Installation")
                prop = Property(
                    owner_id=user.id,
                    name=asset_name,
                    address="Field Location",
                    property_type=activity_data.activity_type,
                    latitude=activity_data.latitude,
                    longitude=activity_data.longitude,
                    sustainability_metrics={}
                )
                db.add(prop)
                await db.flush()
                property_id = prop.id
            
            # Create activity
            activity = Activity(
                user_id=user.id,
                property_id=property_id,
                activity_type=activity_data.activity_type,
                activity_data=a_data,
                description=activity_data.description,
                image_url=activity_data.image_url,
                image_hash=phash or activity_data.image_hash,
                latitude=activity_data.latitude,
                longitude=activity_data.longitude,
                gps_accuracy=activity_data.gps_accuracy,
                environment_type=env_type,
                radius_used_m=radius,
                duplicate_flag=dup_flag,
                override_reason=activity_data.override_reason,
                captured_at=activity_data.captured_at,
                client_id=activity_data.client_id,
            )
            db.add(activity)
            await db.flush()

            # Trust score + anomaly detection
            try:
                from app.services.trust_engine import TrustEngine
                from app.services.ai_detector import AnomalyDetector
                engine = TrustEngine(db)
                await engine.calculate_trust_score(activity)
                
                detector = AnomalyDetector(db)
                anomaly_flags = await detector.analyze_activity(activity)
                if anomaly_flags and activity.status == "verified":
                    activity.status = "flagged"
                    activity.trust_flags["anomaly_detected"] = True
                    await db.commit()
                    
                # Quantify if automatically verified
                if activity.status == "verified":
                    try:
                        from app.services.quantification_engine import QuantificationEngine
                        quant_engine = QuantificationEngine(db)
                        await quant_engine.quantify_activity(activity.id, None)
                    except Exception as e:
                        import logging
                        logging.getLogger("verifield.api").error(f"Auto-quantification failed for {activity.id}: {e}")

                    try:
                        from app.services.blockchain import anchor_activity_on_chain
                        await anchor_activity_on_chain(activity, db)
                    except Exception as e:
                        import logging
                        logging.getLogger("verifield.api").error(f"Auto-blockchain anchoring failed for {activity.id}: {e}")
                        
            except Exception as e:
                await db.rollback()
                import logging
                logging.getLogger("verifield.api").warning(f"Swallowed trust/anomaly batch execution error: {e}")

            submitted += 1
            results.append({"client_id": activity_data.client_id, "status": "submitted", "id": str(activity.id)})
            
            # Dispatch SMS verification request to beneficiary for each successfully synced activity
            if activity.activity_type in ("CLEAN_COOKING", "HYBRID_ENERGY"):
                from app.db.session import async_session_factory
                background_tasks.add_task(dispatch_sms_verification, activity.id, async_session_factory)
        except Exception as e:
            errors += 1
            results.append({"client_id": activity_data.client_id, "status": "error", "error": str(e)})

    await db.commit()
    return ActivityBatchResponse(submitted=submitted, duplicates=duplicates, errors=errors, results=results)


# =============================================================================
# GET /api/v1/activities — List activities with filtering
# =============================================================================
@router.get(
    "",
    response_model=ActivityListResponse,
    summary="List activities with filters",
)
async def list_activities(
    activity_type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    user_id: Optional[UUID] = Query(None),
    property_id: Optional[UUID] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    min_trust: Optional[float] = Query(None, ge=0, le=100),
    max_trust: Optional[float] = Query(None, ge=0, le=100),
    duplicate_only: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=1000),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List activities with optional filtering, sorting, and pagination."""
    # Build query with filters joined on user table for secure multi-tenant scoping
    query = select(Activity).join(User, Activity.user_id == User.id).options(selectinload(Activity.user))
    count_query = select(func.count(Activity.id)).join(User, Activity.user_id == User.id)

    conditions = []
    # If the user is a field agent, they only see their own logged activities.
    # If the user is an admin, they only see activities belonging to their organization.
    if user.role != "admin":
        conditions.append(Activity.user_id == user.id)
    else:
        if user.organization:
            conditions.append(User.organization == user.organization)
        if user_id:
            conditions.append(Activity.user_id == user_id)

    if activity_type:
        conditions.append(Activity.activity_type == activity_type)
    if status_filter:
        conditions.append(Activity.status == status_filter)
    if property_id:
        conditions.append(Activity.property_id == property_id)
    if date_from:
        conditions.append(Activity.captured_at >= date_from)
    if date_to:
        conditions.append(Activity.captured_at <= date_to)
    if min_trust is not None:
        conditions.append(Activity.trust_score >= min_trust)
    if max_trust is not None:
        conditions.append(Activity.trust_score <= max_trust)
    if duplicate_only:
        conditions.append(Activity.duplicate_flag == True)

    if conditions:
        query = query.where(and_(*conditions))
        count_query = count_query.where(and_(*conditions))

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination and ordering
    offset = (page - 1) * per_page
    query = query.order_by(Activity.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    activities = result.scalars().all()

    total_pages = max(1, (total + per_page - 1) // per_page)

    return ActivityListResponse(
        activities=[activity_to_response(a) for a in activities],
        total=total, page=page, per_page=per_page, total_pages=total_pages,
    )


# =============================================================================
# GET /api/v1/activities/{id} — Get activity detail
# =============================================================================
@router.get(
    "/{activity_id}",
    response_model=ActivityResponse,
    summary="Get activity detail",
)
async def get_activity(
    activity_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed information about a specific activity."""
    result = await db.execute(select(Activity).options(selectinload(Activity.user)).where(Activity.id == activity_id))
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    if user.role != "admin" and activity.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return activity_to_response(activity)


# =============================================================================
# GET /api/v1/activities/{id}/trust — Get trust score breakdown
# =============================================================================
@router.get(
    "/{activity_id}/trust",
    response_model=TrustScoreResponse,
    summary="Get trust score breakdown",
)
async def get_trust_score(
    activity_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the detailed trust score breakdown for an activity."""
    result = await db.execute(select(TrustLog).where(TrustLog.activity_id == activity_id))
    trust_log = result.scalar_one_or_none()
    if not trust_log:
        raise HTTPException(status_code=404, detail="Trust score not calculated yet")
    return TrustScoreResponse.model_validate(trust_log)


# =============================================================================
# PATCH /api/v1/activities/{id}/status — Update activity status
# =============================================================================

class ActivityStatusUpdate(BaseModel):
    status: str

@router.patch(
    "/{activity_id}/status",
    response_model=ActivityResponse,
    summary="Update activity status",
)
async def update_activity_status(
    activity_id: UUID,
    payload: ActivityStatusUpdate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin endpoint to approve, reject, or flag an activity."""
    result = await db.execute(
        select(Activity)
        .options(selectinload(Activity.user))
        .where(Activity.id == activity_id)
    )
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
        
    activity.status = payload.status
    await db.commit()
    await db.refresh(activity)

    # If an admin manually verifies an activity, we must trigger the
    # Quantification Engine to calculate carbon credits and energy scores,
    # as it bypassed the background worker's automatic quantification.
    if activity.status == "verified":
        try:
            from app.services.quantification_engine import QuantificationEngine
            quant_engine = QuantificationEngine(db)
            await quant_engine.quantify_activity(activity.id, None)
        except Exception as e:
            # We don't want to fail the API request if quantification fails,
            # but we should log it for debugging
            import logging
            logging.getLogger("verifield.api").error(f"Manual quantification failed for {activity.id}: {e}")

        try:
            from app.services.blockchain import anchor_activity_on_chain
            await anchor_activity_on_chain(activity, db)
        except Exception as e:
            import logging
            logging.getLogger("verifield.api").error(f"Manual blockchain anchoring failed for {activity.id}: {e}")

    # Re-fetch with user relationship to ensure response has agent_name
    # (quantification engine may have committed and invalidated the session state)
    result = await db.execute(
        select(Activity)
        .options(selectinload(Activity.user))
        .where(Activity.id == activity_id)
    )
    activity = result.scalar_one_or_none()

    return activity_to_response(activity)
