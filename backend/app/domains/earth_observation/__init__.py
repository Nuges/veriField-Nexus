"""
=============================================================================
VeriField Nexus — Centralized Earth Observation Domain Package
=============================================================================
"""

from app.domains.earth_observation.models import (
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
)
from app.domains.earth_observation.provenance import (
    generate_baseline_package_hash,
    generate_derived_layer_provenance_hash,
    generate_scene_provenance_hash,
)
from app.domains.earth_observation.providers import (
    CommercialSatelliteProvider,
    EarthObservationProvider,
    LandsatProvider,
    ProviderRegistry,
    RawSceneMetadata,
    Sentinel1Provider,
    Sentinel2Provider,
    default_registry,
    get_default_provider_registry,
)
from app.domains.earth_observation.schemas import (
    AnomalyCorroborateRequest,
    AnomalyResponse,
    AOIResponse,
    BaselinePackageCreateRequest,
    BaselinePackageResponse,
    BoundarySetRequest,
    DerivedLayerComputeRequest,
    DerivedLayerResponse,
    ObservationIngestRequest,
    ObservationResponse,
    ProjectBoundaryVersionResponse,
    ProviderCapabilityInfo,
    ProviderMatrixResponse,
    RawSceneResponse,
    SceneSearchRequest,
)
from app.domains.earth_observation.services import (
    AnomalyService,
    AOIService,
    BaselineService,
    DerivedLayerService,
    GeospatialEngine,
    LAYER_SPECIFICATIONS,
    ManifestService,
    ObservationService,
    SpatialBackendState,
    anomaly_service,
    aoi_service,
    baseline_service,
    derived_layer_service,
    geospatial_engine,
    manifest_service,
    observation_service,
)

__all__ = [
    # Models & Enums
    "SpatialBackendState",
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
    # Provenance
    "generate_scene_provenance_hash",
    "generate_derived_layer_provenance_hash",
    "generate_baseline_package_hash",
    # Providers
    "EarthObservationProvider",
    "RawSceneMetadata",
    "Sentinel2Provider",
    "Sentinel1Provider",
    "LandsatProvider",
    "CommercialSatelliteProvider",
    "ProviderRegistry",
    "default_registry",
    "get_default_provider_registry",
    # Services
    "GeospatialEngine",
    "geospatial_engine",
    "AOIService",
    "aoi_service",
    "ObservationService",
    "observation_service",
    "DerivedLayerService",
    "derived_layer_service",
    "LAYER_SPECIFICATIONS",
    "AnomalyService",
    "anomaly_service",
    "BaselineService",
    "baseline_service",
    "ManifestService",
    "manifest_service",
    # Router
    "earth_observation_router",
]


def __getattr__(name: str):
    if name == "earth_observation_router":
        from app.domains.earth_observation.api import router
        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
