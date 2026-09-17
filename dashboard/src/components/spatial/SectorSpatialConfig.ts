// =============================================================================
// VeriField Nexus — Sector-Aware Spatial Configuration Engine
// =============================================================================
// Defines metadata-driven layer definitions, asset types, legend configurations,
// and Earth Observation product schemas for each canonical climate sector.
//
// INVARIANTS:
// 1. Satellite index != Carbon. Spectral indices (NDVI/EVI) indicate photosynthetic
//    activity, NOT carbon stocks or carbon credits.
// 2. SAR backscatter is a physical radar proxy, never direct "Soil Moisture"
//    without a calibrated ground-coupled model.
// 3. Commercial EO (PlanetScope, SkySat) is NOT_CONFIGURED unless real API keys exist.
// 4. Biochar satellite imagery provides site/land context only; never infers yield.
// 5. Hybrid Energy satellite imagery provides site context only; never infers MWh.
// 6. Cookstove exact household coordinates are protected via clustering.
// =============================================================================

export type BasemapType = "map" | "satellite";

const CANONICAL_MAP: Record<string, string> = {
  agriculture: "agriculture_land_use",
  agriculture_land_use: "agriculture_land_use",
  afolu: "agriculture_land_use",
  biochar: "biochar",
  hybrid_energy: "hybrid_energy",
  energy: "hybrid_energy",
  ams_i_f: "hybrid_energy",
  ev: "ev_mobility",
  ev_mobility: "ev_mobility",
  ams_iii_c: "ev_mobility",
  cookstoves: "cookstoves",
  clean_cooking: "cookstoves",
  ams_ii_g: "cookstoves",
};

export function resolveCanonicalSector(sector?: string): string {
  if (!sector) return "";
  const clean = sector.toLowerCase().trim().replace(/[\s\-_]+/g, "_");
  return CANONICAL_MAP[clean] || clean;
}

export interface LayerDefinition {
  id: string;
  name: string;
  category: "BASEMAP" | "PROJECT" | "EVIDENCE" | "EARTH_OBSERVATION";
  description: string;
  color?: string;
  enabledByDefault: boolean;
  requiresData: boolean;
  dataProvider?: string;
}

export interface LegendItem {
  id: string;
  label: string;
  color: string;
  shape: "circle" | "polygon" | "line" | "dashed_polygon";
  description?: string;
}

export interface SectorSpatialConfig {
  sectorCode: string;
  sectorName: string;
  assetSingular: string;
  assetPlural: string;
  emptyTitle: string;
  emptySubtitle: string;
  availableLayers: LayerDefinition[];
  legend: LegendItem[];
  supportsEarthObservation: boolean;
  allowedEOProviders: string[];
  privacySafeClustering: boolean;
}

const AGRICULTURE_CONFIG: SectorSpatialConfig = {
  sectorCode: "AGRICULTURE_LAND_USE",
  sectorName: "Agriculture & Land Use",
  assetSingular: "Land Unit",
  assetPlural: "Land Units",
  emptyTitle: "No land boundaries registered.",
  emptySubtitle: "Add or capture a land unit to establish the project map.",
  supportsEarthObservation: true,
  allowedEOProviders: ["SENTINEL_2", "SENTINEL_1", "LANDSAT_8_9"],
  privacySafeClustering: false,
  availableLayers: [
    {
      id: "boundaries",
      name: "Project Boundaries",
      category: "PROJECT",
      description: "Authoritative project boundary polygons",
      color: "#00B47A",
      enabledByDefault: true,
      requiresData: true,
    },
    {
      id: "land_units",
      name: "Land Units & Parcels",
      category: "PROJECT",
      description: "Agricultural plots, strata, and monitoring parcels",
      color: "#10B981",
      enabledByDefault: true,
      requiresData: true,
    },
    {
      id: "soil_samples",
      name: "Soil Sample Locations",
      category: "EVIDENCE",
      description: "Georeferenced ground-truth soil sampling points",
      color: "#3B82F6",
      enabledByDefault: true,
      requiresData: true,
    },
    {
      id: "tree_observations",
      name: "Tree Observations",
      category: "EVIDENCE",
      description: "Biomass and canopy ground observations",
      color: "#059669",
      enabledByDefault: true,
      requiresData: true,
    },
    {
      id: "field_activities",
      name: "Field Activities",
      category: "EVIDENCE",
      description: "Farm management, planting, and conservation events",
      color: "#EC4899",
      enabledByDefault: false,
      requiresData: true,
    },
    {
      id: "sentinel_2",
      name: "Sentinel-2 Optical (10m)",
      category: "EARTH_OBSERVATION",
      description: "Copernicus multispectral optical imagery & spectral indices (NDVI/EVI)",
      color: "#10B981",
      enabledByDefault: false,
      requiresData: true,
      dataProvider: "Copernicus Sentinel-2 L2A",
    },
    {
      id: "sentinel_1",
      name: "Sentinel-1 SAR Backscatter (C-Band)",
      category: "EARTH_OBSERVATION",
      description: "Synthetic Aperture Radar VV/VH backscatter proxy",
      color: "#6366F1",
      enabledByDefault: false,
      requiresData: true,
      dataProvider: "Copernicus Sentinel-1 GRD",
    },
    {
      id: "landsat",
      name: "Landsat 8/9 (30m)",
      category: "EARTH_OBSERVATION",
      description: "USGS multispectral & thermal infrared historical surface reflectance",
      color: "#F59E0B",
      enabledByDefault: false,
      requiresData: true,
      dataProvider: "USGS Landsat Collection 2 Tier 1",
    },
  ],
  legend: [
    { id: "boundary", label: "Project Boundary", color: "#00B47A", shape: "polygon" },
    { id: "parcel", label: "Land Unit / Parcel", color: "#10B981", shape: "polygon" },
    { id: "plot", label: "Monitoring Plot", color: "#F59E0B", shape: "dashed_polygon" },
    { id: "soil", label: "Soil Sample Point", color: "#3B82F6", shape: "circle" },
    { id: "tree", label: "Tree Observation", color: "#059669", shape: "circle" },
    { id: "activity", label: "Field Activity", color: "#EC4899", shape: "circle" },
  ],
};

