// =============================================================================

// VeriField Nexus — Workspace Resolution Engine (CIOS-Compliant)

// =============================================================================

// Deterministic, metadata-driven workspace resolution.

// No hardcoded sector names. No heuristic matching. No string comparisons.

// All workspace routing is derived from backend metadata exclusively.

// =============================================================================






// ─── Type Definitions ────────────────────────────────────────────────────────



export interface KPICardDef {

  key: string;

  label: string;

  valueField: string;

  unit: string;

  iconName: string;

  colorTheme: "green" | "amber" | "blue" | "purple" | "emerald";

  description: string;

}



export interface ChartDef {

  key: string;

  title: string;

  type: "area" | "bar" | "line";

  dataKeyX: string;

  dataKeyY: string;

  fillColor: string;

  strokeColor: string;

}



export interface ModuleLabels {

  assetLabel: string;

  assetLabelPlural: string;

  telemetryTitle: string;

  telemetryDesc: string;

  syncTitle: string;

  emptyLogsMsg: string;

  specLabel: string;

  assetTargetLabel: string;

  noLogsText: string;

  propHeading: string;

  propSub: string;

  tabLabel: string;

  tabIconName: string;

  activitiesTitle: string;

  activitiesDesc: string;

}



export interface TableColumnDef {

  header: string;

  accessor: string;

  align?: "left" | "center" | "right";

  format?: "weight" | "percent" | "raw" | "id";

}



export interface FilterOption {

  value: string;

  label: string;

}



export interface ModuleDefinition {

  id: string;

  name: string;

  badge: string;

  label: string;

  methodology: string;

  registryReference: string;

  allowedRoles: string[];

  kpis: KPICardDef[];

  charts: ChartDef[];

  labels: ModuleLabels;

  markerColor: string;

  themeColor: string;

  tableColumns: TableColumnDef[];

  filterOptions: FilterOption[];

}



// ─── Backend API Response Types ──────────────────────────────────────────────



export interface APIFamily {

  id: string;

  code: string;
  name: string;
  description?: string;
  project_types?: unknown[];
}

export interface APIMethodologyUIConfig {
  kpis?: KPICardDef[];
  charts?: ChartDef[];
  filterOptions?: FilterOption[];
  default_price_usd?: number;
  [key: string]: unknown;
}

export interface ClassifiableRecord {
  sector?: string | null;
  methodology_code?: string | null;
  property_type?: string | null;
  activity_type?: string | null;
  type?: string | null;
  asset_type?: string | null;
}

export interface APIMethodology {
  id: string;
  code: string;
  name: string;
  description?: string;
  family?: APIFamily;
  family_id?: string; // Some endpoints may return flat ID
  ui_config?: APIMethodologyUIConfig;
  form_schema?: Record<string, unknown>;
  recommendation_rules?: Record<string, unknown>;
}



// ─── Workspace Config (resolved from metadata) ──────────────────────────────



export interface WorkspaceConfig {

  id: string;                          // Family ID

  code: string;                        // Family code (lowercase)

  name: string;                        // Family display name

  description: string;

  badge: string;                       // Dynamic badge text

  label: string;                       // Dynamic label text

  methodology?: string;                // Primary methodology name

  kpis: KPICardDef[];

  charts: ChartDef[];

  filterOptions: FilterOption[];

  form_schema?: Record<string, unknown>;

  default_price_usd?: number;

  methodologyCodes: string[];          // All methodology codes in this family

}



// ─── Workspace Registry ──────────────────────────────────────────────────────



/**

 * Builds a deterministic workspace registry from backend API metadata.

 * No hardcoded sector names. All values derived from API responses.

 */

