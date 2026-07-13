from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AssetCreate(BaseModel):
    project_id: UUID
    name: str = Field(..., min_length=2, max_length=255)
    asset_type_id: Optional[UUID] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    attributes: Optional[Dict[str, Any]] = None


class AssetUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    attributes: Optional[Dict[str, Any]] = None


class AssetResponse(BaseModel):
    id: UUID
    organization_id: UUID
    project_id: UUID
    name: str
    asset_type_id: Optional[UUID] = None
    status: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    attributes: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