const BIOCHAR_CONFIG: SectorSpatialConfig = {
  sectorCode: "BIOCHAR",
  sectorName: "Biochar Carbon Removal",
  assetSingular: "Facility",
  assetPlural: "Facilities",
  emptyTitle: "No biochar facilities registered.",
  emptySubtitle: "Add or capture a production facility to establish the project map.",
  supportsEarthObservation: true,
  allowedEOProviders: ["SENTINEL_2"], // Contextual optical only
  privacySafeClustering: false,
  availableLayers: [
    {
      id: "facilities",
      name: "Production Facilities",
      category: "PROJECT",
      description: "Thermal conversion plants, kilns, and pyrolyzers",
      color: "#8B5CF6",
      enabledByDefault: true,
      requiresData: true,
    },
    {
      id: "feedstock_sources",
      name: "Feedstock Sources",
      category: "PROJECT",
      description: "Biomass origins, residue suppliers, and collection points",
      color: "#10B981",
      enabledByDefault: true,
      requiresData: true,
    },
    {
      id: "storage_locations",
      name: "Storage Locations",
      category: "PROJECT",
      description: "Warehouse and inventory storage locations",
      color: "#F59E0B",
      enabledByDefault: false,
      requiresData: true,
    },
    {
      id: "end_use_sites",
      name: "End-Use Sites",
      category: "EVIDENCE",
      description: "Soil amendment parcels and durable non-soil application sites",
      color: "#EC4899",
      enabledByDefault: true,
      requiresData: true,
    },
    {
      id: "linked_land_units",
      name: "Linked Agricultural Land",
      category: "PROJECT",
      description: "Cross-sector agricultural land units linked for biomass or soil end use",
      color: "#00B47A",
      enabledByDefault: true,
      requiresData: true,
    },
    {
      id: "sentinel_2",
      name: "Satellite Context (Sentinel-2)",
      category: "EARTH_OBSERVATION",
      description: "Optical land-use context for facility and application sites (Context only)",
      color: "#10B981",
      enabledByDefault: false,
      requiresData: true,
      dataProvider: "Copernicus Sentinel-2",
    },
  ],
  legend: [
    { id: "facility", label: "Production Facility", color: "#8B5CF6", shape: "circle" },
    { id: "source", label: "Feedstock Source", color: "#10B981", shape: "circle" },
    { id: "storage", label: "Storage Location", color: "#F59E0B", shape: "circle" },
    { id: "end_use", label: "End-Use Site", color: "#EC4899", shape: "circle" },
    { id: "linked_land", label: "Linked Agricultural Land", color: "#00B47A", shape: "polygon" },
  ],
};

