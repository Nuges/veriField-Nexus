"""
=============================================================================
VeriField Nexus — Properties API Routes
=============================================================================
CRUD operations for the Real Estate Sustainability module.
Manages properties and their associated sustainability metrics.
=============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from uuid import UUID

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.property import Property
from app.models.activity import Activity
from app.schemas.property import (
    PropertyCreate, PropertyUpdate,
    PropertyResponse, PropertyListResponse, PropertyDetailResponse,
)
from app.schemas.activity import ActivityResponse

router = APIRouter(prefix="/properties", tags=["Properties"])


# =============================================================================
# POST /api/v1/properties — Create a new property
# =============================================================================
@router.post(
    "",
    response_model=PropertyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new property",
)
async def create_property(
    payload: PropertyCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new property for sustainability tracking."""
    prop = Property(
        owner_id=user.id,
        name=payload.name,
        address=payload.address,
        property_type=payload.property_type,
        latitude=payload.latitude,
        longitude=payload.longitude,
        sustainability_metrics={},
    )
    db.add(prop)
    await db.commit()
    await db.refresh(prop)
    return PropertyResponse.model_validate(prop)


# =============================================================================
# GET /api/v1/properties — List properties
# =============================================================================
@router.get(
    "",
    response_model=PropertyListResponse,
    summary="List properties",
)
async def list_properties(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List properties. Non-admins only see their own properties."""
    query = select(Property)
    count_query = select(func.count(Property.id))

    if user.role != "admin":
        query = query.where(Property.owner_id == user.id)
        count_query = count_query.where(Property.owner_id == user.id)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    query = query.order_by(Property.created_at.desc()).offset(offset).limit(per_page)
    result = await db.execute(query)
    properties = result.scalars().all()

    return PropertyListResponse(
        properties=[PropertyResponse.model_validate(p) for p in properties],
        total=total, page=page, per_page=per_page,
    )


# =============================================================================
# GET /api/v1/properties/{id} — Get property detail with metrics
# =============================================================================
@router.get(
    "/{property_id}",
    response_model=PropertyDetailResponse,
    summary="Get property detail with sustainability metrics",
)
async def get_property(
    property_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get property details including aggregated sustainability metrics."""
    result = await db.execute(select(Property).where(Property.id == property_id))
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if user.role != "admin" and prop.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get activity stats
    count_result = await db.execute(
        select(func.count(Activity.id)).where(Activity.property_id == property_id)
    )
    total_activities = count_result.scalar() or 0

    avg_result = await db.execute(
        select(func.avg(Activity.trust_score)).where(
            Activity.property_id == property_id,
            Activity.trust_score.isnot(None),
        )
    )
    avg_trust = avg_result.scalar()

    # Activity type breakdown
    breakdown_result = await db.execute(
        select(Activity.activity_type, func.count(Activity.id))
        .where(Activity.property_id == property_id)
        .group_by(Activity.activity_type)
    )
    breakdown = {row[0]: row[1] for row in breakdown_result.all()}

    return PropertyDetailResponse(
        **PropertyResponse.model_validate(prop).model_dump(),
        total_activities=total_activities,
        avg_trust_score=round(avg_trust, 2) if avg_trust else None,
        activity_breakdown=breakdown,
    )


# =============================================================================
# PUT /api/v1/properties/{id} — Update a property
# =============================================================================
@router.put(
    "/{property_id}",
    response_model=PropertyResponse,
    summary="Update a property",
)
async def update_property(
    property_id: UUID,
    payload: PropertyUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update property details."""
    result = await db.execute(select(Property).where(Property.id == property_id))
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if user.role != "admin" and prop.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(prop, field, value)
    await db.commit()
    await db.refresh(prop)
    return PropertyResponse.model_validate(prop)


# =============================================================================
# GET /api/v1/properties/{id}/activities — List property activities
# =============================================================================
@router.get(
    "/{property_id}/activities",
    summary="List activities for a property",
)
async def list_property_activities(
    property_id: UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all activities assigned to a specific property."""
    result = await db.execute(
        select(Activity)
        .where(Activity.property_id == property_id)
        .order_by(Activity.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    activities = result.scalars().all()
    return [ActivityResponse.model_validate(a) for a in activities]
