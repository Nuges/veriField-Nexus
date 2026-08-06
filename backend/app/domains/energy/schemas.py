from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class SolarAssetCreate(BaseModel):
    project_id: UUID
    site_code: str
    site_name: str
    latitude: float
    longitude: float
    capacity_kwp: float = Field(100.0, gt=0)
    battery_capacity_kwh: float = Field(200.0, ge=0)
    diesel_generator_kw: float = Field(150.0, ge=0)


class SolarAssetResponse(BaseModel):
    id: UUID
    project_id: UUID
    site_code: str
    site_name: str
    latitude: float
    longitude: float
    capacity_kwp: float
    battery_capacity_kwh: float
    diesel_generator_kw: float
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class EnergyTelemetryCreate(BaseModel):
    solar_asset_id: UUID
    solar_generation_kwh: float = Field(..., ge=0)
    battery_discharge_kwh: float = Field(..., ge=0)
    diesel_generation_kwh: float = Field(..., ge=0)
    diesel_fuel_consumed_liters: float = Field(..., ge=0)


class EnergyTelemetryResponse(BaseModel):
    id: UUID
    solar_asset_id: UUID
    solar_generation_kwh: float
    battery_discharge_kwh: float
    diesel_generation_kwh: float
    diesel_fuel_consumed_liters: float
    grid_displaced_kwh: float
    net_co2e_avoided_tonnes: float
    has_anomaly: bool
    anomaly_reason: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class EnergyPortfolioResponse(BaseModel):
    total_sites: int
    total_installed_capacity_kwp: float
    total_battery_storage_kwh: float
    total_generation_mwh: float
    total_diesel_avoided_liters: float
    total_co2e_avoided_tonnes: float
