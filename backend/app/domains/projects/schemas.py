from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=2)
    country: str | None = None
    programme_id: Optional[UUID] = None
    methodology_id: UUID
    methodology_version_id: Optional[UUID] = None
    registry_id: Optional[str] = None
    baseline_source: Optional[str] = "diesel_generator"
    diesel_emission_factor: Optional[float] = 2.68
    grid_emission_factor: Optional[float] = 0.7
    crediting_start: Optional[date] = None
    crediting_end: Optional[date] = None
    baseline_parameters: Optional[Dict[str, Any]] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    registry_id: Optional[str] = None
    crediting_start: Optional[date] = None
    crediting_end: Optional[date] = None
    baseline_parameters: Optional[Dict[str, Any]] = None


class ProjectResponse(BaseModel):
    id: UUID
    project_code: Optional[str] = None
    name: str
    country: str
    organization_id: Optional[UUID] = None
    jurisdiction_id: Optional[UUID] = None
    programme_id: Optional[UUID] = None
    methodology_id: UUID
    methodology_version_id: Optional[UUID] = None
    registry_id: Optional[str] = None
    baseline_source: str
    diesel_emission_factor: float
    grid_emission_factor: float
    crediting_start: Optional[date] = None
    crediting_end: Optional[date] = None
    baseline_parameters: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    items: List[ProjectResponse]
    total: int
