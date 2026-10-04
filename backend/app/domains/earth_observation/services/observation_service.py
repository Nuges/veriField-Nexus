"""
=============================================================================
VeriField Nexus — Earth Observation Ingestion & Observation Service
=============================================================================
Manages the ingestion, discovery, and retrieval of satellite observations:
- Queries providers for candidate scenes intersecting an AOI.
- Ingests scene metadata into EOObservation with full SHA-256 cryptographic provenance.
- Evaluates atmospheric cloud cover QA states (USABLE, PARTIALLY_USABLE, CLOUD_OBSCURED).
- Creates an audit record in EOProcessingRun for every ingestion operation.
- Enforces multi-tenant isolation by organization_id and project_id.
=============================================================================
"""

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from geoalchemy2.shape import from_shape
from app.domains.earth_observation.models import (
    EOAreaOfInterest,
    EOObservation,
    EOProcessingRun,
    EOQualityStatus,
)
from app.domains.earth_observation.provenance import generate_scene_provenance_hash
from app.domains.earth_observation.providers.base import RawSceneMetadata
from app.domains.earth_observation.providers.registry import (
    ProviderRegistry,
    get_default_provider_registry,
)
from app.domains.earth_observation.services.geospatial_engine import geospatial_engine

logger = logging.getLogger(__name__)


