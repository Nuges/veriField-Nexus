"""
=============================================================================
VeriField Nexus — Trust & Analytics Schemas
=============================================================================
Pydantic models for trust score responses and analytics data.
=============================================================================
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# ---------------------------------------------------------------------------
# Trust Score Schemas
# ---------------------------------------------------------------------------

class TrustScoreResponse(BaseModel):
    """Detailed trust score breakdown for an activity."""
    activity_id: UUID
    gps_score: float = Field(description="GPS consistency score (0-30)")
    image_score: float = Field(description="Image uniqueness score (0-35)")
    frequency_score: float = Field(description="Submission frequency score (0-35)")
    final_score: float = Field(description="Overall trust score (0-100)")
    flags: Optional[Dict[str, Any]] = None
    calculated_at: datetime

    model_config = {"from_attributes": True}


class TrustDistribution(BaseModel):
    """Trust score distribution for analytics."""
    high: int = Field(description="Activities with score 80-100")
    medium: int = Field(description="Activities with score 50-79")
    low: int = Field(description="Activities with score 0-49")
    unscored: int = Field(description="Activities pending trust scoring")


# ---------------------------------------------------------------------------
# Analytics Schemas
# ---------------------------------------------------------------------------

class AnalyticsOverview(BaseModel):
    """High-level platform analytics."""
    total_submissions: int
    total_users: int
    total_properties: int
    avg_trust_score: Optional[float]
    flagged_activities: int
    submissions_today: int
    submissions_this_week: int


class DailySubmission(BaseModel):
    """Daily submission count for trend charts."""
    date: str  # ISO date string (YYYY-MM-DD)
    count: int
    avg_trust_score: Optional[float] = None


class ActivityTypeSummary(BaseModel):
    """Activity breakdown by type."""
    activity_type: str
    count: int
    percentage: float
    avg_trust_score: Optional[float] = None


class AnalyticsTrends(BaseModel):
    """Trend analysis response."""
    daily_submissions: List[DailySubmission]
    activity_types: List[ActivityTypeSummary]
    trust_distribution: TrustDistribution


# ---------------------------------------------------------------------------
# Export Schemas
# ---------------------------------------------------------------------------

class ExportRequest(BaseModel):
    """Schema for data export request."""
    format: str = Field(default="json", description="Export format: json or csv")
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    activity_types: Optional[List[str]] = None
    min_trust_score: Optional[float] = Field(None, ge=0, le=100)
    include_flagged: bool = Field(default=False, description="Include flagged activities")
    webhook_url: Optional[str] = Field(None, description="URL to POST exported data to")


class ExportResponse(BaseModel):
    """Schema for export response."""
    export_id: str
    record_count: int
    format: str
    data: Optional[List[Dict[str, Any]]] = None  # Present for JSON exports
    download_url: Optional[str] = None             # Present for CSV exports
    webhook_status: Optional[str] = None           # Present if webhook_url was provided