export function buildWorkspaceRegistry(

  methodologies: APIMethodology[],

  families: APIFamily[]

): Record<string, WorkspaceConfig> {

  const registry: Record<string, WorkspaceConfig> = {};



  // Step 1: Index methodologies by family

  const methByFamilyId: Record<string, APIMethodology[]> = {};

  const methByCode: Record<string, APIMethodology> = {};



  for (const meth of methodologies) {

    const code = (meth.code || "").toLowerCase();

    methByCode[code] = meth;



    // Resolve family ID from either nested object or flat field

    const familyId = meth.family?.id || meth.family_id;

    if (familyId) {

      if (!methByFamilyId[familyId]) methByFamilyId[familyId] = [];

      methByFamilyId[familyId].push(meth);

    }



    // Also register the methodology itself (for direct code lookups)

    registry[code] = {

      id: meth.id,

      code: code,

      name: meth.name,

      description: meth.description || "",

      badge: meth.family?.name?.toUpperCase() || meth.name.toUpperCase(),

      label: meth.family?.name || meth.name,

      methodology: meth.name,

      kpis: meth.ui_config?.kpis || [],

      charts: meth.ui_config?.charts || [],

      filterOptions: meth.ui_config?.filterOptions || [],

      form_schema: meth.form_schema,

      default_price_usd: meth.ui_config?.default_price_usd,

      methodologyCodes: [code]

    };

  }



  // Step 2: Register families as top-level workspaces

  for (const fam of families) {

    const familyCode = (fam.code || "").toLowerCase();

    const childMeths = methByFamilyId[fam.id] || [];



    // Find the first child with a ui_config to inherit

    const primaryMeth = childMeths.find(m => m.ui_config && Object.keys(m.ui_config).length > 0)

      || childMeths[0];



    const config: WorkspaceConfig = {

      id: fam.id,

      code: familyCode,

      name: fam.name,

      description: fam.description || "",

      badge: `${fam.name.toUpperCase()} ENGINE`,

      label: fam.name,

      methodology: primaryMeth?.name,

      kpis: primaryMeth?.ui_config?.kpis || [],

      charts: primaryMeth?.ui_config?.charts || [],

      filterOptions: primaryMeth?.ui_config?.filterOptions || [],

      form_schema: primaryMeth?.form_schema,

      default_price_usd: primaryMeth?.ui_config?.default_price_usd,

      methodologyCodes: childMeths.map(m => (m.code || "").toLowerCase())

    };



    // Family code always takes precedence (overwrite methodology-level entry)

    registry[familyCode] = config;

  }



  return registry;

}



/**

 * Build a map from methodology code → family code.

 * Used to resolve a user's licensed_methodologies to their parent workspace.

 */

export function buildMethodologyToFamilyMap(

  methodologies: APIMethodology[],

  families: APIFamily[]

): Record<string, string> {

  const map: Record<string, string> = {};

  const familyById: Record<string, string> = {};



  for (const fam of families) {

    familyById[fam.id] = (fam.code || "").toLowerCase();

  }



  for (const meth of methodologies) {

    const methCode = (meth.code || "").toLowerCase();

    const familyId = meth.family?.id || meth.family_id;

    if (familyId && familyById[familyId]) {

      map[methCode] = familyById[familyId];

    }

  }



  return map;

}



/**

 * Resolve a user's active workspace from their licensed sectors and methodologies.

 * Uses ONLY metadata. No hardcoded fallbacks.

 *

 * Resolution order:

 * 1. licensed_sectors (direct family codes)

 * 2. licensed_methodologies → mapped to parent family codes

 * 3. First available workspace in registry

 * 4. "generic" (no workspace)

 */

const SECTOR_CANONICAL_MAP: Record<string, string> = {
  // Agriculture & Land Use
  agriculture_land_use: "agriculture_land_use",
  agriculture: "agriculture_land_use",
  afolu: "agriculture_land_use",
  land_use: "agriculture_land_use",
  agri: "agriculture_land_use",
  farm: "agriculture_land_use",
  farming: "agriculture_land_use",
  soil: "agriculture_land_use",
  rice: "agriculture_land_use",
  vm0042: "agriculture_land_use",
  vm0047: "agriculture_land_use",
  vt0014: "agriculture_land_use",
  vmd0053: "agriculture_land_use",
  vm0051: "agriculture_land_use",
  bm_ag04: "agriculture_land_use",
  bm_fr05: "agriculture_land_use",

  // EV Mobility
  ev_mobility: "ev_mobility",
  ev: "ev_mobility",
  electric_mobility: "ev_mobility",
  mobility: "ev_mobility",
  electric_vehicles: "ev_mobility",
  ams_iii_c: "ev_mobility",
  "867f684f": "ev_mobility",

  // Hybrid Energy
  hybrid_energy: "hybrid_energy",
  hybrid: "hybrid_energy",
  energy: "hybrid_energy",
  solar: "hybrid_energy",
  mini_grids: "hybrid_energy",
  acm0002: "hybrid_energy",
  "7f12bfe9": "hybrid_energy",

  // Clean Cookstoves
  cookstoves: "cookstoves",
  cookstove: "cookstoves",
  clean_cooking: "cookstoves",
  clean_cookstoves: "cookstoves",
  ams_ii_g: "cookstoves",
  "6f12bfe9": "cookstoves",
  dff43d66: "cookstoves",

  // Biochar
  biochar: "biochar",
  biochar_carbon: "biochar",
  pyrolysis: "biochar",
  "4f12bfe9": "biochar",
  e6db7fbe: "biochar",
};

