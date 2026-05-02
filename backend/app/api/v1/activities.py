"""
=============================================================================
VeriField Nexus — Activities API Routes
=============================================================================
CRUD operations for field activity submissions. Supports:
- Single activity submission
- Batch submission (offline sync)
- Filtered listing with pagination
- Trust score retrieval
=============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional
from datetime import datetime
from uuid import UUID

from app.db.session import get_db
from app.core.security import get_current_user, require_admin
from app.models.user import User
from app.models.activity import Activity
from app.models.trust_log import TrustLog
from app.schemas.activity import (
    ActivityCreate, ActivityBatchCreate,
    ActivityResponse, ActivityListResponse, ActivityBatchResponse,
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
    """
    if activity_type == "cooking":
        hours = data.get("duration_hours", 1.0) if data else 1.0
        return {
            "emission_reduction_value_kg": round(2.5 * hours, 2),
            "methodology_reference": "Gold Standard TPDDTEC v3.1"
        }
    elif activity_type == "energy":
        kwh = data.get("energy_kwh", 5.0) if data else 5.0
        return {
            "emission_reduction_value_kg": round(0.8 * kwh, 2),
            "methodology_reference": "CDM AMS-I.A."
        }
    elif activity_type == "farming":
        return {
            "emission_reduction_value_kg": 15.0,
            "methodology_reference": "Verra VM0042"
        }
    return {}


# =============================================================================
# POST /api/v1/activities — Submit a single activity
# =============================================================================
@router.post(
    "",
    response_model=ActivityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new field activity",
)
async def create_activity(
    payload: ActivityCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a new field activity with photo, GPS, and timestamp data.
    Automatically triggers trust score calculation and anomaly detection.
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
    
    # Auto-create asset if no property is linked
    property_id = payload.property_id
    if not property_id:
        from app.models.property import Property
        asset_name = activity_data.get("asset_name", f"New {payload.activity_type.capitalize()} Installation")
        prop = Property(
            owner_id=user.id,
            name=asset_name,
            address="Field Location",
            property_type=payload.activity_type,
            latitude=payload.latitude,
            longitude=payload.longitude,
            sustainability_metrics={}
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
        await detector.analyze_activity(activity)
    except Exception:
        pass  # Don't fail submission if anomaly detection fails

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
            
            # Auto-create asset if no property is linked
            property_id = activity_data.property_id
            if not property_id:
                from app.models.property import Property
                asset_name = a_data.get("asset_name", f"New {activity_data.activity_type.capitalize()} Installation")
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
                await detector.analyze_activity(activity)
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
from pydantic import BaseModel

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
    return ActivityResponse.model_validate(activity)
