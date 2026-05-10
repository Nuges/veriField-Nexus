"""
=============================================================================
VeriField Nexus — Sensor Data Processor
=============================================================================
Background job that processes incoming sensor data:
1. Computes usage patterns from recent readings
2. Updates asset sustainability metrics
3. Flags anomalous sensor behavior (dead battery, zero readings)
=============================================================================
"""

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.sensor_reading import SensorReading
from app.models.property import Property

logger = logging.getLogger("verifield.jobs.sensor")


async def process_sensor_data(asset_id: UUID) -> dict:
    """
    Process sensor readings for a specific asset.
    Computes usage patterns and updates asset sustainability metrics.
    
    Args:
        asset_id: UUID of the property/asset to process
        
    Returns:
        dict with computed usage summary
    """
    async with async_session_factory() as db:
        # Get readings from the last 30 days
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        
        result = await db.execute(
            select(SensorReading)
            .where(
                and_(
                    SensorReading.asset_id == asset_id,
                    SensorReading.timestamp >= thirty_days_ago,
                )
            )
            .order_by(SensorReading.timestamp.desc())
        )
        readings = result.scalars().all()

        if not readings:
            logger.debug(f"No recent sensor readings for asset {asset_id}")
            return {"asset_id": str(asset_id), "status": "no_data"}

        # Compute usage statistics
        total_readings = len(readings)
        usage_count = sum(1 for r in readings if r.usage_flag)
        usage_rate = (usage_count / total_readings * 100) if total_readings > 0 else 0

        # Temperature stats
        temps = [r.temperature for r in readings if r.temperature is not None]
        avg_temp = sum(temps) / len(temps) if temps else None
        max_temp = max(temps) if temps else None

        # Fuel weight stats
        fuel_weights = [r.fuel_weight_kg for r in readings if r.fuel_weight_kg is not None]
        total_fuel_kg = sum(fuel_weights)
        avg_fuel_per_reading = total_fuel_kg / len(fuel_weights) if fuel_weights else 0

        # Battery health
        batteries = [r.battery_voltage for r in readings if r.battery_voltage is not None]
        latest_battery = batteries[0] if batteries else None
        battery_status = "good"
        if latest_battery is not None:
            if latest_battery < 3.0:
                battery_status = "low"
            elif latest_battery < 3.3:
                battery_status = "warning"

        # Compute daily usage pattern (how many days out of 30 had usage)
        usage_days = set()
        for r in readings:
            if r.usage_flag:
                usage_days.add(r.timestamp.date())
        active_days = len(usage_days)

        summary = {
            "asset_id": str(asset_id),
            "period_days": 30,
            "total_readings": total_readings,
            "usage_count": usage_count,
            "usage_rate_pct": round(usage_rate, 1),
            "active_days": active_days,
            "avg_temperature": round(avg_temp, 1) if avg_temp else None,
            "max_temperature": round(max_temp, 1) if max_temp else None,
            "total_fuel_kg": round(total_fuel_kg, 2),
            "avg_fuel_per_reading_kg": round(avg_fuel_per_reading, 3),
            "battery_voltage": latest_battery,
            "battery_status": battery_status,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }

        # Update the asset's sustainability metrics
        prop_result = await db.execute(
            select(Property).where(Property.id == asset_id)
        )
        prop = prop_result.scalar_one_or_none()
        if prop:
            metrics = prop.sustainability_metrics or {}
            metrics["sensor_usage_rate"] = summary["usage_rate_pct"]
            metrics["sensor_active_days"] = summary["active_days"]
            metrics["sensor_battery_status"] = summary["battery_status"]
            metrics["sensor_total_fuel_kg"] = summary["total_fuel_kg"]
            metrics["sensor_last_computed"] = summary["computed_at"]
            prop.sustainability_metrics = metrics
            await db.commit()

        logger.info(
            f"Sensor data processed for asset {asset_id}: "
            f"{total_readings} readings, {usage_rate:.1f}% usage rate, "
            f"{active_days} active days"
        )
        return summary
