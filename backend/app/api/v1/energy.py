"""
=============================================================================
VeriField Nexus — Energy Displacement API Routes
=============================================================================
REST endpoints for hybrid energy displacement MRV operations:
  - Inverter telemetry ingestion (smart meter API-first data)
  - Portfolio-level aggregation metrics
  - Energy project listing

Completely separate from cookstove activity routes.
All endpoints require admin authentication.
=============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from uuid import UUID
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.core.security import get_current_user, require_admin
from app.models.user import User
from app.models.activity import Activity
from app.models.carbon_calculation import CarbonCalculation
from app.services.energy_displacement_engine import EnergyDisplacementEngine

router = APIRouter(prefix="/energy", tags=["Energy Displacement MRV"])


# =============================================================================
# Pydantic Request/Response Models
# =============================================================================

class InverterTelemetryPayload(BaseModel):
    """
    Telemetry payload from smart inverters (API-first ingestion).
    Typically sent daily by the inverter's cloud platform or gateway.
    """
    site_id: str = Field(..., description="Unique site identifier matching the activity")
    inverter_serial: str = Field(..., description="Inverter hardware serial number")
    date: str = Field(..., description="Telemetry date (YYYY-MM-DD)")
    solar_kwh_generated: float = Field(..., ge=0, description="Solar energy generated (kWh)")
    grid_kwh_consumed: float = Field(0.0, ge=0, description="Grid energy consumed (kWh)")
    diesel_runtime_hrs: float = Field(0.0, ge=0, description="Diesel backup runtime (hrs)")
    gas_runtime_hrs: float = Field(0.0, ge=0, description="Gas generator runtime (hrs)")
    battery_soc_avg: Optional[float] = Field(None, ge=0, le=100, description="Average battery SOC (%)")
    system_uptime_pct: Optional[float] = Field(None, ge=0, le=100, description="System uptime (%)")
    fault_codes: Optional[List[str]] = Field(None, description="Active fault codes")
    ambient_temp_c: Optional[float] = Field(None, description="Ambient temperature (°C)")


class PortfolioResponse(BaseModel):
    """Portfolio-level aggregation for the Energy Displacement methodology."""
    total_tco2e_reduced: float
    total_calculations: int
    estimated_value_usd: float
    credit_price_per_tco2e: float
    methodology: str
    total_projects: int = 0
    total_energy_mwh: float = 0.0


# =============================================================================
# POST /api/v1/energy/inverter/telemetry — Ingest Inverter Telemetry
# =============================================================================

@router.post(
    "/inverter/telemetry",
    status_code=status.HTTP_201_CREATED,
    summary="Ingest smart inverter telemetry data",
)
async def ingest_inverter_telemetry(
    payload: InverterTelemetryPayload,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """
    Receive daily telemetry from smart inverters (API-first data ingestion).

    This data is stored as a sensor reading linked to the matching site's
    property record and appended to the activity telemetry log.
    It feeds directly into the trust scoring and emission calculation pipelines.

    Returns the ingested telemetry record summary.
    """
    # Find the matching activity by site_id in activity_data
    result = await db.execute(
        select(Activity).where(
            Activity.activity_type == "HYBRID_ENERGY",
        ).order_by(Activity.created_at.desc())
    )
    activities = result.scalars().all()

    # Search for matching site_id in activity_data JSONB
    matched_activity = None
    for act in activities:
        act_data = act.activity_data or {}
        if act_data.get("site_id") == payload.site_id:
            matched_activity = act
            break

    if not matched_activity:
        raise HTTPException(
            status_code=404,
            detail=f"No HYBRID_ENERGY activity found with site_id='{payload.site_id}'",
        )

    # Store telemetry in existing SensorReading model (repurposing fields):
    #   device_id = inverter_serial
    #   temperature = solar_kwh_generated (repurposed for energy readings)
    #   usage_flag = system online status
    #   fuel_weight_kg = diesel_runtime_hrs (repurposed for backup tracking)
    #   battery_voltage = battery_soc_avg (repurposed for battery state)
    if matched_activity.property_id:
        from app.models.sensor_reading import SensorReading
        reading = SensorReading(
            asset_id=matched_activity.property_id,
            device_id=f"inverter_{payload.inverter_serial}",
            temperature=payload.solar_kwh_generated,      # Solar kWh stored here
            usage_flag=(payload.system_uptime_pct or 100) > 50,
            fuel_weight_kg=payload.diesel_runtime_hrs,     # Diesel backup runtime
            battery_voltage=payload.battery_soc_avg,       # Battery SOC
        )
        db.add(reading)

    # Append telemetry entry to activity_data telemetry log
    act_data = matched_activity.activity_data or {}
    telemetry_log = act_data.get("telemetry_log", [])
    telemetry_log.append({
        "date": payload.date,
        "solar_kwh": payload.solar_kwh_generated,
        "grid_kwh": payload.grid_kwh_consumed,
        "diesel_hrs": payload.diesel_runtime_hrs,
        "gas_hrs": payload.gas_runtime_hrs,
        "battery_soc": payload.battery_soc_avg,
        "uptime_pct": payload.system_uptime_pct,
        "faults": payload.fault_codes,
        "temp_c": payload.ambient_temp_c,
    })
    # Keep only last 365 entries to prevent unbounded growth
    act_data["telemetry_log"] = telemetry_log[-365:]
    matched_activity.activity_data = act_data

    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(matched_activity, "activity_data")

    await db.commit()

    return {
        "status": "ingested",
        "site_id": payload.site_id,
        "date": payload.date,
        "solar_kwh": payload.solar_kwh_generated,
        "activity_id": str(matched_activity.id),
    }


# =============================================================================
# GET /api/v1/energy/portfolio — Portfolio Aggregation
# =============================================================================

@router.get(
    "/portfolio",
    summary="Get energy displacement portfolio metrics",
)
async def get_portfolio(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """
    Returns aggregated portfolio-level metrics for all energy displacement
    projects: total CO2 reduced, total energy generation, project count,
    and estimated portfolio value.
    """
    engine = EnergyDisplacementEngine(db)
    metrics = await engine.get_portfolio_metrics()

    # Count distinct projects
    proj_result = await db.execute(
        select(func.count()).select_from(
            select(CarbonCalculation.project_id)
            .where(CarbonCalculation.methodology_used == "ENERGY_DISPLACEMENT")
            .distinct()
            .subquery()
        )
    )
    metrics["total_projects"] = proj_result.scalar() or 0

    # Aggregate total energy generation from activities
    act_result = await db.execute(
        select(Activity).where(Activity.activity_type == "HYBRID_ENERGY")
    )
    activities = act_result.scalars().all()

    total_mwh = 0.0
    for act in activities:
        act_data = act.activity_data or {}
        solar_kwp = float(act_data.get("solar_capacity_kwp", 0.0))
        sun_hours = float(act_data.get("avg_sun_hours", 5.0))
        efficiency = float(act_data.get("system_efficiency", 0.80))
        annual_kwh = solar_kwp * sun_hours * efficiency * 365.0
        total_mwh += annual_kwh / 1000.0

    metrics["total_energy_mwh"] = round(total_mwh, 3)

    return metrics


# =============================================================================
# GET /api/v1/energy/activities — List Energy Displacement Activities
# =============================================================================

@router.get(
    "/activities",
    summary="List hybrid energy displacement activities",
)
async def list_energy_activities(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """
    List all HYBRID_ENERGY activities with pagination and optional
    status filtering. Returns activity data, trust scores, and
    associated carbon calculations.
    """
    query = (
        select(Activity)
        .where(Activity.activity_type == "HYBRID_ENERGY")
    )

    if status_filter:
        query = query.where(Activity.status == status_filter)

    # Count total
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar() or 0

    # Paginate
    query = (
        query.order_by(Activity.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(query)
    activities = result.scalars().all()

    return {
        "activities": [
            {
                "id": str(a.id),
                "user_id": str(a.user_id),
                "activity_type": a.activity_type,
                "activity_data": a.activity_data,
                "status": a.status,
                "trust_score": a.trust_score,
                "latitude": a.latitude,
                "longitude": a.longitude,
                "captured_at": a.captured_at.isoformat() if a.captured_at else None,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "image_url": a.image_url,
            }
            for a in activities
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, -(-total // per_page)),
    }


# =============================================================================
# GET /api/v1/energy/telemetry/{site_id} — Get Telemetry for a Site
# =============================================================================

@router.get(
    "/telemetry/{site_id}",
    summary="Get telemetry readings for a site",
)
async def get_site_telemetry(
    site_id: str,
    limit: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """
    Retrieve recent telemetry readings for a specific site.
    Used by the dashboard to render real-time monitoring charts.
    """
    # Find matching activity
    result = await db.execute(
        select(Activity).where(Activity.activity_type == "HYBRID_ENERGY")
    )
    activities = result.scalars().all()

    matched_activity = None
    for act in activities:
        act_data = act.activity_data or {}
        if act_data.get("site_id") == site_id or str(act.id) == site_id:
            matched_activity = act
            break

    if not matched_activity:
        return {
            "message": "No telemetry data available",
            "status": "empty"
        }

    # Read telemetry from activity_data JSONB telemetry_log
    act_data = matched_activity.activity_data or {}
    telemetry_log = act_data.get("telemetry_log", [])

    if not telemetry_log:
        return {
            "message": "No telemetry data available",
            "status": "empty"
        }

    # Return the most recent entries (up to limit)
    recent_entries = telemetry_log[-limit:]
    recent_entries.reverse()  # Most recent first

    # Populate arrays for specific telemetry validation requirements
    daily_generation_kwh = [entry.get("solar_kwh", 0.0) for entry in recent_entries]
    battery_soc = [entry.get("battery_soc") for entry in recent_entries if entry.get("battery_soc") is not None]
    uptime = [entry.get("uptime_pct") for entry in recent_entries if entry.get("uptime_pct") is not None]
    diesel_runtime_hours = [entry.get("diesel_hrs", 0.0) for entry in recent_entries]

    return {
        "site_id": site_id,
        "activity_id": str(matched_activity.id),
        "readings": recent_entries,
        "total_readings": len(telemetry_log),
        "daily_generation_kwh": daily_generation_kwh,
        "battery_soc": battery_soc,
        "uptime": uptime,
        "diesel_runtime_hours": diesel_runtime_hours
    }
