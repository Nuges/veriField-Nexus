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

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
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


def calculate_carbon_offset(activity_type: str, data: dict) -> dict:
    """
    Calculate estimated CO2 reduction based on activity type.
    Updated for the Smart Installation System activity types.
    """
    activity_type_upper = activity_type.upper()
    
    if activity_type_upper == "CLEAN_COOKING":
        household_size = data.get("household_size", 4)
        fuel = data.get("primary_fuel", "wood")
        base_reduction = {"wood": 3.5, "charcoal": 2.8, "pellet": 1.5, "LPG": 0.5}
        return {
            "emission_reduction_value_kg": round(base_reduction.get(fuel, 2.0) * household_size * 0.5, 2),
            "methodology_reference": "Gold Standard TPDDTEC v3.1",
        }
    elif activity_type_upper == "AGRICULTURE":
        hectares = data.get("plot_area_hectares", 1.0)
        return {
            "emission_reduction_value_kg": round(15.0 * hectares, 2),
            "methodology_reference": "Verra VM0042",
        }
    elif activity_type_upper == "ENERGY_USE":
        kwh = data.get("daily_output_kwh", data.get("capacity_kw", 5.0))
        return {
            "emission_reduction_value_kg": round(0.8 * kwh, 2),
            "methodology_reference": "CDM AMS-I.A.",
        }
    elif activity_type_upper == "FORESTRY_LAND_USE":
        trees = data.get("tree_count", 10)
        return {
            "emission_reduction_value_kg": round(22.0 * trees / 100, 2),
            "methodology_reference": "Verra VM0047 ARR",
        }
    elif activity_type_upper == "SAFE_WATER":
        liters = data.get("daily_volume_liters", 500)
        return {
            "emission_reduction_value_kg": round(liters * 0.003, 2),
            "methodology_reference": "Gold Standard Safe Water",
        }
    elif activity_type_upper == "TRANSPORT_MOBILITY":
        # AMS-III.C: Use odometer data for distance
        odo_start = data.get("odometer_start", 0)
        odo_end = data.get("odometer_end", 0)
        distance_km = max(0, odo_end - odo_start)
        energy_type = data.get("energy_type", "EV")
        vehicle_type = data.get("vehicle_type", "car_taxi")
        # Per-vehicle baseline EFs
        baseline_efs = {"motorcycle_okada": 0.08, "tricycle_keke": 0.12, "car_taxi": 0.21, "minibus_danfo": 0.35, "bus": 0.65, "light_truck": 0.45, "heavy_truck": 0.90, "forklift": 4.0}
        project_efs = {"EV": 0.03, "hybrid": 0.12, "CNG": 0.14, "LPG": 0.16, "diesel_retrofit": 0.18}
        base = baseline_efs.get(vehicle_type, 0.21)
        proj = project_efs.get(energy_type, 0.12)
        reduction_kg = round(distance_km * (base - proj), 2)
        return {
            "emission_reduction_value_kg": reduction_kg,
            "methodology_reference": "CDM AMS-III.C.",
        }
    # Legacy fallback for old activity types
    elif activity_type_upper in ("COOKING",):
        hours = data.get("duration_hours", 1.0)
        return {"emission_reduction_value_kg": round(2.5 * hours, 2), "methodology_reference": "Gold Standard TPDDTEC v3.1"}
    elif activity_type_upper in ("ENERGY",):
        kwh = data.get("energy_kwh", 5.0)
        return {"emission_reduction_value_kg": round(0.8 * kwh, 2), "methodology_reference": "CDM AMS-I.A."}
    elif activity_type_upper in ("FARMING",):
        return {"emission_reduction_value_kg": 15.0, "methodology_reference": "Verra VM0042"}
    return {}


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
            return ActivityResponse.model_validate(existing)

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
    except Exception:
        pass  # Don't fail submission if trust scoring fails

    # Run anomaly detection
    try:
        from app.services.ai_detector import AnomalyDetector
        detector = AnomalyDetector(db)
        anomaly_flags = await detector.analyze_activity(activity)
        if anomaly_flags and activity.status == "verified":
            activity.status = "flagged"
            activity.trust_flags["anomaly_detected"] = True
            await db.commit()
    except Exception:
        pass  # Don't fail submission if anomaly detection fails

    # If it passed all automatic checks and is verified, quantify immediately!
    if activity.status == "verified":
        try:
            from app.services.quantification_engine import QuantificationEngine
            quant_engine = QuantificationEngine(db)
            await quant_engine.quantify_activity(activity.id, None)
        except Exception as e:
            import logging
            logging.getLogger("verifield.api").error(f"Auto-quantification failed for {activity.id}: {e}")

    await db.refresh(activity)
    return ActivityResponse.model_validate(activity)


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
                        
            except Exception:
                pass

            submitted += 1
            results.append({"client_id": activity_data.client_id, "status": "submitted", "id": str(activity.id)})
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
    # Build query with filters
    query = select(Activity)
    count_query = select(func.count(Activity.id))

    conditions = []
    # Non-admins can only see their own activities
    if user.role != "admin":
        conditions.append(Activity.user_id == user.id)
    elif user_id:
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
        activities=[ActivityResponse.model_validate(a) for a in activities],
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
    result = await db.execute(select(Activity).where(Activity.id == activity_id))
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    if user.role != "admin" and activity.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return ActivityResponse.model_validate(activity)


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
    result = await db.execute(select(Activity).where(Activity.id == activity_id))
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

    return ActivityResponse.model_validate(activity)
