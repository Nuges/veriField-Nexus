"""
=============================================================================
VeriField Nexus — Access Request Schemas
=============================================================================
Pydantic models for access request lead validation.
=============================================================================
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class AccessRequestCreate(BaseModel):
    """Schema for public access request / lead submission."""
    full_name: str = Field(..., min_length=2, max_length=255, description="Full name of applicant")
    email: str = Field(..., description="Business email address")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    organization_name: str = Field(..., min_length=2, max_length=255, description="Desired organization name")
    country: Optional[str] = Field(None, max_length=100, description="Country of operations")
    use_case: Optional[str] = Field(None, max_length=500, description="Explanation of MRV project use case")


class AccessRequestResponse(BaseModel):
    """Schema for access request responses in admin audits."""
    id: UUID
    full_name: str
    email: str
    phone: Optional[str] = None
    organization_name: str
    country: Optional[str] = None
    use_case: Optional[str] = None
    status: str
    created_at: datetime
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AccessRequestApprovalResponse(BaseModel):
    """Credentials returned to admin upon lead approval for onboarding delivery."""
    message: str
    organization_id: UUID
    organization_name: str
    org_admin_email: str
    temporary_password: str
