from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PropertyCreate(BaseModel):
    name: str
    address: Optional[str] = None
    property_type: str = "residential"
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)


class PropertyUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    property_type: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)


class PropertyResponse(BaseModel):
    id: UUID
    owner_id: UUID
    organization_id: Optional[UUID] = None
    name: str
    address: Optional[str] = None
    property_type: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    sustainability_metrics: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PropertyListResponse(BaseModel):
    properties: List[PropertyResponse]
    total: int
    page: int
    per_page: int


class PropertyDetailResponse(PropertyResponse):
    total_activities: int = 0
    avg_trust_score: Optional[float] = None
    activity_breakdown: Optional[Dict[str, int]] = None
