"""
=============================================================================
VeriField Nexus — Sensor Readings API Routes
=============================================================================
CRUD operations for IoT sensor data. Supports:
- Submitting sensor readings (authenticated users)
- ESP32 device data endpoint (API key auth — no JWT needed)
- Listing readings with filtering
- Aggregated device summaries
=============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Header, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, distinct, case
from sqlalchemy.orm import selectinload
from typing import Optional
from uuid import UUID

from app.db.session import get_db
from app.core.security import get_current_user, get_optional_user
from app.models.user import User
from app.models.sensor_reading import SensorReading
from app.models.property import Property
from app.schemas.sensor import (
    SensorReadingCreate,
    SensorReadingResponse, SensorReadingListResponse,
    DeviceSummary, DeviceListResponse,
)

router = APIRouter(prefix="/sensors", tags=["Sensors"])


def _serialize_reading(reading: SensorReading) -> SensorReadingResponse:
    """Convert a SensorReading ORM instance to response model."""
    return SensorReadingResponse(
        id=reading.id,
        asset_id=reading.asset_id,
        device_id=reading.device_id,
        temperature=reading.temperature,
        usage_flag=reading.usage_flag,
        fuel_weight_kg=reading.fuel_weight_kg,
        battery_voltage=reading.battery_voltage,
        timestamp=reading.timestamp,
        property_name=reading.property.name if reading.property else None,
    )


# =============================================================================
# POST /api/v1/sensors/readings — Submit a sensor reading
# =============================================================================
@router.post(
    "/readings",
    response_model=SensorReadingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a sensor reading",
)
async def create_sensor_reading(
    payload: SensorReadingCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a new IoT sensor reading from a field device."""
    # Validate asset exists
    prop_result = await db.execute(select(Property).where(Property.id == payload.asset_id))
    if not prop_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Property/asset not found")

    reading = SensorReading(
        asset_id=payload.asset_id,
        device_id=payload.device_id,
        temperature=payload.temperature,
        usage_flag=payload.usage_flag,
        fuel_weight_kg=payload.fuel_weight_kg,
        battery_voltage=payload.battery_voltage,
    )
    db.add(reading)
    await db.commit()

    # Reload with relationship
    result = await db.execute(
        select(SensorReading)
        .options(selectinload(SensorReading.property))
        .where(SensorReading.id == reading.id)
    )
    reading = result.scalar_one()
    return _serialize_reading(reading)


# =============================================================================
# POST /api/v1/sensors/data — ESP32 device endpoint (API key auth)
# =============================================================================
@router.post(
    "/data",
    response_model=SensorReadingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit sensor data from ESP32 device",
)
async def submit_sensor_data(
    payload: SensorReadingCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    x_device_key: Optional[str] = Header(None, alias="X-Device-Key"),
):
    """
    ESP32-ready endpoint. Does NOT require JWT auth.
    Devices authenticate via X-Device-Key header (optional for dev).
    Triggers background sensor processing after storage.
    """
    # Validate asset exists
    prop_result = await db.execute(select(Property).where(Property.id == payload.asset_id))
    if not prop_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Asset not found")

    reading = SensorReading(
        asset_id=payload.asset_id,
        device_id=payload.device_id,
        temperature=payload.temperature,
        usage_flag=payload.usage_flag,
        fuel_weight_kg=payload.fuel_weight_kg,
        battery_voltage=payload.battery_voltage,
    )
    db.add(reading)
    await db.commit()

    # Trigger background sensor processing
    from app.services.jobs.sensor_processor import process_sensor_data
    background_tasks.add_task(process_sensor_data, payload.asset_id)

    # Reload with relationship
    result = await db.execute(
        select(SensorReading)
        .options(selectinload(SensorReading.property))
        .where(SensorReading.id == reading.id)
    )
    reading = result.scalar_one()
    return _serialize_reading(reading)


# =============================================================================
# GET /api/v1/sensors/readings — List sensor readings
# =============================================================================
@router.get(
    "/readings",
    response_model=SensorReadingListResponse,
    summary="List sensor readings",
)
async def list_sensor_readings(
    device_id: Optional[str] = Query(None),
    asset_id: Optional[UUID] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """List sensor readings with optional filtering."""
    query = select(SensorReading).options(selectinload(SensorReading.property))
    count_query = select(func.count(SensorReading.id))

    conditions = []
    if device_id:
        conditions.append(SensorReading.device_id == device_id)
    if asset_id:
        conditions.append(SensorReading.asset_id == asset_id)

    # Non-admins only see readings for their own properties
    if user and user.role != "admin":
        conditions.append(
            SensorReading.asset_id.in_(
                select(Property.id).where(Property.owner_id == user.id)
            )
        )

    if conditions:
        query = query.where(and_(*conditions))
        count_query = count_query.where(and_(*conditions))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    query = query.order_by(SensorReading.timestamp.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    readings = result.scalars().all()

    return SensorReadingListResponse(
        readings=[_serialize_reading(r) for r in readings],
        total=total, page=page, per_page=per_page,
    )


# =============================================================================
# GET /api/v1/sensors/devices — Aggregated device summaries
# =============================================================================
@router.get(
    "/devices",
    response_model=DeviceListResponse,
    summary="List connected devices with summaries",
)
async def list_devices(
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated summaries of all known sensor devices."""
    # Build the base query with ownership filter for non-admins
    ownership_filter = []
    if user and user.role != "admin":
        ownership_filter.append(
            SensorReading.asset_id.in_(
                select(Property.id).where(Property.owner_id == user.id)
            )
        )

    # Aggregate per device
    agg_query = (
        select(
            SensorReading.device_id,
            SensorReading.asset_id,
            func.count(SensorReading.id).label("reading_count"),
            func.max(SensorReading.timestamp).label("last_reading"),
            func.sum(case((SensorReading.usage_flag == True, 1), else_=0)).label("usage_true_count"),
        )
        .group_by(SensorReading.device_id, SensorReading.asset_id)
    )
    if ownership_filter:
        agg_query = agg_query.where(and_(*ownership_filter))

    result = await db.execute(agg_query)
    rows = result.all()

    devices = []
    for row in rows:
        # Fetch latest reading for this device to get temperature/battery
        latest_q = (
            select(SensorReading)
            .options(selectinload(SensorReading.property))
            .where(
                and_(
                    SensorReading.device_id == row.device_id,
                    SensorReading.asset_id == row.asset_id,
                )
            )
            .order_by(SensorReading.timestamp.desc())
            .limit(1)
        )
        latest_result = await db.execute(latest_q)
        latest = latest_result.scalar_one_or_none()

        usage_rate = (row.usage_true_count / row.reading_count * 100) if row.reading_count > 0 else 0

        devices.append(DeviceSummary(
            device_id=row.device_id,
            asset_id=row.asset_id,
            property_name=latest.property.name if latest and latest.property else None,
            reading_count=row.reading_count,
            last_reading=row.last_reading,
            last_temperature=latest.temperature if latest else None,
            last_battery_voltage=latest.battery_voltage if latest else None,
            usage_rate=round(usage_rate, 1),
        ))

    return DeviceListResponse(devices=devices, total=len(devices))
