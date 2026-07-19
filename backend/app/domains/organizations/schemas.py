from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    org_type: Optional[str] = "DEVELOPER"
    parent_id: Optional[UUID] = None
    metadata_context: Optional[Dict[str, Any]] = {}

    # Legacy fields
    plan: Optional[str] = "FREE"
    licensed_methodologies: Optional[List[str]] = Field(default_factory=list)


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    org_type: Optional[str] = None
    metadata_context: Optional[Dict[str, Any]] = None

    # Legacy fields
    plan: Optional[str] = None
    licensed_methodologies: Optional[List[str]] = None


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    org_type: str
    status: str
    parent_id: Optional[UUID] = None
    metadata_context: Dict[str, Any]
    version: int
    is_deleted: bool
    deleted_at: Optional[datetime] = None

    # Legacy fields
    plan: str
    max_installations: int
    max_agents: int
    created_at: datetime

    model_config = {"from_attributes": True}
