from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ActivityCreate(BaseModel):
    project_id: UUID
    asset_id: Optional[UUID] = None
    property_id: Optional[UUID] = None
    activity_type: str
    activity_data: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    image_hash: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    gps_accuracy: Optional[float] = None
    captured_at: datetime
    client_id: Optional[str] = None

    # Generic evidence payload
    evidence_payload: Optional[Dict[str, Any]] = None


class ActivityUpdate(BaseModel):
    status: Optional[str] = None
    trust_score: Optional[float] = None
    validation_status: Optional[str] = None
    override_reason: Optional[str] = None


class ActivityResponse(BaseModel):
    id: UUID
    organization_id: UUID
    user_id: UUID
    agent_name: Optional[str] = None
    project_id: Optional[UUID] = None
    property_id: Optional[UUID] = None
    asset_id: Optional[UUID] = None
    activity_type: str
    activity_data: Dict[str, Any]
    description: Optional[str] = None
    image_url: Optional[str] = None
    image_hash: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    gps_accuracy: Optional[float] = None
    environment_type: Optional[str] = None
    radius_used_m: Optional[float] = None
    duplicate_flag: Optional[bool] = None
    override_reason: Optional[str] = None
    captured_at: datetime
    submitted_at: datetime
    trust_score: Optional[float] = None
    trust_flags: Optional[Dict[str, Any]] = None
    status: str
    client_id: Optional[str] = None
    created_at: datetime
    # Generic evidence JSON payload
    evidence_payload: Optional[Dict[str, Any]] = None
    validation_status: Optional[str] = None
    validation_hash: Optional[str] = None
    is_locked: Optional[bool] = None

    model_config = {"from_attributes": True}


class ActivityListResponse(BaseModel):
    activities: List[ActivityResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
