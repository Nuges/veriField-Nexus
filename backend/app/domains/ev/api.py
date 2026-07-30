from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select, func

from typing import List, Optional

from uuid import UUID



from app.db.session import get_db

from app.domains.ev.models import EVChargingStation, EVChargingSession

from app.domains.ev.schemas import EVChargingStationCreate, EVChargingSessionCreate, EVChargingSessionResponse, EVSummaryResponse

from app.domains.ev.service import EVQuantificationEngine



router = APIRouter()



@router.post("/stations", status_code=status.HTTP_201_CREATED)

async def create_charging_station(

    data: EVChargingStationCreate,

    db: AsyncSession = Depends(get_db)

):

    station = EVChargingStation(**data.model_dump())

    db.add(station)

    await db.commit()

    await db.refresh(station)

    return station



@router.get("/stations")

async def list_charging_stations(

    project_id: Optional[UUID] = None,

    db: AsyncSession = Depends(get_db)

):

    stmt = select(EVChargingStation)

    if project_id:

        stmt = stmt.where(EVChargingStation.project_id == project_id)

    res = await db.execute(stmt)

    return res.scalars().all()



@router.post("/sessions", response_model=EVChargingSessionResponse, status_code=status.HTTP_201_CREATED)

async def record_charging_session(

    data: EVChargingSessionCreate,

    db: AsyncSession = Depends(get_db)

):

    station = await db.get(EVChargingStation, data.station_id)

    if not station:

        raise HTTPException(status_code=404, detail="EV Charging Station not found")



    net_avoided_kg, has_anomaly, anomaly_reason = EVQuantificationEngine.calculate_avoided_emissions(data, station)



    session = EVChargingSession(

        station_id=data.station_id,

        vehicle_vin=data.vehicle_vin,

        fleet_operator_id=data.fleet_operator_id,

        start_time=data.start_time,

        end_time=data.end_time,

        energy_consumed_kwh=data.energy_consumed_kwh,

        distance_displaced_km=data.distance_displaced_km,

        baseline_vehicle_type=data.baseline_vehicle_type,

        battery_state_of_health_pct=data.battery_state_of_health_pct,

        net_co2e_avoided_kg=net_avoided_kg,

        has_anomaly=has_anomaly,

        anomaly_reason=anomaly_reason

    )

    db.add(session)

    await db.commit()

    await db.refresh(session)

    return session



@router.get("/sessions", response_model=List[EVChargingSessionResponse])

async def list_charging_sessions(

    station_id: Optional[UUID] = None,

    limit: int = 50,

    offset: int = 0,

    db: AsyncSession = Depends(get_db)

):

    stmt = select(EVChargingSession)

    if station_id:

        stmt = stmt.where(EVChargingSession.station_id == station_id)

    stmt = stmt.order_by(EVChargingSession.start_time.desc()).limit(limit).offset(offset)

    res = await db.execute(stmt)

    return res.scalars().all()



@router.get("/summary", response_model=EVSummaryResponse)

async def get_ev_summary(

    project_id: Optional[UUID] = None,

    db: AsyncSession = Depends(get_db)

):

    stations_stmt = select(func.count(EVChargingStation.id))

    if project_id:

        stations_stmt = stations_stmt.where(EVChargingStation.project_id == project_id)

    total_st = (await db.execute(stations_stmt)).scalar() or 0



    sessions_stmt = select(

        func.count(EVChargingSession.id).label("total_sessions"),

        func.coalesce(func.sum(EVChargingSession.energy_consumed_kwh), 0.0).label("total_kwh"),

        func.coalesce(func.sum(EVChargingSession.distance_displaced_km), 0.0).label("total_km"),

        func.coalesce(func.sum(EVChargingSession.net_co2e_avoided_kg), 0.0).label("total_kg_co2"),

        func.coalesce(func.avg(EVChargingSession.battery_state_of_health_pct), 100.0).label("avg_soh"),

        func.count(EVChargingSession.id).filter(EVChargingSession.has_anomaly == True).label("anomaly_count")

    )

    if project_id:

        sessions_stmt = sessions_stmt.join(EVChargingStation).where(EVChargingStation.project_id == project_id)



    res = await db.execute(sessions_stmt)

    row = res.one()



    return {

        "total_stations": total_st,

        "total_charging_sessions": row.total_sessions or 0,

        "total_energy_kwh": float(row.total_kwh),

        "total_distance_displaced_km": float(row.total_km),

        "total_co2e_avoided_tonnes": round(float(row.total_kg_co2) / 1000.0, 3),

        "avg_fleet_battery_health": round(float(row.avg_soh), 1),

        "anomalies_count": row.anomaly_count or 0

    }