const HYBRID_ENERGY_CONFIG: SectorSpatialConfig = {
  sectorCode: "HYBRID_ENERGY",
  sectorName: "Hybrid Energy & Mini-grids",
  assetSingular: "Energy System",
  assetPlural: "Energy Systems",
  emptyTitle: "No energy assets registered.",
  emptySubtitle: "Add or capture a generation asset to establish the project map.",
  supportsEarthObservation: true,
  allowedEOProviders: ["SENTINEL_2"], // Contextual optical only
  privacySafeClustering: false,
  availableLayers: [
    {
      id: "generation_assets",
      name: "Solar PV & Generation Assets",
      category: "PROJECT",
      description: "Solar PV arrays and hybrid generation installations",
      color: "#3B82F6",
      enabledByDefault: true,
      requiresData: true,
    },
    {
      id: "inverters_meters",
      name: "Inverters & Smart Meters",
      category: "PROJECT",
      description: "Telemetry metering points and inverter gateways",
      color: "#10B981",
      enabledByDefault: true,
      requiresData: true,
    },
    {
      id: "generators",
      name: "Backup Generators",
      category: "PROJECT",
      description: "Diesel or secondary generator installations",
      color: "#F59E0B",
      enabledByDefault: true,
      requiresData: true,
    },
    {
      id: "facility_boundary",
      name: "Facility Site Boundary",
      category: "PROJECT",
      description: "Project plant fence-line or mini-grid concession perimeter",
      color: "#6366F1",
      enabledByDefault: true,
      requiresData: true,
    },
  ],
  legend: [
    { id: "solar", label: "Solar / Generation Asset", color: "#3B82F6", shape: "circle" },
    { id: "meter", label: "Inverter / Meter", color: "#10B981", shape: "circle" },
    { id: "gen", label: "Backup Generator", color: "#F59E0B", shape: "circle" },
    { id: "site_bound", label: "Site Boundary", color: "#6366F1", shape: "polygon" },
  ],
};

const EV_MOBILITY_CONFIG: SectorSpatialConfig = {
  sectorCode: "EV_MOBILITY",
  sectorName: "EV Mobility",
  assetSingular: "Charging Station",
  assetPlural: "Charging Stations",
  emptyTitle: "No charging stations registered.",
  emptySubtitle: "Add or capture a charging station to establish the project map.",
  supportsEarthObservation: false,
  allowedEOProviders: [],
  privacySafeClustering: true,
  availableLayers: [
    {
      id: "charging_stations",
      name: "Charging Stations",
      category: "PROJECT",
      description: "EV charging stations and fleet hubs",
      color: "#10B981",
      enabledByDefault: true,
      requiresData: true,
    },
    {
      id: "chargers",
      name: "Charger Outlets / Dispensers",
      category: "PROJECT",
      description: "Individual metered dispensing points",
      color: "#3B82F6",
      enabledByDefault: true,
      requiresData: true,
    },
    {
      id: "operating_sites",
      name: "Operating Sites / Hubs",
      category: "PROJECT",
      description: "Depots and interchange facilities",
      color: "#8B5CF6",
      enabledByDefault: false,
      requiresData: true,
    },
  ],
  legend: [
    { id: "station", label: "Charging Station", color: "#10B981", shape: "circle" },
    { id: "charger", label: "Dispenser / Charger", color: "#3B82F6", shape: "circle" },
    { id: "hub", label: "Operating Hub", color: "#8B5CF6", shape: "circle" },
  ],
};

const COOKSTOVES_CONFIG: SectorSpatialConfig = {
  sectorCode: "COOKSTOVES",
  sectorName: "Clean Cooking Solutions",
  assetSingular: "Cookstove",
  assetPlural: "Cookstoves",
  emptyTitle: "No cookstove devices registered.",
  emptySubtitle: "Add or capture a device to establish the project map.",
  supportsEarthObservation: false,
  allowedEOProviders: [],
  privacySafeClustering: true, // Privacy rule: Cluster points to prevent household coordinate leakage
  availableLayers: [
    {
      id: "deployment_clusters",
      name: "Deployment Clusters",
      category: "PROJECT",
      description: "Community-level distribution aggregates (privacy protected)",
      color: "#F59E0B",
      enabledByDefault: true,
      requiresData: true,
    },
    {
      id: "devices",
      name: "Active Devices",
      category: "PROJECT",
      description: "Registered stove units with verified thermal telemetry",
      color: "#10B981",
      enabledByDefault: true,
      requiresData: true,
    },
    {
      id: "field_activities",
      name: "Field Monitoring Visits",
      category: "EVIDENCE",
      description: "Survey, inspection, and maintenance activity events",
      color: "#3B82F6",
      enabledByDefault: false,
      requiresData: true,
    },
  ],
  legend: [
    { id: "cluster", label: "Deployment Cluster", color: "#F59E0B", shape: "circle" },
    { id: "device", label: "Stove Device", color: "#10B981", shape: "circle" },
    { id: "visit", label: "Monitoring Visit", color: "#3B82F6", shape: "circle" },
  ],
};

export function getSectorSpatialConfig(sectorCode?: string): SectorSpatialConfig {
  const code = resolveCanonicalSector(sectorCode || "").toUpperCase();
  switch (code) {
    case "AGRICULTURE_LAND_USE":
    case "AFOLU":
      return AGRICULTURE_CONFIG;
    case "BIOCHAR":
      return BIOCHAR_CONFIG;
    case "HYBRID_ENERGY":
    case "ENERGY":
      return HYBRID_ENERGY_CONFIG;
    case "EV_MOBILITY":
    case "EV":
      return EV_MOBILITY_CONFIG;
    case "COOKSTOVES":
    case "CLEAN_COOKING":
    default:
      return COOKSTOVES_CONFIG;
  }
}
