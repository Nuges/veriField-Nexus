from pydantic import BaseModel, ConfigDict, Field

from typing import Optional, List

from datetime import datetime

from uuid import UUID



class HouseholdCreate(BaseModel):

    project_id: UUID

    household_code: str

    head_of_household: str

    phone_number: Optional[str] = None

    address: str

    community_name: str

    latitude: float

    longitude: float

    family_members_count: int = 5

    baseline_fuel_type: str = "WOOD_FIRE"

    baseline_fuel_kg_per_day: float = 7.5



class CookstoveDeviceCreate(BaseModel):

    household_id: UUID

    serial_number: str

    stove_model: str

    thermal_efficiency_pct: float = Field(45.0, ge=10, le=90)

    fuel_type_used: str = "PELLETS"

    installation_date: datetime

    installer_agent_id: Optional[UUID] = None

    photo_evidence_url: Optional[str] = None



class UsageSurveyCreate(BaseModel):

    stove_id: UUID

    surveyor_user_id: UUID

    survey_date: datetime

    is_stove_in_use: bool = True

    reported_daily_usage_hours: float = Field(..., ge=0, le=24)

    fuel_consumed_kg_per_day: float = Field(..., ge=0)

    thermal_tampering_detected: bool = False

    is_primary_cooking_method: bool = True



class UsageSurveyResponse(BaseModel):

    id: UUID

    stove_id: UUID

    surveyor_user_id: UUID

    survey_date: datetime

    is_stove_in_use: bool

    reported_daily_usage_hours: float

    fuel_consumed_kg_per_day: float

    calculated_co2e_reduction_tonnes: float

    has_fraud_flag: bool

    fraud_reason: Optional[str] = None

    created_at: datetime



    model_config = ConfigDict(from_attributes=True)



class CookstoveSummaryResponse(BaseModel):

    total_households: int

    total_stoves_deployed: int

    active_usage_rate_pct: float

    total_co2e_reduced_tonnes: float

    fraud_alerts_count: int