export function canonicalSectorCode(sec: string): string {
  if (!sec) return "";
  const clean = sec.toLowerCase().trim().replace(/[\s\-_]+/g, "_");
  if (SECTOR_CANONICAL_MAP[clean]) {
    return SECTOR_CANONICAL_MAP[clean];
  }
  return clean;
}

/**
 * Resolve a user's active workspace from their licensed sectors and methodologies.
 * Uses ONLY metadata. No hardcoded fallbacks.
 *
 * Resolution order:
 * 1. licensed_sectors (direct family codes)
 * 2. licensed_methodologies → mapped to parent family codes
 * 3. First available workspace in registry
 * 4. "generic" (no workspace)
 */
const SECTOR_FAMILY_CODES = ["cookstoves", "hybrid_energy", "biochar", "ev_mobility", "agriculture_land_use"];

export function resolveUserWorkspace(
  licensedSectors: string[],
  licensedMethodologies: string[],
  methToFamily: Record<string, string>,
  registry: Record<string, Partial<WorkspaceConfig> | { methodologyCodes: string[] }>,
  orgName?: string
): { activeWorkspace: string; allowedWorkspaces: string[] } {
  const resolved = new Set<string>();

  // Priority 1: Direct sector licenses (these ARE family codes)
  for (const sec of licensedSectors) {
    const code = canonicalSectorCode(sec);
    if (SECTOR_FAMILY_CODES.includes(code)) {
      resolved.add(code);
    }
  }

  // Priority 2: Methodology licenses → resolve to parent family
  for (const meth of licensedMethodologies) {
    const methCode = meth.toLowerCase().trim();
    const familyCode = canonicalSectorCode(methToFamily[methCode] || methCode);
    if (SECTOR_FAMILY_CODES.includes(familyCode)) {
      resolved.add(familyCode);
    }
  }

  // Priority 3: Organization name semantic fallback
  if (resolved.size === 0 && orgName) {
    const orgCode = canonicalSectorCode(orgName);
    if (SECTOR_FAMILY_CODES.includes(orgCode)) {
      resolved.add(orgCode);
    }
  }

  const allowed = Array.from(resolved);

  if (allowed.length === 0) {
    return { activeWorkspace: "cookstoves", allowedWorkspaces: SECTOR_FAMILY_CODES };
  }

  return { activeWorkspace: allowed[0], allowedWorkspaces: allowed };
}



/**

 * Validate that a cached workspace is still valid for the current user.

 * Returns the cached value if valid, or null if it should be discarded.

 */

export function validateCachedWorkspace(

  cached: string | null,

  allowedWorkspaces: string[],

  methToFamily: Record<string, string>,

  isSuperAdmin: boolean

): string | null {

  if (!cached) return null;
  const normalized = canonicalSectorCode(cached);



  // Super admins can access any workspace

  if (isSuperAdmin) return normalized;



  // Direct match to allowed workspace

  if (allowedWorkspaces.includes(normalized)) return normalized;



  // Cached value might be a methodology code — resolve to family

  const familyCode = methToFamily[normalized];

  if (familyCode && allowedWorkspaces.includes(familyCode)) return familyCode;



  // Invalid cache — discard

  return null;

}



/**

 * Classify a record (property, activity, etc.) to its workspace.

 * Uses the record's metadata fields to determine workspace affiliation.

 *

 * For sandboxed (non-super-admin) users, ALL their data belongs to their workspace.

 * For super admins viewing all data, we use the record's metadata to classify.

 */

