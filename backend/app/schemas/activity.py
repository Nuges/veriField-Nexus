"""
=============================================================================
VeriField Nexus — Activity Schemas
=============================================================================
Pydantic models for activity submission and retrieval.
Supports both single and batch submissions for offline sync.
=============================================================================
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------

class ActivityCreate(BaseModel):
    """
    Schema for submitting a new field activity.
    
    Required fields: activity_type, captured_at
    Recommended: image_url, latitude, longitude (for trust scoring)
    """
    # Activity details
    activity_type: str = Field(
        ...,
        description="Type: cooking, farming, energy, sustainability, other"
    )
    activity_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Structured data specific to activity type"
    )
    description: Optional[str] = Field(None, max_length=1000)

    # Photo proof
    image_url: Optional[str] = Field(None, description="Supabase Storage URL of captured photo")
    image_hash: Optional[str] = Field(None, description="Client-computed perceptual hash")

    # Location data (auto-captured by device)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    gps_accuracy: Optional[float] = Field(None, ge=0, description="GPS accuracy in meters")

    # Timestamps
    captured_at: datetime = Field(..., description="When the activity was actually performed")

    # Property association (optional)
    property_id: Optional[UUID] = Field(None, description="Associated property UUID")

    # Offline sync — client-generated UUID to prevent duplicates
    client_id: Optional[str] = Field(None, max_length=36, description="Client UUID for deduplication")


class ActivityBatchCreate(BaseModel):
    """Schema for batch-submitting multiple activities (offline sync)."""
    activities: List[ActivityCreate] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of activities to submit (max 50 per batch)"
    )


class ActivityFilter(BaseModel):
    """Schema for filtering activities in list endpoint."""
    activity_type: Optional[str] = None
    status: Optional[str] = None
    user_id: Optional[UUID] = None
    property_id: Optional[UUID] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    min_trust_score: Optional[float] = Field(None, ge=0, le=100)
    max_trust_score: Optional[float] = Field(None, ge=0, le=100)
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------

class ActivityResponse(BaseModel):
    """Schema for a single activity in API responses."""
    id: UUID
    user_id: UUID
    property_id: Optional[UUID] = None
    activity_type: str
    activity_data: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    gps_accuracy: Optional[float] = None
    captured_at: datetime
    submitted_at: datetime
    trust_score: Optional[float] = None
    trust_flags: Optional[Dict[str, Any]] = None
    status: str
    client_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ActivityListResponse(BaseModel):
    """Schema for paginated activity list."""
    activities: List[ActivityResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class ActivityBatchResponse(BaseModel):
    """Schema for batch submission response."""
    submitted: int = Field(description="Number of successfully submitted activities")
    duplicates: int = Field(description="Number of skipped duplicate entries")
    errors: int = Field(description="Number of failed submissions")
    results: List[Dict[str, Any]] = Field(description="Individual submission results")
