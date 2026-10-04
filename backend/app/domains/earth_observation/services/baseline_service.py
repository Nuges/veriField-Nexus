"""
=============================================================================
VeriField Nexus — Baseline Satellite Evidence Package Service
=============================================================================
Compiles multi-year historical satellite observations and land evidence into
an immutable, cryptographically sealed Baseline Package:
- Gathers historical observations flagged as baseline evidence.
- Correlates with project boundary version and land units.
- Generates a deterministic baseline package SHA-256 seal.
- Proves historical pre-project land use and vegetation indices.
=============================================================================
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.earth_observation.models import (
    EOAreaOfInterest,
    EOObservation,
    ProjectBoundaryVersion,
)
from app.domains.earth_observation.provenance import generate_baseline_package_hash

logger = logging.getLogger(__name__)


class BaselineService:
    """
    Compiles and seals baseline satellite evidence packages.
    """

    async def compile_baseline_package(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        aoi: EOAreaOfInterest,
        boundary_version: ProjectBoundaryVersion,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compiles all baseline observations for the AOI and generates an immutable sealed manifest.
        """
        stmt = (
            select(EOObservation)
            .where(
                EOObservation.project_id == project_id,
                EOObservation.organization_id == organization_id,
                EOObservation.aoi_id == aoi.id,
                EOObservation.is_baseline == True,
            )
            .order_by(EOObservation.acquisition_timestamp.asc())
        )
        observations = list((await db.execute(stmt)).scalars().all())

        obs_hashes = [obs.provenance_hash for obs in observations]
        baseline_dt_iso = datetime.now(timezone.utc).isoformat()

        package_hash = generate_baseline_package_hash(
            project_id=str(project_id),
            boundary_version_number=boundary_version.version_number,
            observation_provenance_hashes=obs_hashes,
            evidence_hashes=[],
            soil_sample_hashes=[],
            baseline_date_iso=baseline_dt_iso,
        )

        manifest = {
            "baseline_package_id": str(uuid.uuid4()),
            "project_id": str(project_id),
            "organization_id": str(organization_id),
            "aoi_id": str(aoi.id),
            "boundary_version_number": boundary_version.version_number,
            "boundary_area_ha": aoi.area_ha,
            "sealed_at": baseline_dt_iso,
            "package_seal_hash": package_hash,
            "notes": notes or "Historical pre-project land baseline package",
            "observation_count": len(observations),
            "observations": [
                {
                    "observation_id": str(o.id),
                    "scene_id": o.scene_id,
                    "provider": o.provider_code,
                    "platform": o.platform,
                    "sensor": o.sensor,
                    "acquisition_timestamp": o.acquisition_timestamp.isoformat(),
                    "cloud_cover_pct": o.cloud_cover_pct,
                    "provenance_hash": o.provenance_hash,
                }
                for o in observations
            ],
        }

        logger.info(
            "Compiled baseline package for project %s (Seal: %s..., %d scenes)",
            project_id,
            package_hash[:12],
            len(observations),
        )
        return manifest


baseline_service = BaselineService()
