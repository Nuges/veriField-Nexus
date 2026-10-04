/**
 * VeriField Nexus — Earth Observation Display Provenance Classification
 *
 * Implements authoritative classification of displayed raster layers to ensure
 * truthfulness:
 * 1. PROVIDER_VISUAL: Delivered from provider thumbnail/visual (not a VeriField band composite).
 * 2. SAR_RENDER: Dual-polarization SAR quicklook (not raw backscatter or soil moisture).
 * 3. SOURCE_BAND_COMPOSITE: Only when genuinely composited from raw spectral bands.
 * 4. DERIVED_PRODUCT: Analytical outputs (e.g. NDVI, EVI) from numerical processing.
 *
 * Enforces clear distinction between native sensor resolution (m) and delivered preview dimensions (px).
 */

export type DisplaySourceType =
  | "PROVIDER_VISUAL"
  | "SAR_RENDER"
  | "SOURCE_BAND_COMPOSITE"
  | "DERIVED_PRODUCT";

export interface DisplayProvenance {
  sourceType: DisplaySourceType;
  sourceLabel: string;
  displayDescription: string;
  sensorResolution: string;
  previewDimensions: string;
  bandRecipe: string | null;
  channels: string | null;
  isSar: boolean;
  isOptical: boolean;
  disclaimer: string | null;
  historicalContext: string | null;
  providerName: string;
  assetKey: string;
  processingLevel: string;
  crs: string;
}

export interface ObservationInput {
  scene_id?: string;
  platform?: string;
  sensor?: string;
  provider?: string;
  provider_code?: string;
  product_code?: string;
  observation_type?: string;
  processing_level?: string;
  display_mode?: string;
  display_source_type?: string;
  raw_band_uris?: Record<string, string>;
  is_baseline?: boolean;
  spatial_resolution_m?: number;
  cloud_cover_pct?: number | null;
  quality_status?: string;
  provenance_hash?: string;
  acquisition_timestamp?: string;
}