class ObservationService:
    """
    Service handling discovery, ingestion, and querying of Earth Observation scenes.
    """

    def __init__(self, provider_registry: Optional[ProviderRegistry] = None):
        self._registry = provider_registry or get_default_provider_registry()

    def set_provider_registry(self, registry: ProviderRegistry) -> None:
        """Sets active provider registry (used for test harness configuration)."""
        self._registry = registry

    def search_scenes(
        self,
        bounding_box: List[float],
        date_from: datetime,
        date_to: datetime,
        provider_code: Optional[str] = None,
        max_cloud_cover: float = 30.0,
    ) -> List[RawSceneMetadata]:
        """
        Queries registered satellite providers for candidate scenes.
        Returns empty list if provider is not configured.
        """
        results: List[RawSceneMetadata] = []
        providers = (
            [self._registry.get_provider(provider_code)]
            if provider_code and self._registry.get_provider(provider_code)
            else self._registry.list_providers()
        )

        for provider in providers:
            if not provider:
                continue
            scenes = provider.search_scenes(
                bounding_box=bounding_box,
                date_from=date_from,
                date_to=date_to,
                max_cloud_cover=max_cloud_cover,
            )
            results.extend(scenes)

        return results

    def evaluate_cloud_qa(
        self,
        cloud_cover_pct: Optional[float],
        policy_id: str = "DEFAULT_OPTICAL_QA_V1",
        policy_version: str = "1.0.0",
        cloud_obscured_threshold: float = 50.0,
        partially_usable_threshold: float = 20.0,
    ) -> Tuple[EOQualityStatus, Dict[str, Any]]:
        """
        Auditable, configurable policy-driven atmospheric cloud cover QA evaluation.
        Persists quality_policy_id, version, thresholds, evaluation timestamp.
        Allows methodology overrides for specific project requirements.
        """
        if cloud_cover_pct is None:
            return EOQualityStatus.USABLE, {
                "quality_policy_id": policy_id,
                "policy_version": policy_version,
                "cloud_cover_pct": None,
                "qa_determination": "NO_CLOUD_METRIC_REPORTED",
                "evaluated_at": datetime.now(timezone.utc).isoformat(),
            }

        if cloud_cover_pct > cloud_obscured_threshold:
            status = EOQualityStatus.CLOUD_OBSCURED
        elif cloud_cover_pct > partially_usable_threshold:
            status = EOQualityStatus.PARTIALLY_USABLE
        else:
            status = EOQualityStatus.USABLE

        flags = {
            "quality_policy_id": policy_id,
            "policy_version": policy_version,
            "cloud_cover_pct": cloud_cover_pct,
            "thresholds": {
                "cloud_obscured_threshold": cloud_obscured_threshold,
                "partially_usable_threshold": partially_usable_threshold,
            },
            "qa_status": status.value,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }
        return status, flags

    async def ingest_observation(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        raw_scene: RawSceneMetadata,
        aoi: Optional[EOAreaOfInterest] = None,
        is_baseline: bool = False,
        baseline_notes: Optional[str] = None,
        quality_policy_id: str = "DEFAULT_OPTICAL_QA_V1",
        cloud_obscured_threshold: float = 50.0,
        partially_usable_threshold: float = 20.0,
    ) -> EOObservation:
        """
        Persists a verified satellite observation scene with full cryptographic provenance
        and authoritative PostGIS spatial footprint.
        """
        start_time = time.time()

        # Check for existing observation of this scene in this project
        stmt = select(EOObservation).where(
            EOObservation.project_id == project_id,
            EOObservation.scene_id == raw_scene.scene_id,
        )
        existing = (await db.execute(stmt)).scalars().first()
        if existing:
            logger.info("Observation for scene %s already exists. Returning existing.", raw_scene.scene_id)
            return existing

        # Determine cloud quality status via configurable QA policy
        if raw_scene.quality_status in (EOQualityStatus.NO_DATA, EOQualityStatus.PROCESSING_FAILED):
            quality_status = raw_scene.quality_status
            qa_flags = {"quality_policy_id": quality_policy_id, "qa_status": quality_status.value}
        else:
            quality_status, qa_flags = self.evaluate_cloud_qa(
                raw_scene.cloud_cover_pct,
                policy_id=quality_policy_id,
                cloud_obscured_threshold=cloud_obscured_threshold,
                partially_usable_threshold=partially_usable_threshold,
            )

        merged_quality_flags = {**(raw_scene.quality_flags or {}), **qa_flags}

        # Generate cryptographic provenance hash
        provenance_hash = generate_scene_provenance_hash(
            provider=raw_scene.provider_code,
            scene_id=raw_scene.scene_id,
            acquisition_timestamp=raw_scene.acquisition_timestamp,
            spatial_resolution_m=raw_scene.spatial_resolution_m,
            processing_level=raw_scene.processing_level,
            bounding_box=raw_scene.bounding_box,
            indices_summary=None,
            raw_band_checksums=raw_scene.raw_band_checksums,
        )

        bbox_dict = {
            "min_lon": raw_scene.bounding_box[0],
            "min_lat": raw_scene.bounding_box[1],
            "max_lon": raw_scene.bounding_box[2],
            "max_lat": raw_scene.bounding_box[3],
        }

        # Authoritative PostGIS footprint geometry
        footprint_shape = geospatial_engine.geometry_to_shape(raw_scene.geometry_geojson)
        footprint_wkb = from_shape(footprint_shape, srid=4326)

        observation = EOObservation(
            organization_id=organization_id,
            project_id=project_id,
            aoi_id=aoi.id if aoi else None,
            boundary_version_id=aoi.boundary_version_id if aoi else None,
            provider_code=raw_scene.provider_code,
            platform=raw_scene.platform,
            sensor=raw_scene.sensor,
            product_code=raw_scene.product_code,
            scene_id=raw_scene.scene_id,
            acquisition_timestamp=raw_scene.acquisition_timestamp,
            processing_timestamp=datetime.now(timezone.utc),
            spatial_resolution_m=raw_scene.spatial_resolution_m,
            cloud_cover_pct=raw_scene.cloud_cover_pct,
            crs="EPSG:4326",
            geometry_geojson=raw_scene.geometry_geojson,
            footprint_geom=footprint_wkb,
            bbox=bbox_dict,
            observation_type=raw_scene.observation_type.value,
            processing_level=raw_scene.processing_level,
            processing_version="1.0.0",
            quality_status=quality_status.value,
            quality_flags=merged_quality_flags,
            raw_band_uris=raw_scene.raw_band_uris,
            raw_band_checksums=raw_scene.raw_band_checksums,
            asset_uri=raw_scene.asset_uri,
            provenance_hash=provenance_hash,
            lineage_manifest=raw_scene.lineage_manifest,
            is_baseline=is_baseline,
            baseline_notes=baseline_notes,
        )
        db.add(observation)
        await db.flush()

        # Audit run
        exec_ms = int((time.time() - start_time) * 1000)
        audit_run = EOProcessingRun(
            organization_id=organization_id,
            project_id=project_id,
            run_type="INGESTION",
            status="COMPLETED",
            parameters={
                "scene_id": raw_scene.scene_id,
                "provider": raw_scene.provider_code,
                "is_baseline": is_baseline,
            },
            input_observation_ids=[str(observation.id)],
            output_layer_ids=[],
            execution_time_ms=exec_ms,
            provenance_hash=provenance_hash,
        )
        db.add(audit_run)
        await db.commit()
        await db.refresh(observation)

        logger.info(
            "Ingested observation %s (Scene: %s, ProvHash: %s...)",
            observation.id,
            observation.scene_id,
            provenance_hash[:12],
        )
        return observation

    async def list_observations(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        aoi_id: Optional[uuid.UUID] = None,
        is_baseline: Optional[bool] = None,
        provider_code: Optional[str] = None,
        limit: int = 100,
    ) -> List[EOObservation]:
        """
        Lists observations matching filter criteria within the organization.
        """
        stmt = (
            select(EOObservation)
            .where(
                EOObservation.project_id == project_id,
                EOObservation.organization_id == organization_id,
            )
            .order_by(desc(EOObservation.acquisition_timestamp))
        )
        if aoi_id:
            stmt = stmt.where(EOObservation.aoi_id == aoi_id)
        if is_baseline is not None:
            stmt = stmt.where(EOObservation.is_baseline == is_baseline)
        if provider_code:
            stmt = stmt.where(EOObservation.provider_code == provider_code)

        stmt = stmt.limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_observation_by_id(
        self,
        db: AsyncSession,
        observation_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> Optional[EOObservation]:
        """
        Fetches single observation by primary key.
        """
        stmt = select(EOObservation).where(
            EOObservation.id == observation_id,
            EOObservation.organization_id == organization_id,
        )
        result = await db.execute(stmt)
        return result.scalars().first()


observation_service = ObservationService()
