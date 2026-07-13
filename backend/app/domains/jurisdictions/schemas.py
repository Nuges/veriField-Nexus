from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.domains.jurisdictions.models import JurisdictionLevel


class JurisdictionCreate(BaseModel):
    name: str = Field(..., max_length=255)
    code: str = Field(..., max_length=50)
    level: JurisdictionLevel
    parent_id: Optional[UUID] = None
    metadata_context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    spatial_boundary: Optional[Dict[str, Any]] = Field(default_factory=dict)


class JurisdictionUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    code: Optional[str] = Field(None, max_length=50)
    level: Optional[JurisdictionLevel] = None
    parent_id: Optional[UUID] = None
    metadata_context: Optional[Dict[str, Any]] = None
    spatial_boundary: Optional[Dict[str, Any]] = None
    status: Optional[str] = Field(None, max_length=50)
    health_score: Optional[float] = None


class JurisdictionResponse(BaseModel):
    id: UUID
    parent_id: Optional[UUID] = None
    code: str
    name: str
    level: JurisdictionLevel
    metadata_context: Dict[str, Any]
    spatial_boundary: Dict[str, Any]
    status: str
    health_score: float
    version: int
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