export function classifyDisplayProvenance(
  obs: ObservationInput = {},
  rasterDimensions?: { width: number; height: number } | null
): DisplayProvenance {
  const platform = obs.platform || "";
  const sceneId = obs.scene_id || "";
  const obsType = obs.observation_type || "";

  const isS2 =
    platform.includes("Sentinel-2") ||
    obs.provider_code === "SENTINEL_2" ||
    sceneId.startsWith("S2");

  const isS1 =
    platform.includes("Sentinel-1") ||
    obs.provider_code === "SENTINEL_1" ||
    obsType === "SAR_C_BAND_BACKSCATTER" ||
    sceneId.startsWith("S1");

  const isLandsat =
    platform.includes("Landsat") ||
    obs.provider_code === "LANDSAT" ||
    obs.product_code === "LANDSAT_C2_L2" ||
    sceneId.startsWith("L") ||
    sceneId.startsWith("LE07") ||
    sceneId.startsWith("LC08") ||
    sceneId.startsWith("LC09");

  // Delivered preview dimensions (rendered pixel grid)
  const previewDimensions = rasterDimensions
    ? `${rasterDimensions.width} × ${rasterDimensions.height} px`
    : "343 × 343 px";

  // Native sensor resolution (physical ground sampling distance)
  const sensorResolution = isLandsat
    ? `${obs.spatial_resolution_m || 30} m`
    : isS1
    ? `${obs.spatial_resolution_m || 10} m (GRD)`
    : `${obs.spatial_resolution_m || 10} m`;

  const assetKey = obs.raw_band_uris
    ? Object.keys(obs.raw_band_uris)[0] || "thumbnail"
    : "thumbnail";

  const crs = "EPSG:4326 (WGS 84)";

  // Check if this is an explicit derived analytical product
  if (
    obs.display_source_type === "DERIVED_PRODUCT" ||
    obsType === "DERIVED_INDEX"
  ) {
    return {
      sourceType: "DERIVED_PRODUCT",
      sourceLabel: "Derived Product",
      displayDescription: "Analytical spectral product (numerical computation)",
      sensorResolution,
      previewDimensions,
      bandRecipe: null,
      channels: null,
      isSar: false,
      isOptical: true,
      disclaimer:
        "Derived index raster computation is PRODUCTION_READY_WITH_LIMITATION. No synthetic pixels are fabricated.",
      historicalContext: null,
      providerName: "VeriField Processing Engine",
      assetKey,
      processingLevel: obs.processing_level || "Derived-L3",
      crs,
    };
  }

  // Check if genuinely composited from raw spectral bands
  // CRITICAL: NEVER infer SOURCE_BAND_COMPOSITE merely from platform Sentinel-2!
  const isGenuineSourceBandComposite =
    obs.display_mode === "SOURCE_BAND_COMPOSITE" ||
    obs.display_source_type === "SOURCE_BAND_COMPOSITE";

  if (isGenuineSourceBandComposite) {
    let bandRecipe = "R=B04, G=B03, B=B02";
    if (isLandsat) {
      const isOli = sceneId.includes("LC08") || sceneId.includes("LC09");
      bandRecipe = isOli ? "R=B4, G=B3, B=B2" : "R=B3, G=B2, B=B1";
    }

    return {
      sourceType: "SOURCE_BAND_COMPOSITE",
      sourceLabel: "Source Band Composite",
      displayDescription: "True-color RGB composite generated from calibrated source bands",
      sensorResolution,
      previewDimensions,
      bandRecipe,
      channels: null,
      isSar: false,
      isOptical: true,
      disclaimer: null,
      historicalContext: obs.is_baseline ? "Baseline evidence composite" : null,
      providerName: isS2
        ? "Copernicus Data Space Ecosystem"
        : isLandsat
        ? "USGS / AWS STAC"
        : "External Provider",
      assetKey,
      processingLevel: obs.processing_level || (isS2 ? "Level-2A" : "Collection 2 Level 2"),
      crs,
    };
  }

  // Sentinel-1 SAR Quicklook
  if (isS1) {
    return {
      sourceType: "SAR_RENDER",
      sourceLabel: "Provider Quicklook",
      displayDescription: "Dual-polarization SAR quicklook",
      sensorResolution,
      previewDimensions,
      bandRecipe: null,
      channels: "R=VV, G=VH, B=VV/VH ratio",
      isSar: true,
      isOptical: false,
      disclaimer:
        "Dual-polarization SAR quicklook (penetrates clouds, structural/roughness context). Soil moisture inversion model is NOT_CONFIGURED.",
      historicalContext: null,
      providerName: obs.provider || "Copernicus Data Space Ecosystem",
      assetKey,
      processingLevel: obs.processing_level || "Level-1-GRD",
      crs,
    };
  }

  // Landsat Optical Preview
  if (isLandsat) {
    return {
      sourceType: "PROVIDER_VISUAL",
      sourceLabel: "Provider Preview",
      displayDescription: "Landsat Collection 2 Level 2 Preview",
      sensorResolution,
      previewDimensions,
      bandRecipe: null,
      channels: null,
      isSar: false,
      isOptical: true,
      disclaimer: null,
      historicalContext: "Baseline evidence (prior to project start)",
      providerName: obs.provider || "USGS / AWS STAC",
      assetKey,
      processingLevel: obs.processing_level || "Collection 2 Level 2",
      crs,
    };
  }

  // Sentinel-2 or Default Optical Preview
  return {
    sourceType: "PROVIDER_VISUAL",
    sourceLabel: "Provider Visual",
    displayDescription: "Provider-rendered optical preview",
    sensorResolution,
    previewDimensions,
    bandRecipe: null, // Truth: not a VeriField band composite
    channels: null,
    isSar: false,
    isOptical: true,
    disclaimer: null,
    historicalContext: obs.is_baseline ? "Baseline evidence" : null,
    providerName: obs.provider || (isS2 ? "Copernicus Data Space Ecosystem" : "External Provider"),
    assetKey,
    processingLevel: obs.processing_level || "Level-2A",
    crs,
  };
}
