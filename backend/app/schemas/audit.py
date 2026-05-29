"""
=============================================================================
VeriField Nexus — Audit Task Schemas
=============================================================================
Pydantic models for audit task request/response validation.
=============================================================================
"""

from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class AuditTaskCreate(BaseModel):
    asset_id: UUID
    assigned_agent: UUID
    status: str = "pending"
    deadline: Optional[datetime] = None


class AuditTaskUpdate(BaseModel):
    status: Optional[str] = None
    deadline: Optional[datetime] = None
    assigned_agent: Optional[UUID] = None


class AuditTaskResponse(BaseModel):
    id: UUID
    asset_id: UUID
    assigned_agent: UUID
    status: str
    deadline: Optional[datetime] = None
    created_at: datetime

    # Joined fields (populated from relationships)
    property_name: Optional[str] = None
    property_address: Optional[str] = None
    property_type: Optional[str] = None
    agent_name: Optional[str] = None

    model_config = {"from_attributes": True}


class AuditTaskListResponse(BaseModel):
    audits: List[AuditTaskResponse]
    total: int
    page: int
    per_page: int
