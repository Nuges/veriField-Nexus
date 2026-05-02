"""
=============================================================================
VeriField Nexus — Property Schemas
=============================================================================
Pydantic models for property management in the Real Estate module.
=============================================================================
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------

class PropertyCreate(BaseModel):
    """Schema for creating a new property."""
    name: str = Field(..., min_length=2, max_length=255, description="Property name")
    address: Optional[str] = Field(None, description="Full property address")
    property_type: str = Field(
        default="residential",
        description="Type: residential, commercial, agricultural, industrial, mixed"
    )
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)


class PropertyUpdate(BaseModel):
    """Schema for updating a property."""
    name: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = None
    property_type: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------

class PropertyResponse(BaseModel):
    """Schema for property data in API responses."""
    id: UUID
    owner_id: UUID
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
    """Schema for paginated property list."""
    properties: List[PropertyResponse]
    total: int
    page: int
    per_page: int


class PropertyDetailResponse(PropertyResponse):
    """Extended property response with activity summary."""
    total_activities: int = 0
    avg_trust_score: Optional[float] = None
    activity_breakdown: Optional[Dict[str, int]] = None  # Count by type
