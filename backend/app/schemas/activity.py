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
    AGRICULTURE = "AGRICULTURE"
    ENERGY_USE = "ENERGY_USE"
    FORESTRY_LAND_USE = "FORESTRY_LAND_USE"
    SAFE_WATER = "SAFE_WATER"
    TRANSPORT_MOBILITY = "TRANSPORT_MOBILITY"
    OTHER = "OTHER"


# ---------------------------------------------------------------------------
# Per-Type Field Schemas (for validation reference)
# ---------------------------------------------------------------------------

ACTIVITY_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "CLEAN_COOKING": {
        "fields": [
            {"key": "stove_id", "label": "Stove ID", "type": "string", "required": True},
            {"key": "household_size", "label": "Household Size", "type": "int", "required": True},
            {"key": "primary_fuel", "label": "Primary Fuel", "type": "enum",
             "options": ["wood", "pellet", "charcoal", "LPG"], "required": True},
            {"key": "usage_flag", "label": "Currently in Use?", "type": "boolean", "required": True},
        ],
        "icon": "local_fire_department",
        "description": "Clean cooking stove installation & usage logging",
        "methodology": "Gold Standard TPDDTEC v3.1",
    },
    "AGRICULTURE": {
        "fields": [
            {"key": "crop_type", "label": "Crop Type", "type": "string", "required": True},
            {"key": "plot_area_hectares", "label": "Plot Area (ha)", "type": "float", "required": True},
            {"key": "practice_type", "label": "Practice Type", "type": "enum",
             "options": ["conservation_tillage", "cover_cropping", "agroforestry", "composting", "other"], "required": True},
            {"key": "soil_type", "label": "Soil Type", "type": "enum",
             "options": ["clay", "loam", "sandy", "silt", "peat"], "required": False},
        ],
        "icon": "grass",
        "description": "Agricultural practices & sustainable land management",
        "methodology": "Verra VM0042",
    },
    "ENERGY_USE": {
        "fields": [
            {"key": "device_type", "label": "Device Type", "type": "enum",
             "options": ["solar_panel", "solar_lantern", "biogas", "wind", "micro_hydro"], "required": True},
            {"key": "capacity_kw", "label": "Capacity (kW)", "type": "float", "required": True},
            {"key": "daily_output_kwh", "label": "Daily Output (kWh)", "type": "float", "required": False},
            {"key": "households_served", "label": "Households Served", "type": "int", "required": True},
        ],
        "icon": "bolt",
        "description": "Renewable energy installations & usage tracking",
        "methodology": "CDM AMS-I.A.",
    },
    "FORESTRY_LAND_USE": {
        "fields": [
            {"key": "tree_count", "label": "Trees Planted", "type": "int", "required": True},
            {"key": "species", "label": "Species", "type": "string", "required": True},
            {"key": "plot_area_hectares", "label": "Plot Area (ha)", "type": "float", "required": True},
            {"key": "survival_rate_pct", "label": "Survival Rate (%)", "type": "float", "required": False},
        ],
        "icon": "park",
        "description": "Tree planting, reforestation & land use change",
        "methodology": "Verra VM0047 ARR",
    },
    "SAFE_WATER": {
        "fields": [
            {"key": "water_source_type", "label": "Water Source Type", "type": "enum",
             "options": ["borehole", "handpump", "solar_pump", "gravity_fed", "filter"], "required": True},
            {"key": "daily_volume_liters", "label": "Daily Volume (L)", "type": "float", "required": True},
            {"key": "households_served", "label": "Households Served", "type": "int", "required": True},
            {"key": "operational_status", "label": "Operational Status", "type": "enum",
             "options": ["active", "faulty", "maintenance"], "required": True},
        ],
        "icon": "water_drop",
        "description": "Safe water supply & purification systems",
        "methodology": "Gold Standard Safe Water",
    },
    "TRANSPORT_MOBILITY": {
        "fields": [
            {"key": "vehicle_id", "label": "Vehicle ID", "type": "string", "required": True},
            {"key": "energy_type", "label": "Energy Type", "type": "enum",
             "options": ["EV", "hybrid", "CNG", "diesel_retrofit"], "required": True},
            {"key": "daily_distance_km", "label": "Daily Distance (km)", "type": "float", "required": True},
            {"key": "energy_consumption_kwh", "label": "Energy Used (kWh)", "type": "float", "required": False},
        ],
        "icon": "directions_car",
        "description": "Clean transport & low-emission mobility",
        "methodology": "CDM AMS-III.C.",
    },
    "OTHER": {
        "fields": [
            {"key": "custom_activity_name", "label": "Activity Name", "type": "string", "required": True},
            {"key": "description", "label": "Description", "type": "text", "required": True},
        ],
        "icon": "more_horiz",
        "description": "Custom activity type (fallback)",
        "methodology": "Manual Review Required",
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
        ...,
        description="Type: CLEAN_COOKING, AGRICULTURE, ENERGY_USE, FORESTRY_LAND_USE, SAFE_WATER, TRANSPORT_MOBILITY, OTHER"
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
