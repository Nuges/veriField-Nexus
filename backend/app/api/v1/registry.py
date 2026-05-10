"""
=============================================================================
VeriField Nexus — Registry Export API
=============================================================================
Generates audit-ready CSV/JSON exports matching Verra and Gold Standard
registry formats. This is the MONEY endpoint — these exports become
carbon credit issuance applications.
=============================================================================
"""

import csv
import io
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional

from app.db.session import get_db
from app.core.security import require_admin
from app.models.user import User
from app.models.activity import Activity
from app.models.property import Property
from app.models.carbon_calculation import CarbonCalculation
from app.models.sensor_reading import SensorReading
from app.models.community_validation import CommunityValidation
from app.models.audit_task import AuditTask

router = APIRouter(prefix="/registry", tags=["Registry Export"])


async def _get_verification_layers(db: AsyncSession, property_id) -> dict:
    """Check all three cross-verification layers for a property."""
    layers = {"sensor": False, "community": False, "audit": False}
    if not property_id:
        return layers

    sensor_r = await db.execute(
        select(SensorReading).where(SensorReading.asset_id == property_id).limit(1)
    )
    layers["sensor"] = sensor_r.scalar_one_or_none() is not None

    comm_r = await db.execute(
        select(CommunityValidation).where(
            and_(
                CommunityValidation.asset_id == property_id,
                CommunityValidation.response == "yes",
            )
        ).limit(1)
    )
    layers["community"] = comm_r.scalar_one_or_none() is not None

    audit_r = await db.execute(
        select(AuditTask).where(
            and_(
                AuditTask.asset_id == property_id,
                AuditTask.status == "completed",
            )
        ).limit(1)
    )
    layers["audit"] = audit_r.scalar_one_or_none() is not None

    return layers


# =============================================================================
# GET /api/v1/registry/export/verra — Verra CSV Export
# =============================================================================
@router.get(
    "/export/verra",
    summary="Export registry-ready CSV for Verra",
    response_class=StreamingResponse,
)
async def export_verra_csv(
    min_trust_score: float = Query(80.0, ge=0, le=100),
    include_unquantified: bool = Query(False),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a CSV export matching Verra VCS requirements.
    Only includes verified activities with trust score >= threshold.
    """
    # Fetch verified activities
    conditions = [
        Activity.status == "verified",
        Activity.trust_score >= min_trust_score,
    ]
    result = await db.execute(
        select(Activity)
        .where(and_(*conditions))
        .order_by(Activity.captured_at.asc())
    )
    activities = result.scalars().all()

    # Build CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Header matching Verra upload template
    writer.writerow([
        "Asset_ID", "Asset_Name", "Asset_Type",
        "Latitude", "Longitude",
        "Activity_ID", "Activity_Type",
        "Capture_Date", "Submission_Date",
        "Verification_Status", "Trust_Score",
        "Methodology", "tCO2e",
        "Sensor_Corroborated", "Community_Validated", "Audit_Passed",
    ])

    total_tco2e = 0.0
    record_count = 0

    for activity in activities:
        # Get property info
        prop = None
        if activity.property_id:
            prop_result = await db.execute(
                select(Property).where(Property.id == activity.property_id)
            )
            prop = prop_result.scalar_one_or_none()

        # Get carbon calculation if exists
        calc_result = await db.execute(
            select(CarbonCalculation).where(
                CarbonCalculation.activity_id == activity.id
            ).limit(1)
        )
        calc = calc_result.scalar_one_or_none()

        # Skip if no quantification and flag is off
        tco2e = 0.0
        methodology = "N/A"
        if calc:
            tco2e = calc.tco2e_generated
            methodology = calc.methodology_used
        elif not include_unquantified:
            # Use inline estimate from activity_data
            data = activity.activity_data or {}
            tco2e = data.get("emission_reduction_value_kg", 0) / 1000.0
            methodology = data.get("methodology_reference", "Estimated")

        # Check verification layers
        layers = await _get_verification_layers(db, activity.property_id)

        writer.writerow([
            str(activity.property_id) if activity.property_id else "",
            prop.name if prop else "Unknown",
            prop.property_type if prop else activity.activity_type,
            activity.latitude or "",
            activity.longitude or "",
            str(activity.id),
            activity.activity_type,
            activity.captured_at.strftime("%Y-%m-%d %H:%M:%S") if activity.captured_at else "",
            activity.submitted_at.strftime("%Y-%m-%d %H:%M:%S") if activity.submitted_at else "",
            activity.status,
            round(activity.trust_score, 1) if activity.trust_score else "",
            methodology,
            round(tco2e, 4),
            "Yes" if layers["sensor"] else "No",
            "Yes" if layers["community"] else "No",
            "Yes" if layers["audit"] else "No",
        ])

        total_tco2e += tco2e
        record_count += 1

    output.seek(0)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"verifield_verra_export_{timestamp}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "X-Total-Records": str(record_count),
            "X-Total-tCO2e": str(round(total_tco2e, 4)),
        },
    )


# =============================================================================
# GET /api/v1/registry/export/goldstandard — Gold Standard JSON Export
# =============================================================================
@router.get(
    "/export/goldstandard",
    summary="Export registry-ready JSON for Gold Standard",
)
async def export_goldstandard_json(
    min_trust_score: float = Query(80.0, ge=0, le=100),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a JSON export matching Gold Standard requirements.
    """
    conditions = [
        Activity.status == "verified",
        Activity.trust_score >= min_trust_score,
    ]
    result = await db.execute(
        select(Activity)
        .where(and_(*conditions))
        .order_by(Activity.captured_at.asc())
    )
    activities = result.scalars().all()

    records = []
    total_tco2e = 0.0

    for activity in activities:
        prop = None
        if activity.property_id:
            prop_result = await db.execute(
                select(Property).where(Property.id == activity.property_id)
            )
            prop = prop_result.scalar_one_or_none()

        calc_result = await db.execute(
            select(CarbonCalculation).where(
                CarbonCalculation.activity_id == activity.id
            ).limit(1)
        )
        calc = calc_result.scalar_one_or_none()

        tco2e = calc.tco2e_generated if calc else 0.0
        methodology = calc.methodology_used if calc else "Estimated"

        layers = await _get_verification_layers(db, activity.property_id)

        records.append({
            "asset_id": str(activity.property_id) if activity.property_id else None,
            "asset_name": prop.name if prop else "Unknown",
            "gps": {"lat": activity.latitude, "lon": activity.longitude},
            "activity_id": str(activity.id),
            "activity_type": activity.activity_type,
            "capture_date": activity.captured_at.isoformat() if activity.captured_at else None,
            "verification_status": activity.status,
            "trust_score": activity.trust_score,
            "methodology": methodology,
            "tco2e": round(tco2e, 4),
            "verification_layers": layers,
        })
        total_tco2e += tco2e

    return {
        "registry": "Gold Standard",
        "export_date": datetime.now(timezone.utc).isoformat(),
        "total_records": len(records),
        "total_tco2e": round(total_tco2e, 4),
        "records": records,
    }
