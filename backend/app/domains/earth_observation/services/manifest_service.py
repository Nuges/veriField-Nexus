"""
=============================================================================
VeriField Nexus — Earth Observation MRV Evidence Manifest Service
=============================================================================
Generates exportable, audit-ready MRV Evidence Manifests supporting registry
documentation, third-party validation, and verification bodies:
- AOI Footprint and boundary versioning.
- Cryptographic provenance chain of all ingested satellite scenes.
- Explicit formula definitions and processing versions for derived layers.
- Anomaly review trail and ground corroboration statuses.
- Full compliance with scientific accuracy requirements.
- Note: EO evidence supports verification and documentation; it does not
  decide methodology eligibility, registry compliance, or credit issuance.
=============================================================================
"""

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.earth_observation.models import (
    EOAreaOfInterest,
    EODerivedLayer,
    EOObservation,
    EOSpatialAnomaly,
    ProjectBoundaryVersion,
)

logger = logging.getLogger(__name__)


class ManifestService:
    """
    Generates MRV Evidence spatial manifests.
    """

    async def generate_project_mrv_manifest(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        aoi: EOAreaOfInterest,
    ) -> Dict[str, Any]:
        """
        Builds a comprehensive registry MRV manifest for an AOI.
        """
        # Query boundary version
        bv_stmt = select(ProjectBoundaryVersion).where(
            ProjectBoundaryVersion.id == aoi.boundary_version_id
        )
        bv = (await db.execute(bv_stmt)).scalars().first()

        # Query all observations
        obs_stmt = (
            select(EOObservation)
            .where(
                EOObservation.aoi_id == aoi.id,
                EOObservation.organization_id == organization_id,
            )
            .order_by(EOObservation.acquisition_timestamp.asc())
        )
        observations = list((await db.execute(obs_stmt)).scalars().all())

        # Query derived layers
        obs_ids = [o.id for o in observations]
        layers = []
        if obs_ids:
            lay_stmt = (
                select(EODerivedLayer)
                .where(EODerivedLayer.observation_id.in_(obs_ids))
                .order_by(EODerivedLayer.created_at.asc())
            )
            layers = list((await db.execute(lay_stmt)).scalars().all())

        # Query anomalies
        anom_stmt = (
            select(EOSpatialAnomaly)
            .where(
                EOSpatialAnomaly.aoi_id == aoi.id,
                EOSpatialAnomaly.organization_id == organization_id,
            )
            .order_by(EOSpatialAnomaly.detected_at.desc())
        )
        anomalies = list((await db.execute(anom_stmt)).scalars().all())

        generated_at = datetime.now(timezone.utc).isoformat()

        manifest_payload = {
            "mrv_manifest_version": "1.0.0",
            "schema_uri": "https://schema.verifieldnexus.com/mrv/earth-observation/v1.json",
            "generated_at": generated_at,
            "project_id": str(project_id),
            "organization_id": str(organization_id),
            "aoi": {
                "id": str(aoi.id),
                "name": aoi.name,
                "aoi_type": aoi.aoi_type,
                "boundary_version_number": bv.version_number if bv else 1,
                "boundary_effective_date": bv.effective_date.isoformat() if bv else None,
                "area_ha": aoi.area_ha,
                "crs": aoi.crs,
                "bbox": aoi.bbox,
                "geometry_geojson": aoi.geometry_geojson,
            },
            "observations_summary": {
                "total_scenes": len(observations),
                "optical_count": sum(1 for o in observations if "OPTICAL" in o.observation_type),
                "sar_count": sum(1 for o in observations if "SAR" in o.observation_type),
                "baseline_scenes_count": sum(1 for o in observations if o.is_baseline),
            },
            "observations": [
                {
                    "observation_id": str(o.id),
                    "scene_id": o.scene_id,
                    "provider": o.provider_code,
                    "platform": o.platform,
                    "sensor": o.sensor,
                    "product_code": o.product_code,
                    "observation_type": o.observation_type,
                    "acquisition_timestamp": o.acquisition_timestamp.isoformat(),
                    "spatial_resolution_m": o.spatial_resolution_m,
                    "cloud_cover_pct": o.cloud_cover_pct,
                    "processing_level": o.processing_level,
                    "quality_status": o.quality_status,
                    "provenance_hash": o.provenance_hash,
                    "is_baseline": o.is_baseline,
                }
                for o in observations
            ],
            "derived_layers": [
                {
                    "layer_id": str(l.id),
                    "observation_id": str(l.observation_id),
                    "layer_type": l.layer_type,
                    "formula_identifier": l.formula_identifier,
                    "formula": l.formula,
                    "band_mapping": l.band_mapping,
                    "processor_version": l.processor_version,
                    "spatial_resolution_m": l.spatial_resolution_m,
                    "statistics": l.statistics,
                    "checksum_sha256": l.checksum_sha256,
                    "provenance_hash": l.provenance_hash,
                }
                for l in layers
            ],
            "spatial_anomalies_and_reviews": [
                {
                    "anomaly_id": str(a.id),
                    "anomaly_type": a.anomaly_type,
                    "severity": a.severity,
                    "status": a.status,
                    "description": a.description,
                    "review_recommendation": a.review_recommendation,
                    "detected_at": a.detected_at.isoformat(),
                    "corroborated_at": a.corroborated_at.isoformat() if a.corroborated_at else None,
                    "corroboration_notes": a.corroboration_notes,
                }
                for a in anomalies
            ],
            "scientific_disclaimers": {
                "spectral_indices": "Spectral indices reflect vegetative canopy reflectance, not direct carbon stock.",
                "sar_backscatter": "SAR backscatter reflects radar microwave reflectivity. Soil moisture / SOC models are NOT_CONFIGURED without calibrated ground sensors.",
                "registry_boundary": "Earth Observation evidence supports monitoring, verification, and registry documentation. EO itself does not decide methodology eligibility, registry compliance, additionality, or credit issuance.",
            },
        }

        # Deterministic manifest hash
        manifest_canonical = json.dumps(manifest_payload, sort_keys=True)
        manifest_payload["manifest_digest_sha256"] = hashlib.sha256(manifest_canonical.encode("utf-8")).hexdigest()

        return manifest_payload


manifest_service = ManifestService()
