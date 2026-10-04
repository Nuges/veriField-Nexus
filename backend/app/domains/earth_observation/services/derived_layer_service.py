"""
=============================================================================
VeriField Nexus — Earth Observation Derived Layer Service
=============================================================================
Computes and registers verified spectral and spatial derived layers from observations:
- NDVI (Normalized Difference Vegetation Index): Rouse et al. (1974)
- EVI (Enhanced Vegetation Index): Huete et al. (2002)
- NDWI Gao (1996): Canopy/Vegetation liquid water
- NDWI McFeeters (1996): Open water body delineation
- SAR Backscatter (VV/VH): Sentinel-1 radiometric radar backscatter in decibels (dB)

SCIENTIFIC INVARIANTS:
- Satellite spectral index != Carbon. Indices describe canopy reflectance, NOT carbon stock.
- SAR Backscatter is radar reflectivity, NEVER direct "Soil Moisture".
- If no ground sensor network or calibrated model is coupled:
  * SOIL MOISTURE MODEL: NOT_CONFIGURED
  * SOC (Soil Organic Carbon) MODEL: NOT_CONFIGURED
=============================================================================
"""

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.earth_observation.models import (
    EODerivedLayer,
    EOObservation,
    EOQualityStatus,
)
from app.domains.earth_observation.provenance import generate_derived_layer_provenance_hash

logger = logging.getLogger(__name__)


# Formula specifications with unambiguous scientific citations
LAYER_SPECIFICATIONS = {
    "NDVI": {
        "formula_identifier": "NDVI_ROUSE_1974",
        "formula": "(NIR - RED) / (NIR + RED)",
        "band_mapping": {"nir": "B08", "red": "B04"},
        "description": "Normalized Difference Vegetation Index (Canopy greenness/vigor proxy)",
    },
    "EVI": {
        "formula_identifier": "EVI_HUETE_2002",
        "formula": "2.5 * (NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1)",
        "band_mapping": {"nir": "B08", "red": "B04", "blue": "B02"},
        "description": "Enhanced Vegetation Index (High-biomass saturation adjusted)",
    },
    "NDWI_GAO_1996": {
        "formula_identifier": "NDWI_GAO_1996",
        "formula": "(NIR - SWIR) / (NIR + SWIR)",
        "band_mapping": {"nir": "B08", "swir": "B11"},
        "description": "Normalized Difference Water Index (Vegetation canopy liquid water)",
    },
    "NDWI_MCFEETERS_1996": {
        "formula_identifier": "NDWI_MCFEETERS_1996",
        "formula": "(GREEN - NIR) / (GREEN + NIR)",
        "band_mapping": {"green": "B03", "nir": "B08"},
        "description": "Normalized Difference Water Index (Surface open water extent)",
    },
    "SAR_VV_BACKSCATTER": {
        "formula_identifier": "SAR_C_BAND_VV_SIGMA0",
        "formula": "10 * log10(DN^2) + cal_offset",
        "band_mapping": {"vv": "VV"},
        "description": "Sentinel-1 C-band SAR VV Polarized Backscatter (dB). Soil moisture model: NOT_CONFIGURED",
    },
    "SAR_VH_BACKSCATTER": {
        "formula_identifier": "SAR_C_BAND_VH_SIGMA0",
        "formula": "10 * log10(DN^2) + cal_offset",
        "band_mapping": {"vh": "VH"},
        "description": "Sentinel-1 C-band SAR VH Cross-Polarized Backscatter (dB). Soil moisture model: NOT_CONFIGURED",
    },
}


class DerivedLayerService:
    """
    Computes, registers, and tracks derived spectral index layers from satellite observations.
    """

    PROCESSOR_VERSION = "1.0.0"

    def get_layer_specification(self, layer_type: str) -> Optional[Dict[str, Any]]:
        """Returns standard scientific metadata for a layer type."""
        return LAYER_SPECIFICATIONS.get(layer_type)

    async def register_derived_layer(
        self,
        db: AsyncSession,
        observation: EOObservation,
        layer_type: str,
        statistics: Dict[str, float],
        asset_uri: Optional[str] = None,
        custom_band_mapping: Optional[Dict[str, str]] = None,
    ) -> EODerivedLayer:
        """
        Creates an immutable derived layer linked cryptographically to its parent observation.
        """
        spec = self.get_layer_specification(layer_type)
        if not spec:
            raise ValueError(f"Unsupported layer type '{layer_type}'. Available: {list(LAYER_SPECIFICATIONS.keys())}")

        formula_id = spec["formula_identifier"]
        formula_expr = spec["formula"]
        bands = custom_band_mapping or spec["band_mapping"]

        # Compute provenance hash linking observation hash, formula, version, and statistics
        provenance_hash = generate_derived_layer_provenance_hash(
            source_observation_hash=observation.provenance_hash,
            layer_type=layer_type,
            formula_identifier=formula_id,
            processor_version=self.PROCESSOR_VERSION,
            statistics=statistics,
            aoi_id=str(observation.aoi_id or ""),
        )

        # Checksum
        content_repr = f"{observation.id}:{layer_type}:{formula_id}:{json.dumps(statistics, sort_keys=True)}"
        checksum_sha256 = hashlib.sha256(content_repr.encode("utf-8")).hexdigest()

        layer = EODerivedLayer(
            organization_id=observation.organization_id,
            project_id=observation.project_id,
            observation_id=observation.id,
            aoi_id=observation.aoi_id,
            layer_type=layer_type,
            formula_identifier=formula_id,
            formula=formula_expr,
            band_mapping=bands,
            processor_version=self.PROCESSOR_VERSION,
            spatial_resolution_m=observation.spatial_resolution_m,
            statistics=statistics,
            asset_uri=asset_uri or f"derived://{observation.project_id}/{observation.scene_id}/{layer_type.lower()}.tif",
            checksum_sha256=checksum_sha256,
            quality_status=observation.quality_status,
            provenance_hash=provenance_hash,
        )
        db.add(layer)
        await db.commit()
        await db.refresh(layer)

        logger.info(
            "Registered derived layer %s (Type: %s, ProvHash: %s...)",
            layer.id,
            layer_type,
            provenance_hash[:12],
        )
        return layer

    async def list_derived_layers(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        observation_id: Optional[uuid.UUID] = None,
        layer_type: Optional[str] = None,
    ) -> List[EODerivedLayer]:
        """
        Queries derived layers for a project or observation.
        """
        stmt = (
            select(EODerivedLayer)
            .where(
                EODerivedLayer.project_id == project_id,
                EODerivedLayer.organization_id == organization_id,
            )
            .order_by(desc(EODerivedLayer.created_at))
        )
        if observation_id:
            stmt = stmt.where(EODerivedLayer.observation_id == observation_id)
        if layer_type:
            stmt = stmt.where(EODerivedLayer.layer_type == layer_type)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_derived_layer(
        self,
        db: AsyncSession,
        layer_id: uuid.UUID,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> Optional[EODerivedLayer]:
        """
        Retrieves a single derived layer by ID within tenant authorization boundaries.
        """
        stmt = select(EODerivedLayer).where(
            EODerivedLayer.id == layer_id,
            EODerivedLayer.project_id == project_id,
            EODerivedLayer.organization_id == organization_id,
        )
        return (await db.execute(stmt)).scalars().first()


derived_layer_service = DerivedLayerService()
