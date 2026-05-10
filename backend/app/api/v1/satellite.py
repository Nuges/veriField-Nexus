"""
=============================================================================
VeriField Nexus — Satellite NDVI API
=============================================================================
Endpoints for satellite-based vegetation monitoring.
=============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import Optional

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.ndvi_record import NdviRecord
from app.services.satellite_service import SatelliteService

router = APIRouter(prefix="/satellite", tags=["Satellite NDVI"])


# =============================================================================
# POST /api/v1/satellite/ndvi/{asset_id} — Fetch NDVI for an asset
# =============================================================================
@router.post(
    "/ndvi/{asset_id}",
    summary="Fetch NDVI for an asset",
)
async def fetch_ndvi(
    asset_id: UUID,
    month: Optional[str] = Query(None, description="Target month YYYY-MM"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch or compute NDVI score for an asset from Sentinel-2 data.
    Results are cached — re-requesting the same month returns cached data.
    """
    service = SatelliteService(db)
    try:
        result = await service.fetch_ndvi_for_asset(asset_id, month)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# GET /api/v1/satellite/ndvi/{asset_id}/history — NDVI history for an asset
# =============================================================================
@router.get(
    "/ndvi/{asset_id}/history",
    summary="Get NDVI history for an asset",
)
async def get_ndvi_history(
    asset_id: UUID,
    limit: int = Query(12, ge=1, le=60),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get historical NDVI records for an asset (most recent first)."""
    result = await db.execute(
        select(NdviRecord)
        .where(NdviRecord.asset_id == asset_id)
        .order_by(NdviRecord.observation_date.desc())
        .limit(limit)
    )
    records = result.scalars().all()

    return {
        "asset_id": str(asset_id),
        "records": [
            {
                "ndvi_score": r.ndvi_score,
                "trend": r.trend,
                "observation_date": r.observation_date,
                "source": r.source,
            }
            for r in records
        ],
        "count": len(records),
    }
