from pydantic import BaseModel, Field

from typing import Optional, Dict, Any, List

from datetime import datetime

from uuid import UUID



class EVChargingStationCreate(BaseModel):

    project_id: UUID

    station_code: str

    operator_name: str

    location_name: str

    latitude: float

    longitude: float

    charger_type: str = "DC_FAST"

    max_output_kw: float = 50.0

    grid_emission_factor_kg_kwh: float = 0.45

    renewable_source_pct: float = 0.0



class EVChargingSessionCreate(BaseModel):

    station_id: UUID

    vehicle_vin: str

    fleet_operator_id: Optional[str] = None

    start_time: datetime

    end_time: datetime

    energy_consumed_kwh: float = Field(..., gt=0)

    distance_displaced_km: float = Field(..., gt=0)

    baseline_vehicle_type: str = "ICE_DIESEL"

    battery_state_of_health_pct: float = Field(98.0, ge=0, le=100)



class EVChargingSessionResponse(BaseModel):

    id: UUID

    station_id: UUID

    vehicle_vin: str

    fleet_operator_id: Optional[str] = None

    start_time: datetime

    end_time: datetime

    energy_consumed_kwh: float

    distance_displaced_km: float

    baseline_vehicle_type: str

    battery_state_of_health_pct: float

    net_co2e_avoided_kg: float

    has_anomaly: bool

    anomaly_reason: Optional[str] = None

    created_at: datetime



    class Config:

        from_attributes = True



class EVSummaryResponse(BaseModel):

    total_stations: int

    total_charging_sessions: int

    total_energy_kwh: float

    total_distance_displaced_km: float

    total_co2e_avoided_tonnes: float

    avg_fleet_battery_health: float

    anomalies_count: int
