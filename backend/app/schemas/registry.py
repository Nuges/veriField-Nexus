"""
=============================================================================
VeriField Nexus — Registry Schemas
=============================================================================
Pydantic models for registry export data.
=============================================================================
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class VerraExportRow(BaseModel):
    """Single row in Verra registry export."""
    asset_id: str
    asset_name: str
    asset_type: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    activity_id: str
    activity_type: str
    captured_at: str
    submitted_at: str
    verification_status: str
    trust_score: Optional[float] = None
    methodology: str
    tco2e: float
    sensor_corroborated: bool = False
    community_validated: bool = False
    audit_passed: bool = False


class RegistryExportResponse(BaseModel):
    """Metadata response for registry export."""
    registry: str
    format: str
    total_records: int
    total_tco2e: float
    exported_at: str
    download_info: str
