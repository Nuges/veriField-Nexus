"""
=============================================================================
VeriField Nexus — Earth Observation Spatial Anomaly & Review Service
=============================================================================
Detects and tracks spatial and spectral change signals across temporal observations:
- Strictly adheres to factual, cautious terminology:
  * VEGETATION_INDEX_CHANGE
  * SPECTRAL_CHANGE
  * OBSERVED_WATER_EXTENT_CHANGE
  * LAND_COVER_CHANGE_SIGNAL
  * POSSIBLE_DISTURBANCE
- NEVER outputs unverified claims such as "Deforestation confirmed" or "Degradation verified".
- Every anomaly automatically generates a factual REVIEW_RECOMMENDATION for field auditors.
- Integrates with the VerificationTask workflow for audit tracking.
=============================================================================
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.earth_observation.models import (
    EOAnomalyStatus,
    EOAreaOfInterest,
    EODerivedLayer,
    EOObservation,
    EOSpatialAnomaly,
    EOSpatialAnomalyType,
)

logger = logging.getLogger(__name__)


class AnomalyService:
    """
    Manages detection, logging, and corroboration of spatial change signals.
    """

    async def detect_index_change(
        self,
        db: AsyncSession,
        current_layer: EODerivedLayer,
        baseline_layer: EODerivedLayer,
        threshold_delta: float = -0.15,
        severity: str = "MEDIUM",
    ) -> Optional[EOSpatialAnomaly]:
        """
        Compares summary statistics between current and baseline derived layers.
        If delta exceeds threshold, logs a factual EOSpatialAnomaly with review recommendations.
        """
        curr_mean = current_layer.statistics.get("mean")
        base_mean = baseline_layer.statistics.get("mean")

        if curr_mean is None or base_mean is None:
            return None

        delta = round(curr_mean - base_mean, 4)

        # For vegetation drop (e.g. delta <= -0.15 in NDVI)
        if delta <= threshold_delta:
            description = (
                f"Observed negative spectral shift in {current_layer.layer_type}: "
                f"mean changed from {base_mean:.3f} (baseline) to {curr_mean:.3f} (current), "
                f"delta = {delta:.3f}."
            )
            recommendation = (
                f"Review field activity records and schedule ground inspection to investigate "
                f"observed {current_layer.layer_type} drop ({delta:+.3f}). Corroborate whether "
                f"signal is caused by harvest, seasonal senescence, weather event, or canopy disturbance."
            )

            # Copy authoritative spatial geometry from AOI if available
            anomaly_geom = None
            if current_layer.aoi_id:
                aoi_res = await db.execute(
                    select(EOAreaOfInterest.geom).where(EOAreaOfInterest.id == current_layer.aoi_id)
                )
                anomaly_geom = aoi_res.scalar_one_or_none()

            anomaly = EOSpatialAnomaly(
                organization_id=current_layer.organization_id,
                project_id=current_layer.project_id,
                aoi_id=current_layer.aoi_id,
                observation_id=current_layer.observation_id,
                anomaly_type=EOSpatialAnomalyType.VEGETATION_INDEX_CHANGE.value,
                severity=severity,
                status=EOAnomalyStatus.OBSERVED.value,
                geom=anomaly_geom,
                description=description,
                review_recommendation=recommendation,
                baseline_observation_id=baseline_layer.observation_id,
                comparison_metric=current_layer.layer_type,
                delta_value=delta,
            )
            db.add(anomaly)
            await db.commit()
            await db.refresh(anomaly)

            logger.info("Logged spatial anomaly %s: %s (delta=%.3f)", anomaly.id, anomaly.anomaly_type, delta)
            return anomaly

        return None

    async def corroborate_anomaly(
        self,
        db: AsyncSession,
        anomaly_id: uuid.UUID,
        organization_id: uuid.UUID,
        corroborated: bool,
        notes: str,
        verification_task_id: Optional[uuid.UUID] = None,
        corroborating_activity_id: Optional[uuid.UUID] = None,
    ) -> Optional[EOSpatialAnomaly]:
        """
        Records human auditor or ground-evidence corroboration for an anomaly.
        """
        stmt = select(EOSpatialAnomaly).where(
            EOSpatialAnomaly.id == anomaly_id,
            EOSpatialAnomaly.organization_id == organization_id,
        )
        anomaly = (await db.execute(stmt)).scalars().first()
        if not anomaly:
            return None

        anomaly.status = (
            EOAnomalyStatus.CORROBORATED.value if corroborated else EOAnomalyStatus.DISMISSED.value
        )
        anomaly.corroboration_notes = notes
        anomaly.corroborated_at = datetime.now(timezone.utc)
        if verification_task_id:
            anomaly.verification_task_id = verification_task_id
        if corroborating_activity_id:
            anomaly.corroborating_activity_id = corroborating_activity_id

        await db.commit()
        await db.refresh(anomaly)
        return anomaly

    async def list_anomalies(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        status: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> List[EOSpatialAnomaly]:
        """
        Lists spatial anomalies for a project with status/severity filtering.
        """
        stmt = (
            select(EOSpatialAnomaly)
            .where(
                EOSpatialAnomaly.project_id == project_id,
                EOSpatialAnomaly.organization_id == organization_id,
            )
            .order_by(desc(EOSpatialAnomaly.detected_at))
        )
        if status:
            stmt = stmt.where(EOSpatialAnomaly.status == status)
        if severity:
            stmt = stmt.where(EOSpatialAnomaly.severity == severity)

        result = await db.execute(stmt)
        return list(result.scalars().all())


anomaly_service = AnomalyService()
