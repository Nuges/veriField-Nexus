"""
=============================================================================
VeriField Nexus — Export API Routes
=============================================================================
Endpoint to export structured data to external APIs (OYU-like systems).
Supports JSON and CSV formats with optional webhook delivery.
=============================================================================
"""

import uuid
import json
import csv
import io
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import httpx

from app.db.session import get_db
from app.core.security import require_admin
from app.models.user import User
from app.models.activity import Activity
from app.schemas.analytics import ExportRequest, ExportResponse

router = APIRouter(prefix="/export", tags=["Export"])


# =============================================================================
# POST /api/v1/export — Export data
# =============================================================================
@router.post(
    "",
    response_model=ExportResponse,
    summary="Export activity data",
)
async def export_data(
    payload: ExportRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Export verified activity data for external systems.
    Supports JSON format with optional webhook POST delivery.
    """
    # Build query with filters
    conditions = []
    if payload.date_from:
        conditions.append(Activity.captured_at >= payload.date_from)
    if payload.date_to:
        conditions.append(Activity.captured_at <= payload.date_to)
    if payload.activity_types:
        conditions.append(Activity.activity_type.in_(payload.activity_types))
    if payload.min_trust_score is not None:
        conditions.append(Activity.trust_score >= payload.min_trust_score)
    if not payload.include_flagged:
        conditions.append(Activity.status != "flagged")

    query = select(Activity)
    if conditions:
        query = query.where(and_(*conditions))
    query = query.order_by(Activity.created_at.desc())

    result = await db.execute(query)
    activities = result.scalars().all()

    # Format data for export
    export_data_list = [
        {
            "id": str(a.id),
            "user_id": str(a.user_id),
            "activity_type": a.activity_type,
            "activity_data": a.activity_data,
            "latitude": a.latitude,
            "longitude": a.longitude,
            "captured_at": a.captured_at.isoformat() if a.captured_at else None,
            "trust_score": a.trust_score,
            "status": a.status,
            "image_url": a.image_url,
        }
        for a in activities
    ]

    export_id = str(uuid.uuid4())
    webhook_status = None

    # Send to webhook if URL provided
    if payload.webhook_url:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    payload.webhook_url,
                    json={"export_id": export_id, "data": export_data_list},
                    headers={"Content-Type": "application/json"},
                )
                webhook_status = f"delivered ({resp.status_code})"
        except Exception as e:
            webhook_status = f"failed: {str(e)}"

    return ExportResponse(
        export_id=export_id,
        record_count=len(export_data_list),
        format=payload.format,
        data=export_data_list if payload.format == "json" else None,
        webhook_status=webhook_status,
    )


# =============================================================================
# GET /api/v1/export/schema — Get export data schema
# =============================================================================
@router.get(
    "/schema",
    summary="Get export data schema documentation",
)
async def get_export_schema(user: User = Depends(require_admin)):
    """Returns the schema documentation for exported data."""
    return {
        "version": "1.0",
        "description": "VeriField Nexus activity export schema",
        "fields": {
            "id": {"type": "uuid", "description": "Activity unique identifier"},
            "user_id": {"type": "uuid", "description": "Submitting user ID"},
            "activity_type": {"type": "string", "enum": ["cooking", "farming", "energy", "sustainability", "other"]},
            "activity_data": {"type": "object", "description": "Type-specific structured data"},
            "latitude": {"type": "float", "description": "GPS latitude"},
            "longitude": {"type": "float", "description": "GPS longitude"},
            "captured_at": {"type": "datetime", "format": "ISO 8601"},
            "trust_score": {"type": "float", "range": "0-100"},
            "status": {"type": "string", "enum": ["verified", "review", "flagged", "pending"]},
            "image_url": {"type": "string", "description": "Photo evidence URL"},
        },
    }
