"""
=============================================================================
VeriField Nexus — Earth Observation REST API Router
=============================================================================
Endpoints for satellite remote sensing and MRV:
- Provider capability discovery (/providers)
- Project boundary & AOI management (/projects/{project_id}/boundary, /aoi)
- Boundary version audit trail (/projects/{project_id}/boundary-history)
- Scene search and ingestion (/search-scenes, /ingest-observation)
- Derived spectral and radar layers (/derived-layers)
- Spatial anomaly detection and field corroboration (/anomalies)
- Baseline evidence compilation (/baseline-package)
- MRV Evidence Manifest export (/manifest)
=============================================================================
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.core.abac import ABACEngine
from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.authentication.models import User
from app.domains.earth_observation.models import (
    EOObservationType,
    EOQualityStatus,
)
from app.domains.earth_observation.providers.base import RawSceneMetadata
from app.domains.earth_observation.providers.registry import (
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
from app.domains.earth_observation.services.anomaly_service import anomaly_service
from app.domains.earth_observation.services.aoi_service import aoi_service
from app.domains.earth_observation.services.baseline_service import baseline_service
from app.domains.earth_observation.services.derived_layer_service import (
    derived_layer_service,
)
from app.domains.earth_observation.services.manifest_service import manifest_service
from app.domains.earth_observation.services.observation_service import (
    observation_service,
)

router = APIRouter(prefix="/earth-observation", tags=["Earth Observation & Satellite MRV"])


# ─── 1. Provider Capabilities ───

@router.get("/providers", response_model=ProviderMatrixResponse)
async def get_provider_capabilities():
    """
    Returns truthful runtime capability states for all registered satellite providers.
    Does NOT claim live access when credentials are not configured.
    """
    registry = get_default_provider_registry()
    matrix = registry.get_capability_matrix()
    result = {}
    for code, info in matrix.items():
        result[code] = ProviderCapabilityInfo(
            provider_code=info["provider_code"],
            capability=info["capability"],
            is_configured=(info["is_configured"] == "true"),
            granular_capabilities=info.get("granular_capabilities"),
        )
    return ProviderMatrixResponse(providers=result)


# ─── 2. Project Boundary & AOI ───

@router.post(
    "/projects/{project_id}/boundary",
    response_model=AOIResponse,
    status_code=status.HTTP_201_CREATED,
)
async def set_project_boundary(
    project_id: uuid.UUID,
    payload: BoundarySetRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Validates GeoJSON polygon, computes WGS84 geodesic area and perimeter,
    increments the project boundary version, and establishes an active AOI.
    """
    abac = ABACEngine(db, current_user)
    project = await abac.enforce_project_access(project_id)

    try:
        aoi, _ = await aoi_service.set_project_boundary(
            db=db,
            project_id=project_id,
            organization_id=project.organization_id,
            geometry_geojson=payload.geometry_geojson,
            name=payload.name,
            source=payload.source,
            reason=payload.reason,
            user_id=current_user.id,
        )
        return aoi
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/projects/{project_id}/aoi")
async def get_project_active_aoi(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves currently active AOI for the project.
    Truthfully returns status='NO_AOI' if no boundary has been configured.
    """
    abac = ABACEngine(db, current_user)
    project = await abac.enforce_project_access(project_id)

    aoi = await aoi_service.get_project_active_aoi(
        db=db,
        project_id=project_id,
        organization_id=project.organization_id,
    )
    if not aoi:
        return {
            "status": "NO_AOI",
            "message": "Project has no spatial boundary configured.",
            "aoi": None,
        }

    return {
        "status": "CONFIGURED",
        "aoi": AOIResponse.model_validate(aoi),
    }


@router.get(
    "/projects/{project_id}/boundary-history",
    response_model=List[ProjectBoundaryVersionResponse],
)
async def list_boundary_history(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves full historical audit trail of boundary revisions for a project.
    """
    abac = ABACEngine(db, current_user)
    project = await abac.enforce_project_access(project_id)

    history = await aoi_service.list_boundary_history(
        db=db,
        project_id=project_id,
        organization_id=project.organization_id,
    )
    return history


# ─── 3. Satellite Scene Search & Ingestion ───

@router.post("/projects/{project_id}/search-scenes", response_model=List[RawSceneResponse])
async def search_satellite_scenes(
    project_id: uuid.UUID,
    payload: SceneSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Queries candidate scenes intersecting the bounding box.
    Returns empty list if provider credentials are not configured.
    """
    abac = ABACEngine(db, current_user)
    await abac.enforce_project_access(project_id)

    scenes = observation_service.search_scenes(
        bounding_box=payload.bounding_box,
        date_from=payload.date_from,
        date_to=payload.date_to,
        provider_code=payload.provider_code,
        max_cloud_cover=payload.max_cloud_cover,
    )
    return [
        RawSceneResponse(
            scene_id=s.scene_id,
            provider_code=s.provider_code,
            platform=s.platform,
            sensor=s.sensor,
            product_code=s.product_code,
            observation_type=s.observation_type.value,
            acquisition_timestamp=s.acquisition_timestamp,
            spatial_resolution_m=s.spatial_resolution_m,
            bounding_box=s.bounding_box,
            processing_level=s.processing_level,
            cloud_cover_pct=s.cloud_cover_pct,
            quality_status=s.quality_status.value,
        )
        for s in scenes
    ]


@router.post(
    "/projects/{project_id}/ingest-observation",
    response_model=ObservationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_observation(
    project_id: uuid.UUID,
    payload: ObservationIngestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Ingests a satellite observation scene into the database with cryptographic SHA-256 provenance.
    """
    abac = ABACEngine(db, current_user)
    project = await abac.enforce_project_access(project_id)

    aoi = await aoi_service.get_project_active_aoi(
        db=db,
        project_id=project_id,
        organization_id=project.organization_id,
    )

    try:
        obs_type = EOObservationType(payload.observation_type)
    except ValueError:
        obs_type = EOObservationType.OPTICAL_MULTISPECTRAL

    raw_scene = RawSceneMetadata(
        scene_id=payload.scene_id,
        provider_code=payload.provider_code,
        platform=payload.platform,
        sensor=payload.sensor,
        product_code=payload.product_code,
        observation_type=obs_type,
        acquisition_timestamp=payload.acquisition_timestamp,
        spatial_resolution_m=payload.spatial_resolution_m,
        bounding_box=payload.bounding_box,
        geometry_geojson=payload.geometry_geojson,
        processing_level=payload.processing_level,
        cloud_cover_pct=payload.cloud_cover_pct,
        raw_band_uris=payload.raw_band_uris,
        raw_band_checksums=payload.raw_band_checksums,
        asset_uri=payload.asset_uri,
        quality_flags=payload.quality_flags,
        lineage_manifest=payload.lineage_manifest,
    )

    observation = await observation_service.ingest_observation(
        db=db,
        project_id=project_id,
        organization_id=project.organization_id,
        raw_scene=raw_scene,
        aoi=aoi,
        is_baseline=payload.is_baseline,
        baseline_notes=payload.baseline_notes,
    )
    return observation


@router.get("/projects/{project_id}/observations", response_model=List[ObservationResponse])
async def list_observations(
    project_id: uuid.UUID,
    aoi_id: Optional[uuid.UUID] = None,
    is_baseline: Optional[bool] = None,
    provider_code: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists satellite observations matching filter criteria.
    """
    abac = ABACEngine(db, current_user)
    project = await abac.enforce_project_access(project_id)

    observations = await observation_service.list_observations(
        db=db,
        project_id=project_id,
        organization_id=project.organization_id,
        aoi_id=aoi_id,
        is_baseline=is_baseline,
        provider_code=provider_code,
        limit=limit,
    )
    return observations


# ─── 4. Derived Layers (NDVI, EVI, NDWI, SAR) ───

@router.post(
    "/projects/{project_id}/derived-layers",
    response_model=DerivedLayerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def compute_derived_layer(
    project_id: uuid.UUID,
    payload: DerivedLayerComputeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Registers a verified derived spectral/radar index layer linked cryptographically
    to its parent observation.
    """
    abac = ABACEngine(db, current_user)
    project = await abac.enforce_project_access(project_id)

    obs = await observation_service.get_observation_by_id(
        db=db,
        observation_id=payload.observation_id,
        organization_id=project.organization_id,
    )
    if not obs or obs.project_id != project_id:
        raise HTTPException(status_code=404, detail="Parent observation not found.")

    try:
        layer = await derived_layer_service.register_derived_layer(
            db=db,
            observation=obs,
            layer_type=payload.layer_type,
            statistics=payload.statistics,
            asset_uri=payload.asset_uri,
        )
        return layer
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/projects/{project_id}/derived-layers", response_model=List[DerivedLayerResponse])
async def list_derived_layers(
    project_id: uuid.UUID,
    observation_id: Optional[uuid.UUID] = None,
    layer_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists derived layers for a project or observation.
    """
    abac = ABACEngine(db, current_user)
    project = await abac.enforce_project_access(project_id)

    layers = await derived_layer_service.list_derived_layers(
        db=db,
        project_id=project_id,
        organization_id=project.organization_id,
        observation_id=observation_id,
        layer_type=layer_type,
    )
    return layers


# ─── 5. Spatial Anomalies & Corroboration ───

@router.get("/projects/{project_id}/anomalies", response_model=List[AnomalyResponse])
async def list_spatial_anomalies(
    project_id: uuid.UUID,
    status_filter: Optional[str] = Query(None, alias="status"),
    severity: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists detected spatial change signals with review recommendations.
    """
    abac = ABACEngine(db, current_user)
    project = await abac.enforce_project_access(project_id)

    anomalies = await anomaly_service.list_anomalies(
        db=db,
        project_id=project_id,
        organization_id=project.organization_id,
        status=status_filter,
        severity=severity,
    )
    return anomalies


@router.post("/anomalies/{anomaly_id}/corroborate", response_model=AnomalyResponse)
async def corroborate_anomaly(
    anomaly_id: uuid.UUID,
    payload: AnomalyCorroborateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Records ground auditor verification or dismissal of a spatial anomaly.
    """
    org_id = current_user.organization_id
    if not org_id and current_user.role != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="No organization context.")

    # If super admin without org, fetch anomaly's org
    if not org_id:
        from app.domains.earth_observation.models import EOSpatialAnomaly
        from sqlalchemy import select
        res = await db.execute(select(EOSpatialAnomaly).where(EOSpatialAnomaly.id == anomaly_id))
        anom = res.scalars().first()
        if not anom:
            raise HTTPException(status_code=404, detail="Anomaly not found.")
        org_id = anom.organization_id

    updated = await anomaly_service.corroborate_anomaly(
        db=db,
        anomaly_id=anomaly_id,
        organization_id=org_id,
        corroborated=payload.corroborated,
        notes=payload.notes,
        verification_task_id=payload.verification_task_id,
        corroborating_activity_id=payload.corroborating_activity_id,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Anomaly not found.")
    return updated


# ─── 6. Baseline Evidence Packages ───

@router.post(
    "/projects/{project_id}/baseline-package",
    response_model=BaselinePackageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def compile_baseline_package(
    project_id: uuid.UUID,
    payload: BaselinePackageCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Compiles all baseline satellite observations into an immutable,
    cryptographically sealed baseline evidence package.
    """
    abac = ABACEngine(db, current_user)
    project = await abac.enforce_project_access(project_id)

    aoi = await aoi_service.get_project_active_aoi(
        db=db,
        project_id=project_id,
        organization_id=project.organization_id,
    )
    if not aoi:
        raise HTTPException(
            status_code=400,
            detail="Cannot compile baseline package: Project has no active AOI configured.",
        )

    from app.domains.earth_observation.models import ProjectBoundaryVersion
    bv_stmt = select(ProjectBoundaryVersion).where(
        ProjectBoundaryVersion.id == aoi.boundary_version_id
    )
    bv = (await db.execute(bv_stmt)).scalars().first()
    if not bv:
        raise HTTPException(status_code=400, detail="AOI is missing associated boundary version.")

    package = await baseline_service.compile_baseline_package(
        db=db,
        project_id=project_id,
        organization_id=project.organization_id,
        aoi=aoi,
        boundary_version=bv,
        notes=payload.notes,
    )
    return package


# ─── 7. MRV Evidence Manifest Export ───

@router.get("/projects/{project_id}/manifest")
async def get_mrv_manifest(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Exports a comprehensive, audit-ready MRV Evidence Manifest supporting project verification,
    monitoring, and registry documentation.
    Includes boundary version, observation provenance chain, derived layers,
    and anomaly corroboration history.
    """
    abac = ABACEngine(db, current_user)
    project = await abac.enforce_project_access(project_id)

    aoi = await aoi_service.get_project_active_aoi(
        db=db,
        project_id=project_id,
        organization_id=project.organization_id,
    )
    if not aoi:
        raise HTTPException(
            status_code=400,
            detail="Cannot export manifest: Project has no active AOI configured.",
        )

    manifest = await manifest_service.generate_project_mrv_manifest(
        db=db,
        project_id=project_id,
        organization_id=project.organization_id,
        aoi=aoi,
    )
    return manifest


# ─── 8. Cloud-Optimized GeoTIFF (COG) Asset Verification ───

@router.get("/projects/{project_id}/verify-cog-asset")
async def verify_cog_asset(
    project_id: uuid.UUID,
    observation_id: uuid.UUID = Query(..., description="Observation ID containing the COG asset"),
    asset_key: str = Query(
        default="visual",
        description="Band/asset key from raw_band_uris (e.g. 'visual', 'red', 'nir', 'vv')",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Verifies Cloud-Optimized GeoTIFF raster accessibility via HTTP Range request.

    Security: Resolves the canonical asset URL from the persisted observation record
    rather than accepting arbitrary URLs. Enforces ABAC project access and SSRF
    protection (hostname allowlist, private IP rejection, DNS rebinding prevention).

    Returns HTTP 206 status, content range, byte length, and TIFF magic header.
    """
    # Enforce project-level ABAC access
    abac = ABACEngine(db, current_user)
    project = await abac.enforce_project_access(project_id)

    # Look up the observation within the project's organization scope
    obs = await observation_service.get_observation_by_id(
        db=db,
        observation_id=observation_id,
        organization_id=project.organization_id,
    )
    if not obs or obs.project_id != project_id:
        raise HTTPException(
            status_code=404,
            detail="Observation not found in this project.",
        )

    # Resolve canonical asset URL from persisted band URIs
    asset_url = None
    if obs.raw_band_uris and isinstance(obs.raw_band_uris, dict):
        asset_url = obs.raw_band_uris.get(asset_key)

    # Fallback to asset_uri if specific key not found
    if not asset_url and asset_key in ("visual", "default"):
        asset_url = obs.asset_uri

    if not asset_url:
        available_keys = list(obs.raw_band_uris.keys()) if obs.raw_band_uris else []
        raise HTTPException(
            status_code=404,
            detail=f"Asset key '{asset_key}' not found in observation. Available keys: {available_keys}",
        )

    from app.domains.earth_observation.providers.stac_client import default_stac_client
    result = default_stac_client.verify_asset_range_access(asset_url)

    # Add observation context to the result
    result["observation_id"] = str(observation_id)
    result["asset_key"] = asset_key
    result["project_id"] = str(project_id)

    return result


# ─── 9. Authenticated EO Raster Delivery Endpoint ───

@router.get("/projects/{project_id}/observations/{observation_id}/raster")
async def get_observation_raster(
    project_id: uuid.UUID,
    observation_id: uuid.UUID,
    crop_to_aoi: bool = Query(True, description="When true, crops imagery to the project AOI with contextual padding"),
    display_mode: Optional[str] = Query(None, description="Visualization mode (e.g. TRUE_COLOR, FALSE_COLOR)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delivers a real browser-renderable raster visualization (JPEG or PNG) for the satellite observation.

    Security & Authorization:
    - Enforces ABAC project access: verifies current_user belongs to project's organization.
    - Scoped strictly to project_id: requests for an observation under the wrong project return 404.
    - SSRF protection: validates allowlisted hostnames and rejects private/loopback/cloud metadata.

    Real Raster Delivery:
    - Resolves visual preview / band composite from authoritative STAC provider assets.
    - If crop_to_aoi is True and project AOI exists, computes the exact geographic crop window
      with 15% contextual padding, returning the spatially aligned sub-raster.
    - PROHIBITS SYNTHETIC VISUALS IN PRODUCTION: If no verified provider imagery is accessible,
      returns HTTP 404 with a descriptive message rather than generating synthetic colored boxes.
    """
    abac = ABACEngine(db, current_user)
    project = await abac.enforce_project_access(project_id)

    obs = await observation_service.get_observation_by_id(
        db=db,
        observation_id=observation_id,
        organization_id=project.organization_id,
    )
    if not obs or obs.project_id != project_id:
        raise HTTPException(
            status_code=404,
            detail="Observation not found in this project.",
        )

    # 1. Gather candidate URLs from provider STAC assets
    candidate_urls = []
    if obs.raw_band_uris and isinstance(obs.raw_band_uris, dict):
        for k in ("thumbnail", "rendered_preview", "visual_png", "preview", "visual"):
            if k in obs.raw_band_uris and obs.raw_band_uris[k]:
                candidate_urls.append((k, obs.raw_band_uris[k]))

    if obs.asset_uri and any(obs.asset_uri.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp")):
        candidate_urls.append(("asset_uri", obs.asset_uri))

    from app.domains.earth_observation.providers.stac_client import (
        SSRFRedirectHandler,
        validate_cog_url,
    )
    import urllib.request
    from PIL import Image
    import io

    fetched_image = None
    fetched_origin = None
    fetched_asset_key = None

    for asset_key, img_url in candidate_urls:
        if img_url.startswith("https://"):
            try:
                validate_cog_url(img_url, enforce_allowlist=True)
                opener = urllib.request.build_opener(SSRFRedirectHandler(enforce_allowlist=True))
                req = urllib.request.Request(
                    img_url,
                    headers={"User-Agent": "VeriField-Nexus-Raster-Renderer/1.0"},
                )
                with opener.open(req, timeout=25) as resp:
                    if resp.status == 200:
                        data = resp.read(5_000_000)  # Max 5MB
                        if len(data) > 0:
                            try:
                                pil_img = Image.open(io.BytesIO(data))
                                pil_img.load()
                                fetched_image = pil_img
                                fetched_origin = f"PROVIDER_{asset_key.upper()}"
                                fetched_asset_key = asset_key
                                break
                            except Exception:
                                pass
            except Exception as fetch_err:
                logger.warning("Failed to fetch candidate raster URL %s: %s", img_url, fetch_err)

    if not fetched_image:
        # Strictly prohibit synthetic placeholder visuals in production
        raise HTTPException(
            status_code=404,
            detail=f"No verified satellite raster imagery available for scene {obs.scene_id}.",
        )

    # Determine metadata recipe and display provenance
    is_s2 = "Sentinel-2" in (obs.platform or "") or obs.provider_code == "SENTINEL_2"
    is_landsat = "Landsat" in (obs.platform or "") or obs.provider_code == "LANDSAT"
    is_s1 = "Sentinel-1" in (obs.platform or "") or obs.observation_type == EOObservationType.SAR_C_BAND_BACKSCATTER

    is_source_band_composite = (
        display_mode == "SOURCE_BAND_COMPOSITE"
        or (fetched_origin and "SOURCE_BAND_COMPOSITE" in fetched_origin)
    )

    if is_source_band_composite:
        display_source_type = "SOURCE_BAND_COMPOSITE"
        vis_type = "SOURCE_BAND_RGB_COMPOSITE"
        vis_version = "BAND_COMPOSITE_V1"
        vis_recipe = "SOURCE_BAND_RGB_COMPOSITE"
        display_source_label = "Source Band Composite"
        if is_s2:
            band_mapping = "R=B04,G=B03,B=B02"
        elif is_landsat:
            is_oli = any(k in (obs.scene_id or "") for k in ("LC08", "LC09"))
            band_mapping = "R=B4,G=B3,B=B2" if is_oli else "R=B3,G=B2,B=B1"
        else:
            band_mapping = "RGB"
    elif is_s1:
        vis_type = "DUAL_POL_SAR_QUICKLOOK"
        band_mapping = "R=VV,G=VH,B=VV/VH ratio"
        vis_version = "S1_C_SAR_GRD_V1"
        display_source_type = "SAR_RENDER"
        vis_recipe = "S1_DUAL_POL_QUICKLOOK"
        display_source_label = "Provider Quicklook"
    elif is_s2:
        vis_type = "PROVIDER_OPTICAL_PREVIEW"
        band_mapping = "PROVIDER_RENDERED"
        vis_version = "S2_TRUE_COLOR_V1"
        display_source_type = "PROVIDER_VISUAL"
        vis_recipe = "S2_TRUE_COLOR_PREVIEW"
        display_source_label = "Provider Visual"
    elif is_landsat:
        vis_type = "LANDSAT_HISTORICAL_OPTICAL_PREVIEW"
        band_mapping = "PROVIDER_RENDERED"
        vis_version = "LANDSAT_C2_L2_V1"
        display_source_type = "PROVIDER_VISUAL"
        vis_recipe = "LANDSAT_C2_L2_PREVIEW"
        display_source_label = "Provider Preview"
    else:
        vis_type = "OPTICAL_VISUAL"
        band_mapping = "PROVIDER_RENDERED"
        vis_version = "STANDARD_V1"
        display_source_type = "PROVIDER_VISUAL"
        vis_recipe = "PROVIDER_SUPPLIED_PREVIEW"
        display_source_label = "Provider Visual"

    crop_mode = "FULL_SCENE"
    final_bounds = obs.bounding_box or []

    # 2. Window / crop to project AOI if requested and project AOI is available
    if crop_to_aoi and obs.bounding_box and len(obs.bounding_box) == 4:
        from app.domains.earth_observation.services.aoi_service import aoi_service
        aoi = await aoi_service.get_active_aoi(db, project_id, project.organization_id)
        if aoi and aoi.geometry_geojson:
            try:
                from shapely.geometry import shape
                poly = shape(aoi.geometry_geojson)
                aoi_w, aoi_s, aoi_e, aoi_n = poly.bounds
                scene_w, scene_s, scene_e, scene_n = obs.bounding_box

                # Check intersection
                inter_w = max(aoi_w, scene_w)
                inter_e = min(aoi_e, scene_e)
                inter_s = max(aoi_s, scene_s)
                inter_n = min(aoi_n, scene_n)

                if inter_w < inter_e and inter_s < inter_n:
                    # 15% contextual padding
                    pad_x = (inter_e - inter_w) * 0.15
                    pad_y = (inter_n - inter_s) * 0.15
                    crop_w = max(scene_w, inter_w - pad_x)
                    crop_e = min(scene_e, inter_e + pad_x)
                    crop_s = max(scene_s, inter_s - pad_y)
                    crop_n = min(scene_n, inter_n + pad_y)

                    W, H = fetched_image.size
                    px0 = max(0, min(W - 1, int((crop_w - scene_w) / (scene_e - scene_w) * W)))
                    px1 = max(px0 + 1, min(W, int((crop_e - scene_w) / (scene_e - scene_w) * W)))
                    py0 = max(0, min(H - 1, int((scene_n - crop_n) / (scene_n - scene_s) * H)))
                    py1 = max(py0 + 1, min(H, int((scene_n - crop_s) / (scene_n - scene_s) * H)))

                    if (px1 - px0) >= 8 and (py1 - py0) >= 8:
                        fetched_image = fetched_image.crop((px0, py0, px1, py1))
                        crop_mode = "AOI_CONTEXT"
                        final_bounds = [crop_w, crop_s, crop_e, crop_n]
            except Exception as crop_err:
                logger.warning("Failed to compute AOI crop: %s", crop_err)

    buf = io.BytesIO()
    out_format = "JPEG" if fetched_image.mode in ("RGB", "L") else "PNG"
    media_type = "image/jpeg" if out_format == "JPEG" else "image/png"
    fetched_image.save(buf, format=out_format, quality=92)
    output_bytes = buf.getvalue()

    return Response(
        content=output_bytes,
        media_type=media_type,
        headers={
            "Cache-Control": "public, max-age=86400",
            "X-EO-Raster-Origin": fetched_origin or "PROVIDER_VISUAL_PREVIEW",
            "X-Display-Source-Type": display_source_type,
            "X-Display-Asset-Key": fetched_asset_key or "thumbnail",
            "X-Display-Source": "PROVIDER_PREVIEW",
            "X-Display-Source-Label": display_source_label,
            "X-Visualization-Recipe": vis_recipe,
            "X-Raster-Crop": crop_mode,
            "X-Raster-Bounds": str(final_bounds),
            "X-Raster-CRS": "EPSG:4326",
            "X-Visualization-Type": vis_type,
            "X-Band-Mapping": band_mapping,
            "X-Visualization-Version": vis_version,
            "X-Observation-ID": str(obs.id),
            "X-Platform": obs.platform or "Unknown",
        },
    )


@router.get("/projects/{project_id}/derived-layers/{layer_id}/raster")
async def get_derived_layer_raster(
    project_id: uuid.UUID,
    layer_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delivers a rendered raster visualization for an analytical derived layer (e.g. NDVI, EVI, NDWI)
    with explicit display provenance headers (X-Display-Source-Type: DERIVED_PRODUCT).

    In the current architecture, derived indices are marked PRODUCTION_READY_WITH_LIMITATION:
    statistical calculation and metadata lineage are operational, but pixel rendering
    (TiTiler/GDAL workers) is deferred. Returns HTTP 404 with provenance headers rather than
    generating synthetic placeholder images.
    """
    abac = ABACEngine(db, current_user)
    project = await abac.enforce_project_access(project_id)

    layer = await derived_layer_service.get_derived_layer(
        db=db,
        layer_id=layer_id,
        project_id=project_id,
        organization_id=project.organization_id,
    )
    if not layer:
        raise HTTPException(
            status_code=404,
            detail="Derived layer not found in this project.",
        )

    raise HTTPException(
        status_code=404,
        detail=f"Derived layer raster computation for {layer.layer_type} is PRODUCTION_READY_WITH_LIMITATION (analytical raster rendering engine not configured). No synthetic raster will be generated.",
        headers={
            "X-Display-Source-Type": "DERIVED_PRODUCT",
            "X-Layer-Type": layer.layer_type,
            "X-Processor-Version": layer.processor_version or "V1.0",
        },
    )
