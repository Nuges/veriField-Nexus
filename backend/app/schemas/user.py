"""
=============================================================================
VeriField Nexus — User Schemas
=============================================================================
Pydantic models for user-related request/response validation.
=============================================================================
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    """Schema for creating a new user account."""
    email: Optional[str] = Field(None, max_length=255, description="User email address")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number with country code")
    full_name: str = Field(..., min_length=2, max_length=255, description="User's full name")
    password: str = Field(..., min_length=8, description="Account password (min 8 characters)")
    role: str = Field(default="field_agent", description="User role: field_agent or admin")
    organization: Optional[str] = Field(None, max_length=255, description="Organization name")


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    full_name: Optional[str] = Field(None, max_length=255)
    avatar_url: Optional[str] = Field(None, max_length=500)
    organization: Optional[str] = Field(None, max_length=255)


class UserLogin(BaseModel):
    """Schema for user login."""
    email: Optional[str] = Field(None, description="Email for email-based login")
    phone: Optional[str] = Field(None, description="Phone for phone-based login")
    password: str = Field(..., description="Account password")


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------

class UserResponse(BaseModel):
    """Schema for user data in API responses."""
    id: UUID
    email: Optional[str] = None
    phone: Optional[str] = None
    full_name: str
    role: str
    avatar_url: Optional[str] = None
    organization: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    """Schema for authentication response with JWT token."""
    user: UserResponse
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Token expiry in seconds")
