"""
=============================================================================
VeriField Nexus — Agriculture Earth Observation Bridge
=============================================================================
Re-exports the centralized Earth Observation domain components for full
backward compatibility across the Agriculture & Land Use sector, while
preserving all existing agriculture-specific interfaces.
=============================================================================
"""

# Re-export existing agriculture-specific EO classes for 100% backward compatibility
from app.domains.agriculture.earth_observation.base import (
    EarthObservationProvider,
    EOProviderType,
    ObservationType,
    SceneMetadata,
)
from app.domains.agriculture.earth_observation.commercial import (
    PlanetScopeProvider,
    SkySatProvider,
)
from app.domains.agriculture.earth_observation.landsat import LandsatProvider
from app.domains.agriculture.earth_observation.provenance import (
    generate_scene_provenance_hash,
)
from app.domains.agriculture.earth_observation.sentinel import (
    Sentinel1Provider,
    Sentinel2Provider,
)

# Re-export centralized shared domain components
from app.domains.earth_observation import (
    AOIResponse,
    BoundarySetRequest,
    EOAnomalyStatus,
    EOAreaOfInterest,
    EODerivedLayer,
    EOObservation,
    EOObservationType,
    EOProcessingRun,
    EOProduct,
    EOProvider,
    EOProviderCapability,
    EOQualityStatus,
    EOSpatialAnomaly,
    EOSpatialAnomalyType,
    ProjectBoundaryVersion,
    anomaly_service,
    aoi_service,
    baseline_service,
    derived_layer_service,
    earth_observation_router,
    geospatial_engine,
    manifest_service,
    observation_service,
)

__all__ = [
    # Legacy Agriculture EO Exports
    "EarthObservationProvider",
    "EOProviderType",
    "ObservationType",
    "SceneMetadata",
    "generate_scene_provenance_hash",
    "Sentinel2Provider",
    "Sentinel1Provider",
    "LandsatProvider",
    "PlanetScopeProvider",
    "SkySatProvider",
    # Shared Centralized EO Domain Exports
    "EOProviderCapability",
    "EOObservationType",
    "EOQualityStatus",
    "EOSpatialAnomalyType",
    "EOAnomalyStatus",
    "ProjectBoundaryVersion",
    "EOAreaOfInterest",
    "EOProvider",
    "EOProduct",
    "EOObservation",
    "EODerivedLayer",
    "EOProcessingRun",
    "EOSpatialAnomaly",
    "geospatial_engine",
    "aoi_service",
    "observation_service",
    "derived_layer_service",
    "anomaly_service",
    "baseline_service",
    "manifest_service",
    "earth_observation_router",
]
