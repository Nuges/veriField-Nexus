"""
=============================================================================
VeriField Nexus — Verification Data Models
=============================================================================
Pydantic schemas governing structural validation rules for API request and
response payloads.
=============================================================================
"""

from typing import Optional
from pydantic import BaseModel, Field


class GPSCoordinates(BaseModel):
    latitude: float = Field(..., description="GPS latitude coordinates", ge=-90.0, le=90.0)
    longitude: float = Field(..., description="GPS longitude coordinates", ge=-180.0, le=180.0)
    accuracy: Optional[float] = Field(None, description="GPS reading accuracy range in meters")


class DeviceSignature(BaseModel):
    deviceId: str = Field(..., description="Unique hardware identifier of the capture device")
    os: Optional[str] = Field(None, description="Operating system version")
    appVersion: Optional[str] = Field(None, description="Capture client software version")


class VerificationRequest(BaseModel):
    assetType: str = Field(..., description="Climate asset type category (e.g., 'cookstove' | 'hybrid_energy')")
    gps: GPSCoordinates = Field(..., description="Location coordinate parameters")
    timestamp: int = Field(..., description="Captured epoch timestamp in Unix seconds", gt=0)
    imageHash: str = Field(..., description="Evidence payload SHA-256 cryptographic hash", min_length=64, max_length=64)
    deviceSignature: Optional[DeviceSignature] = Field(None, description="Client device identity details")


class VerificationResponse(BaseModel):
    id: str = Field(..., description="Unique generated verification UUID")
    assetType: str = Field(..., description="The evaluated climate asset type")
    gps: GPSCoordinates = Field(..., description="The verified coordinate specs")
    timestamp: int = Field(..., description="The epoch timestamp verified")
    imageHash: str = Field(..., description="Cryptographic evidence hash anchored on-chain")
    verificationScore: int = Field(..., description="Calculated Trust Engine score (0-100)", ge=0, le=100)
    solanaSignature: str = Field(..., description="Simulated on-chain anchor transaction hash signature")
    anchoredAt: str = Field(..., description="ISO 8601 UTC timestamp of on-chain committing")