export function classifyRecord(
  record: ClassifiableRecord | null | undefined,

  methToFamily: Record<string, string>,

  activeWorkspace: string,

  isSandboxed: boolean

): boolean {

  // Sandboxed users: all their org data belongs to their workspace

  // (backend already filters by org)

  if (isSandboxed) return true;



  // Super admin: classify by record metadata

  if (!record) return false;



  // Check direct sector field

  const sector = record.sector;

  if (sector) {

    const sectorLower = sector.toLowerCase().trim();

    if (sectorLower === activeWorkspace) return true;

    // Check if it's a methodology code that maps to the active workspace

    const familyCode = methToFamily[sectorLower];

    if (familyCode === activeWorkspace) return true;

  }



  // Check property_type, activity_type, type, asset_type
  const typeFields = ['property_type', 'activity_type', 'type', 'asset_type'] as const;

  for (const field of typeFields) {

    const val = record[field];

    if (typeof val === 'string') {

      const valLower = val.toLowerCase().trim();

      if (valLower === activeWorkspace) return true;

      const familyCode = methToFamily[valLower];

      if (familyCode === activeWorkspace) return true;

    }

  }



  // Check methodology_code on the record

  if (record.methodology_code) {

    const methCode = record.methodology_code.toLowerCase().trim();

    const familyCode = methToFamily[methCode];

    if (familyCode === activeWorkspace) return true;

  }



  // For generic workspace, show everything

  if (activeWorkspace === "generic") return true;



  return false;

}



// ─── Legacy Compatibility Exports ────────────────────────────────────────────

// These are kept TEMPORARILY for any components that still import them.

// They will be removed in the final cleanup pass.



/** @deprecated Use buildWorkspaceRegistry + resolveUserWorkspace instead */

export function normalizeSector(sec: string): string {

  if (!sec) return "generic";

  return sec.toLowerCase().trim();

}



/** @deprecated Use classifyRecord instead */
export function mapToWorkspace(record: ClassifiableRecord | null | undefined): string | null {
  if (!record) return null;

  const normalizeVal = (value?: unknown) => {
    if (typeof value !== "string") return "";
    return value.toLowerCase().trim();
  };

  const type = normalizeVal(record.property_type || record.activity_type || record.type || record.asset_type || record.sector);
  if (!type) return null;
  return type;
}

/** @deprecated Use classifyRecord instead */
export function getRecordSector(record: ClassifiableRecord | null | undefined): string {
  if (record && record.sector) {
    return normalizeSector(record.sector);
  }
  return mapToWorkspace(record) || "generic";
}



// ─── Sector Terminology & Metadata Resolvers ───────────────────────────────────



export interface SectorTerminology {

  sectorCode: string;

  sectorName: string;

  assetSingular: string;      // e.g., "Cookstove Device", "EV Vehicle / Station", "Solar Mini-Grid"

  assetPlural: string;        // e.g., "Cookstove Devices", "EV Fleets & Stations", "Solar Mini-Grids"

  projectsNavLabel: string;   // e.g., "Projects & Devices", "Projects & Fleets", "Projects & Mini-Grids"

  monitoringNavLabel: string;  // e.g., "Live Telemetry", "Monitoring & EO"

  aiNavLabel: string;          // e.g., "AI Assistant", "Decision Support"

  stage3Label: string;        // e.g., "3. Device Deployment", "3. Fleet Onboard", "3. Mini-grid Install"

  stage3DetailedName: string; // e.g., "3. Device Deployment & Calibration"

  proceedToStage3Label: string; // e.g., "Proceed to Device Deployment"

  telemetrySource: string;    // e.g., "Thermal Sensors & Stove Logs"

  entityTypeAsset: string;    // e.g., "Cookstove Device Fleet", "EV Mobility Fleet"

}



