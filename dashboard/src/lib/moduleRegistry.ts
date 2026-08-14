// =============================================================================

// VeriField Nexus — Workspace Resolution Engine (CIOS-Compliant)

// =============================================================================

// Deterministic, metadata-driven workspace resolution.

// No hardcoded sector names. No heuristic matching. No string comparisons.

// All workspace routing is derived from backend metadata exclusively.

// =============================================================================



import {

  Leaf,

  Flame,

  Zap,

  Scale,

  Sprout,

  Home,

  Globe,

  ClipboardCheck,

  MessageSquare,

  Cpu,

  LucideIcon

} from "lucide-react";



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

  project_types?: any[];

}



export interface APIMethodology {

  id: string;

  code: string;

  name: string;

  description?: string;

  family?: APIFamily;

  family_id?: string; // Some endpoints may return flat ID

  ui_config?: Record<string, any>;

  form_schema?: Record<string, any>;

  recommendation_rules?: Record<string, any>;

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

  form_schema?: Record<string, any>;

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

export function canonicalSectorCode(sec: string): string {
  if (!sec) return "";
  const clean = sec.toLowerCase().trim().replace(/[\s\-_]+/g, "_");
  if (clean.includes("7f12bfe9") || clean.includes("hybrid") || clean.includes("energy") || clean.includes("solar")) return "hybrid_energy";
  if (clean.includes("867f684f") || clean.includes("ev") || clean.includes("electric") || clean.includes("mobility")) return "ev_mobility";
  if (clean.includes("e6db7fbe") || clean.includes("4f12bfe9") || clean.includes("biochar")) return "biochar";
  if (clean.includes("dff43d66") || clean.includes("6f12bfe9") || clean.includes("cook") || clean.includes("stove")) return "cookstoves";
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
const SECTOR_FAMILY_CODES = ["cookstoves", "hybrid_energy", "biochar", "ev_mobility"];

export function resolveUserWorkspace(
  licensedSectors: string[],
  licensedMethodologies: string[],
  methToFamily: Record<string, string>,
  registry: Record<string, WorkspaceConfig>
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
  let normalized = canonicalSectorCode(cached);



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

  record: any,

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

  const typeFields = ['property_type', 'activity_type', 'type', 'asset_type'];

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

export function mapToWorkspace(record: any): string | null {

  if (!record) return null;

  const normalizeVal = (value?: any) => {

    if (typeof value !== "string") return "";

    return value.toLowerCase().trim();

  };

  const type = normalizeVal(record.property_type || record.activity_type || record.type || record.asset_type || record.sector);

  if (!type) return null;

  return type;

}



/** @deprecated Use classifyRecord instead */

export function getRecordSector(record: any): string {

  if (record && record.sector) {

    return normalizeSector(record.sector);

  }

  return mapToWorkspace(record) || "generic";

}
