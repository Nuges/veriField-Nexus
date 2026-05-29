"""
=============================================================================
VeriField Nexus — Activity Schemas (Smart Installation System)
=============================================================================
Pydantic models for activity submission and retrieval.
Supports structured, registry-ready data for carbon verification.
=============================================================================
"""

from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum


# ---------------------------------------------------------------------------
# Activity Type Enum
# ---------------------------------------------------------------------------

class ActivityType(str, Enum):
    CLEAN_COOKING = "CLEAN_COOKING"


# ---------------------------------------------------------------------------
# Per-Type Field Schemas (for validation reference)
# ---------------------------------------------------------------------------

ACTIVITY_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "CLEAN_COOKING": {
        "fields": [
            # Stove Details
            {"key": "stove_id", "label": "Stove ID (QR/BLE)", "type": "string", "required": True},
            {"key": "stove_model", "label": "Stove Model", "type": "enum", "required": True,
             "options": ["baikuc_gen1", "tlud_forced", "rocket", "gasifier", "jiko", "lpg_burner", "electric_ics", "other"]},
            {"key": "manufacturer", "label": "Manufacturer", "type": "string", "required": False},
            {"key": "serial_number", "label": "Serial Number", "type": "string", "required": False},
            # Household Details
            {"key": "household_id", "label": "Household ID", "type": "string", "required": True},
            {"key": "head_name", "label": "Head of Household Name", "type": "string", "required": True},
            {"key": "phone_number", "label": "Phone Number", "type": "string", "required": False},
            {"key": "household_size", "label": "Household Size", "type": "int", "required": True},
            {"key": "meals_per_day", "label": "Meals per Day", "type": "enum", "required": True,
             "options": ["1", "2", "3", "4+"]},
            {"key": "consent_obtained", "label": "Consent Obtained?", "type": "boolean", "required": True},
            # Baseline Data
            {"key": "baseline_fuel", "label": "Primary Baseline Fuel", "type": "enum", "required": True,
             "options": ["wood", "charcoal", "crop_residue", "dung", "kerosene", "lpg", "grid_electric"]},
            {"key": "baseline_stove", "label": "Baseline Stove Type", "type": "enum", "required": True,
             "options": ["3_stone_fire", "traditional_clay", "metal_grate", "kerosene_stove", "gas_burner", "other"]},
            {"key": "baseline_fuel_consumption", "label": "Monthly Fuel Before (kg/L)", "type": "float", "required": True},
            {"key": "baseline_fuel_cost", "label": "Monthly Fuel Cost Before (\u20a6)", "type": "float", "required": True},
            {"key": "baseline_cooking_duration", "label": "Daily Cooking Before (hrs)", "type": "float", "required": True},
            {"key": "fuel_source", "label": "Fuel Source", "type": "enum", "required": True,
             "options": ["collected_free", "purchased"]},
            # Project Data
            {"key": "primary_fuel", "label": "Project Primary Fuel", "type": "enum", "required": True,
             "options": ["wood", "pellet", "charcoal", "lpg", "biogas", "electric"]},
            {"key": "usage_flag", "label": "Currently in Use?", "type": "boolean", "required": True},
            {"key": "project_cooking_duration", "label": "Daily Cooking Now (hrs)", "type": "float", "required": True},
            {"key": "stove_condition", "label": "Stove Condition", "type": "enum", "required": True,
             "options": ["good", "minor_damage", "needs_repair", "abandoned"]},
        ],
        "icon": "soup_kitchen",
        "description": "Clean cooking stove installation & usage logging",
        "methodology": "Gold Standard TPDDTEC v3.1",
    },
}


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------

class ActivityCreate(BaseModel):
    """
    Schema for submitting a new field activity / installation.
    
    Required fields: activity_type, captured_at
    Recommended: image_url, latitude, longitude (for trust scoring)
    """
    # Activity details
    activity_type: str = Field(
        default="CLEAN_COOKING",
        description="Activity type: CLEAN_COOKING"
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

    # Smart GPS validation fields
    environment_type: Optional[str] = Field(None, description="URBAN or RURAL (auto-detected)")
    radius_used_m: Optional[float] = Field(None, description="Radius used for duplicate check")
    duplicate_flag: Optional[bool] = Field(False, description="True if nearby duplicate was detected")
    override_reason: Optional[str] = Field(None, description="Agent reason for overriding duplicate warning")

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
    agent_name: Optional[str] = None
    property_id: Optional[UUID] = None
    activity_type: str
    activity_data: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
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
