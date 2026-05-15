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
            {"key": "baseline_fuel_cost", "label": "Monthly Fuel Cost Before (₦)", "type": "float", "required": True},
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
        "icon": "local_fire_department",
        "description": "Clean cooking stove installation & usage logging",
        "methodology": "Gold Standard TPDDTEC v3.1",
    },
    "AGRICULTURE": {
        "fields": [
            # Plot Details
            {"key": "plot_id", "label": "Plot ID", "type": "string", "required": True},
            {"key": "farmer_name", "label": "Farmer Name", "type": "string", "required": True},
            {"key": "farmer_phone", "label": "Farmer Phone", "type": "string", "required": True},
            {"key": "land_tenure", "label": "Land Tenure Type", "type": "enum", "required": True,
             "options": ["owned", "leased", "communal", "other"]},
            {"key": "plot_area_hectares", "label": "Plot Area (ha)", "type": "float", "required": True},
            {"key": "agro_zone", "label": "Agro-ecological Zone", "type": "enum", "required": True,
             "options": ["sudan_savanna", "guinea_savanna", "forest_transition", "humid_forest", "mangrove"]},
            # Baseline Data
            {"key": "baseline_land_use", "label": "Previous Land Use", "type": "enum", "required": True,
             "options": ["cropland_conventional", "degraded_pasture", "bare_eroded", "fallow", "natural_veg"]},
            {"key": "baseline_practice", "label": "Previous Practice", "type": "enum", "required": True,
             "options": ["conventional_tillage", "burning", "no_cover_crop", "synthetic_only", "none"]},
            {"key": "baseline_crop", "label": "Previous Crop", "type": "string", "required": False},
            {"key": "baseline_synthetic_fert", "label": "Synthetic Fert Before?", "type": "boolean", "required": True},
            {"key": "baseline_fert_amount", "label": "Amount Before (kg/ha)", "type": "float", "required": False},
            {"key": "baseline_burning", "label": "Burning Practiced Before?", "type": "boolean", "required": True},
            # Project Practice
            {"key": "crop_type", "label": "Crop Type", "type": "enum", "required": True,
             "options": ["maize", "cassava", "rice", "sorghum", "cowpea", "yam", "soybean", "mixed", "other"]},
            {"key": "practice_type", "label": "Practice Type", "type": "enum", "required": True,
             "options": ["conservation_tillage", "cover_cropping", "agroforestry", "composting", "crop_rotation", "biochar", "other"]},
            {"key": "soil_type", "label": "Soil Type", "type": "enum", "required": True,
             "options": ["clay", "loam", "sandy", "silt", "peat"]},
            {"key": "irrigation_method", "label": "Irrigation Method", "type": "enum", "required": False,
             "options": ["rainfed", "drip", "flood", "sprinkler"]},
            {"key": "fertiliser_type", "label": "Fertiliser Type", "type": "enum", "required": True,
             "options": ["none", "organic_only", "synthetic_only", "both"]},
            {"key": "biomass_retained", "label": "Biomass Retained?", "type": "boolean", "required": True},
            {"key": "livestock_integration", "label": "Livestock Integration?", "type": "boolean", "required": False},
            # Measurements
            {"key": "soil_organic_carbon", "label": "Soil Organic Carbon (%)", "type": "float", "required": False},
            {"key": "soil_moisture", "label": "Soil Moisture (%)", "type": "float", "required": False},
            {"key": "crop_yield", "label": "Crop Yield (tonnes/ha)", "type": "float", "required": False},
        ],
        "icon": "grass",
        "description": "Agricultural practices & sustainable land management",
        "methodology": "Verra VM0042",
    },
    "ENERGY_USE": {
        "fields": [
            # System Details
            {"key": "system_id", "label": "System ID", "type": "string", "required": True},
            {"key": "device_type", "label": "Device Type", "type": "enum", "required": True,
             "options": ["solar_panel", "solar_lantern", "biogas", "wind", "micro_hydro", "solar_water_heater", "solar_pump"]},
            {"key": "manufacturer", "label": "Manufacturer/Model", "type": "string", "required": False},
            {"key": "serial_number", "label": "Serial Number", "type": "string", "required": False},
            # Technical Specs
            {"key": "capacity_kw", "label": "Installed Capacity (kW)", "type": "float", "required": True},
            {"key": "battery_storage_kwh", "label": "Battery Storage (kWh)", "type": "float", "required": False},
            {"key": "grid_connected", "label": "Grid Connected?", "type": "boolean", "required": True},
            {"key": "daily_output_kwh", "label": "Daily Generation (kWh)", "type": "float", "required": False},
            {"key": "metered", "label": "Metered?", "type": "boolean", "required": True},
            # Baseline Data
            {"key": "baseline_energy", "label": "Baseline Energy Source", "type": "enum", "required": True,
             "options": ["kerosene_lamp", "diesel_generator", "grid_electricity", "candles", "firewood", "charcoal", "no_access"]},
            {"key": "baseline_fuel_volume", "label": "Monthly Baseline Fuel (L/kWh)", "type": "float", "required": True},
            {"key": "baseline_energy_cost", "label": "Monthly Baseline Cost (₦)", "type": "float", "required": True},
            {"key": "baseline_hours", "label": "Hours of Access Before", "type": "float", "required": True},
            # Usage
            {"key": "households_served", "label": "Households Served", "type": "int", "required": True},
            {"key": "population_served", "label": "Population Served", "type": "int", "required": True},
            {"key": "project_hours", "label": "Hours of Access Now", "type": "float", "required": True},
            {"key": "system_condition", "label": "System Condition", "type": "enum", "required": True,
             "options": ["good", "needs_maintenance", "faulty", "decommissioned"]},
        ],
        "icon": "bolt",
        "description": "Renewable energy installations & usage tracking",
        "methodology": "CDM AMS-I.A.",
    },
    "FORESTRY_LAND_USE": {
        "fields": [
            # Plot Details
            {"key": "plot_id", "label": "Plot ID", "type": "string", "required": True},
            {"key": "community_name", "label": "Community/Owner Name", "type": "string", "required": True},
            {"key": "land_tenure", "label": "Land Tenure", "type": "enum", "required": True,
             "options": ["owned", "community", "government", "leased"]},
            {"key": "plot_area_hectares", "label": "Plot Area (ha)", "type": "float", "required": True},
            {"key": "ecosystem_type", "label": "Ecosystem Type", "type": "enum", "required": True,
             "options": ["tropical_dry", "tropical_moist", "savanna", "mangrove", "riparian", "degraded_grassland"]},
            # Baseline Land Use
            {"key": "baseline_land_use", "label": "Previous Land Use", "type": "enum", "required": True,
             "options": ["degraded_cropland", "bare_eroded", "degraded_grassland", "deforested", "shrubland"]},
            {"key": "years_deforested", "label": "Years Since Deforested", "type": "int", "required": False},
            {"key": "evidence_previous_forest", "label": "Evidence of Prev Forest?", "type": "boolean", "required": True},
            {"key": "baseline_carbon_stock", "label": "Baseline Carbon (tCO2/ha)", "type": "float", "required": False},
            # Planting Data
            {"key": "tree_count", "label": "Trees Planted/Surviving", "type": "int", "required": True},
            {"key": "species", "label": "Species", "type": "string", "required": True},
            {"key": "native_species", "label": "Native Species?", "type": "boolean", "required": True},
            {"key": "planting_pattern", "label": "Planting Pattern", "type": "enum", "required": True,
             "options": ["row", "grid", "random", "contour"]},
            # Survival Monitoring
            {"key": "survival_rate_pct", "label": "Survival Rate (%)", "type": "float", "required": True},
            {"key": "avg_height_cm", "label": "Average Height (cm)", "type": "float", "required": True},
            {"key": "avg_dbh_cm", "label": "Average DBH (cm)", "type": "float", "required": False},
            {"key": "canopy_cover", "label": "Canopy Cover (%)", "type": "enum", "required": False,
             "options": ["<25", "25-50", "50-75", ">75"]},
            {"key": "threats_observed", "label": "Threats Observed", "type": "enum", "required": True,
             "options": ["none", "grazing", "fire", "pests", "drought", "flooding", "human"]},
        ],
        "icon": "park",
        "description": "Tree planting, reforestation & land use change",
        "methodology": "Verra VM0047 ARR",
    },
    "SAFE_WATER": {
        "fields": [
            # Installation Details
            {"key": "water_point_id", "label": "Water Point ID", "type": "string", "required": True},
            {"key": "water_source_type", "label": "Source Type", "type": "enum", "required": True,
             "options": ["borehole", "handpump", "solar_pump", "gravity_fed", "biosand_filter", "ceramic_filter", "chlorination"]},
            {"key": "community_name", "label": "Community Name", "type": "string", "required": True},
            # Usage Data
            {"key": "households_served", "label": "Households Served", "type": "int", "required": True},
            {"key": "population_served", "label": "Population Served", "type": "int", "required": True},
            {"key": "daily_volume_liters", "label": "Daily Volume Dispensed (L)", "type": "float", "required": True},
            {"key": "operating_hours", "label": "Operating Hours/Day", "type": "float", "required": True},
            {"key": "days_operational", "label": "Days Operational/Month", "type": "int", "required": True},
            # Baseline Data
            {"key": "baseline_water_source", "label": "Previous Water Source", "type": "enum", "required": True,
             "options": ["unprotected_well", "river_stream", "rainwater", "purchased", "borehole"]},
            {"key": "baseline_treatment", "label": "Previous Treatment", "type": "enum", "required": True,
             "options": ["boiling", "chemical", "none", "solar_disinfection"]},
            {"key": "baseline_fuel", "label": "Previous Fuel for Boiling", "type": "enum", "required": False,
             "options": ["wood", "charcoal", "kerosene", "lpg"]},
            {"key": "baseline_fuel_cost", "label": "Monthly Fuel Cost Before (₦)", "type": "float", "required": False},
            # Water Quality & Status
            {"key": "water_quality_tested", "label": "Water Quality Tested?", "type": "boolean", "required": True},
            {"key": "test_result", "label": "Test Result", "type": "enum", "required": False,
             "options": ["pass", "fail"]},
            {"key": "operational_status", "label": "Operational Status", "type": "enum", "required": True,
             "options": ["active", "faulty", "maintenance", "decommissioned"]},
        ],
        "icon": "water_drop",
        "description": "Safe water supply & purification systems",
        "methodology": "Gold Standard Safe Water",
    },
    "TRANSPORT_MOBILITY": {
        "fields": [
            {"key": "vehicle_type", "label": "Vehicle Type", "type": "enum",
             "options": ["motorcycle_okada", "tricycle_keke", "car_taxi", "minibus_danfo", "bus", "light_truck", "heavy_truck", "forklift"], "required": True},
            {"key": "energy_type", "label": "Energy Type", "type": "enum",
             "options": ["EV", "hybrid", "CNG", "LPG", "diesel_retrofit"], "required": True},
            {"key": "vehicle_id", "label": "Vehicle ID", "type": "string", "required": True},
            {"key": "registration_number", "label": "Registration Number", "type": "string", "required": True},
            {"key": "odometer_start", "label": "Odometer Start (km)", "type": "float", "required": True},
            {"key": "odometer_end", "label": "Odometer End (km)", "type": "float", "required": True},
            {"key": "operating_days", "label": "Operating Days", "type": "int", "required": True},
            {"key": "energy_used", "label": "Energy Used", "type": "float", "required": True},
            {"key": "energy_unit", "label": "Energy Unit", "type": "enum",
             "options": ["kWh", "litres", "m3"], "required": False},
            {"key": "charging_source", "label": "Charging Source", "type": "enum",
             "options": ["grid", "solar_onsite", "solar_offsite", "generator", "mixed"], "required": False},
            {"key": "operating_hours", "label": "Operating Hours", "type": "float", "required": False},
        ],
        "icon": "directions_car",
        "description": "Clean transport & low-emission mobility (AMS-III.C)",
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
