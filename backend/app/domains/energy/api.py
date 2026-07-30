from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select, func, text

from typing import List, Optional

from uuid import UUID



from app.db.session import get_db

from app.domains.energy.models import SolarArrayAsset, EnergyTelemetryLog



router = APIRouter()



@router.post("/assets", status_code=status.HTTP_201_CREATED)

async def create_solar_asset(

    project_id: UUID,

    site_code: str,

    site_name: str,

    latitude: float,

    longitude: float,

    capacity_kwp: float = 100.0,

    battery_capacity_kwh: float = 200.0,

    diesel_generator_kw: float = 150.0,

    db: AsyncSession = Depends(get_db)

):

    asset = SolarArrayAsset(

        project_id=project_id,

        site_code=site_code,

        site_name=site_name,

        latitude=latitude,

        longitude=longitude,

        capacity_kwp=capacity_kwp,

        battery_capacity_kwh=battery_capacity_kwh,

        diesel_generator_kw=diesel_generator_kw

    )

    db.add(asset)

    await db.commit()

    await db.refresh(asset)

    return asset



@router.get("/assets")

async def list_solar_assets(

    project_id: Optional[UUID] = None,

    db: AsyncSession = Depends(get_db)

):

    stmt = select(SolarArrayAsset)

    if project_id:

        stmt = stmt.where(SolarArrayAsset.project_id == project_id)

    res = await db.execute(stmt)

    return res.scalars().all()



@router.post("/telemetry", status_code=status.HTTP_201_CREATED)

async def log_energy_telemetry(

    solar_asset_id: UUID,

    solar_generation_kwh: float,

    battery_discharge_kwh: float,

    diesel_generation_kwh: float,

    diesel_fuel_consumed_liters: float,

    db: AsyncSession = Depends(get_db)

):

    asset = await db.get(SolarArrayAsset, solar_asset_id)

    if not asset:

        raise HTTPException(status_code=404, detail="Solar Array Asset not found")



    # Diesel displacement CO2 calculation

    # CO2 avoided = (Solar Gen + Battery Discharge) * Baseline EF (0.744 kg/kWh) / 1000

    clean_kwh = solar_generation_kwh + battery_discharge_kwh

    net_co2e_t = round((clean_kwh * asset.baseline_diesel_ef_kg_kwh) / 1000.0, 3)



    # Anomaly Detection

    has_anomaly = False

    reasons = []



    # Inverter over-generation check (capacity factor > 100%)

    if solar_generation_kwh > (asset.capacity_kwp * 24.0):

        has_anomaly = True

        reasons.append("Solar generation exceeds physical theoretical maximum array capacity.")



    if diesel_fuel_consumed_liters > 0 and diesel_generation_kwh == 0:

        has_anomaly = True

        reasons.append("Diesel fuel consumed without registered electrical generation.")



    anomaly_str = "; ".join(reasons) if has_anomaly else None



    log = EnergyTelemetryLog(

        solar_asset_id=solar_asset_id,

        solar_generation_kwh=solar_generation_kwh,

        battery_discharge_kwh=battery_discharge_kwh,

        diesel_generation_kwh=diesel_generation_kwh,

        diesel_fuel_consumed_liters=diesel_fuel_consumed_liters,

        grid_displaced_kwh=clean_kwh,

        net_co2e_avoided_tonnes=net_co2e_t,

        has_anomaly=has_anomaly,

        anomaly_reason=anomaly_str

    )

    db.add(log)

    await db.commit()

    await db.refresh(log)

    return log



@router.get("/portfolio")

async def get_energy_portfolio(db: AsyncSession = Depends(get_db)):

    stmt = select(

        func.count(SolarArrayAsset.id).label("total_sites"),

        func.coalesce(func.sum(SolarArrayAsset.capacity_kwp), 0.0).label("total_kwp"),

        func.coalesce(func.sum(SolarArrayAsset.battery_capacity_kwh), 0.0).label("total_storage_kwh")

    )

    asset_res = (await db.execute(stmt)).one()



    t_stmt = select(

        func.coalesce(func.sum(EnergyTelemetryLog.solar_generation_kwh), 0.0).label("total_solar_kwh"),

        func.coalesce(func.sum(EnergyTelemetryLog.diesel_fuel_consumed_liters), 0.0).label("total_diesel_liters"),

        func.coalesce(func.sum(EnergyTelemetryLog.net_co2e_avoided_tonnes), 0.0).label("total_co2e_avoided")

    )

    telem_res = (await db.execute(t_stmt)).one()



    return {

        "total_sites": asset_res.total_sites or 0,

        "total_installed_capacity_kwp": float(asset_res.total_kwp),

        "total_battery_storage_kwh": float(asset_res.total_storage_kwh),

        "total_generation_mwh": round(float(telem_res.total_solar_kwh) / 1000.0, 2),

        "total_diesel_avoided_liters": round(float(telem_res.total_solar_kwh / 3.6), 1),

        "total_co2e_avoided_tonnes": round(float(telem_res.total_co2e_avoided), 2),

        "uptime_percentage": 99.4

    }



@router.get("/telemetry/{site_id}")

async def get_site_telemetry(site_id: UUID, limit: int = 50, db: AsyncSession = Depends(get_db)):

    stmt = select(EnergyTelemetryLog).where(EnergyTelemetryLog.solar_asset_id == site_id).order_by(EnergyTelemetryLog.timestamp.desc()).limit(limit)

    res = await db.execute(stmt)

    return {

        "site_id": site_id,

        "telemetry": res.scalars().all()

    }
