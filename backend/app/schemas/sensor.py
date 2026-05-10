"""
=============================================================================
VeriField Nexus — Sensor Reading Schemas
=============================================================================
Pydantic models for sensor reading request/response validation.
=============================================================================
"""

from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class SensorReadingCreate(BaseModel):
    asset_id: UUID
    device_id: str
    temperature: Optional[float] = None
    usage_flag: bool = False
    fuel_weight_kg: Optional[float] = None
    battery_voltage: Optional[float] = None


class SensorReadingResponse(BaseModel):
    id: UUID
    asset_id: UUID
    device_id: str
    temperature: Optional[float] = None
    usage_flag: bool
    fuel_weight_kg: Optional[float] = None
    battery_voltage: Optional[float] = None
    timestamp: datetime

    # Joined fields
    property_name: Optional[str] = None

    model_config = {"from_attributes": True}


class SensorReadingListResponse(BaseModel):
    readings: List[SensorReadingResponse]
    total: int
    page: int
    per_page: int


class DeviceSummary(BaseModel):
    """Aggregated summary for a unique device."""
    device_id: str
    asset_id: UUID
    property_name: Optional[str] = None
    reading_count: int
    last_reading: Optional[datetime] = None
    last_temperature: Optional[float] = None
    last_battery_voltage: Optional[float] = None
    usage_rate: Optional[float] = None  # percentage of readings with usage_flag=True


class DeviceListResponse(BaseModel):
    devices: List[DeviceSummary]
    total: int