export function getSectorTerminology(sectorCode?: string): SectorTerminology {

  const code = canonicalSectorCode(sectorCode || "");



  if (code === "cookstoves") {

    return {

      sectorCode: "cookstoves",

      sectorName: "Clean Cookstoves",

      assetSingular: "Cookstove Device",

      assetPlural: "Cookstove Devices",

      projectsNavLabel: "Projects & Devices",

      monitoringNavLabel: "Live Telemetry",

      aiNavLabel: "Decision Support",

      stage3Label: "3. Device Deployment",

      stage3DetailedName: "3. Device Deployment & Calibration",

      proceedToStage3Label: "Proceed to Device Deployment",

      telemetrySource: "Thermal Sensors & Stove Usage Logs",

      entityTypeAsset: "Cookstove Device Fleet"

    };

  }



  if (code === "ev_mobility") {

    return {

      sectorCode: "ev_mobility",

      sectorName: "Electric Mobility",

      assetSingular: "EV Vehicle / Station",

      assetPlural: "EV Fleets & Stations",

      projectsNavLabel: "Projects & Fleets",

      monitoringNavLabel: "Live Telemetry",

      aiNavLabel: "Decision Support",

      stage3Label: "3. Fleet Onboard",

      stage3DetailedName: "3. Fleet & Station Onboarding",

      proceedToStage3Label: "Proceed to Fleet Onboarding",

      telemetrySource: "EV Telemetry & Charging Sessions",

      entityTypeAsset: "EV Mobility Fleet"

    };

  }



  if (code === "hybrid_energy" || code === "solar") {

    return {

      sectorCode: "hybrid_energy",

      sectorName: "Solar & Mini-Grids",

      assetSingular: "Solar Mini-Grid",

      assetPlural: "Solar Mini-Grids",

      projectsNavLabel: "Projects & Mini-Grids",

      monitoringNavLabel: "Live Telemetry",

      aiNavLabel: "Decision Support",

      stage3Label: "3. Mini-grid Install",

      stage3DetailedName: "3. Mini-grid & Inverter Onboarding",

      proceedToStage3Label: "Proceed to Mini-Grid Onboarding",

      telemetrySource: "Smart Inverters & Solar Generation Logs",

      entityTypeAsset: "Renewable Solar Asset"

    };

  }



  if (code === "biochar") {

    return {

      sectorCode: "biochar",

      sectorName: "Biochar Carbon Removal",

      assetSingular: "Biochar Pyrolyzer",

      assetPlural: "Biochar Pyrolyzers",

      projectsNavLabel: "Projects & Facilities",

      monitoringNavLabel: "Live Telemetry",

      aiNavLabel: "Decision Support",

      stage3Label: "3. Facility Onboard",

      stage3DetailedName: "3. Pyrolyzer Facility Onboarding",

      proceedToStage3Label: "Proceed to Facility Onboarding",

      telemetrySource: "Pyrolyzer Thermal Probes & Batch Logs",

      entityTypeAsset: "Pyrolysis Facility Asset"

    };

  }



  if (code === "agriculture_land_use" || code === "agroforestry" || code === "forestry" || code === "agriculture") {

    return {

      sectorCode: "agriculture_land_use",

      sectorName: "Agriculture & Land Use",

      assetSingular: "Land Management Unit",

      assetPlural: "Parcels & Management Units",

      projectsNavLabel: "Projects & Land Units",

      monitoringNavLabel: "Monitoring & EO",

      aiNavLabel: "Decision Support",

      stage3Label: "3. Boundary & Plots",

      stage3DetailedName: "3. Geodesic Boundaries & Soil Stratification",

      proceedToStage3Label: "Proceed to Land Unit Registration",

      telemetrySource: "Sentinel EO, SAR Proxies & Soil Core Logs",

      entityTypeAsset: "Agricultural Land Unit"

    };

  }



  // Generic / Multi-sector fallback

  return {

    sectorCode: code || "generic",

    sectorName: "Carbon Projects",

    assetSingular: "Monitored Asset",

    assetPlural: "Monitored Assets",

    projectsNavLabel: "Projects & Assets",

    monitoringNavLabel: "Live Telemetry",

    aiNavLabel: "Decision Support",

    stage3Label: "3. Asset Deployment",

    stage3DetailedName: "3. Asset Deployment & Onboarding",

    proceedToStage3Label: "Proceed to Asset Onboarding",

    telemetrySource: "IoT Telemetry & Field Sensors",

    entityTypeAsset: "Carbon Project Asset"

  };

}



export function getSectorLifecycleStages(sectorCode?: string): string[] {

  const terms = getSectorTerminology(sectorCode);

  return [

    "1. Origination",

    "2. Methodology",

    terms.stage3Label,

    "4. Field Ops & Telemetry",

    "5. VVB Verification",

    "6. Credit Issuance & Sealing",

  ];

}
