// =============================================================================
// VeriField Nexus — Canonical Operating Sectors Configuration
// =============================================================================
// Centralized, authoritative platform taxonomy for Primary Operating Sectors.
// This defines the strictly controlled 5 primary sectors across the platform.
//
// Sectors are PLATFORM TAXONOMY, NOT database rows, test fixtures, or
// methodology families. The UI and API must consume this canonical source.
// =============================================================================

export type CanonicalSectorCode =
  | "COOKSTOVES"
  | "HYBRID_ENERGY"
  | "BIOCHAR"
  | "EV_MOBILITY"
  | "AGRICULTURE_LAND_USE";

export interface CanonicalSectorOption {
  code: CanonicalSectorCode;
  label: string;
  description: string;
}

/**
 * Authoritative 5 canonical operating sectors in exact platform presentation order:
 * 1. Clean Cookstoves (COOKSTOVES)
 * 2. Hybrid Energy & Mini-grids (HYBRID_ENERGY)
 * 3. Biochar Carbon Removal (BIOCHAR)
 * 4. EV Mobility (EV_MOBILITY)
 * 5. Agriculture & Land Use (AGRICULTURE_LAND_USE)
 */
export const CANONICAL_OPERATING_SECTORS: readonly CanonicalSectorOption[] = [
  {
    code: "COOKSTOVES",
    label: "Clean Cookstoves",
    description: "Clean cooking appliances, improved cookstoves, and biomass fuel switching MRV",
  },
  {
    code: "HYBRID_ENERGY",
    label: "Hybrid Energy & Mini-grids",
    description: "Renewable mini-grids, solar-diesel hybrid systems, and clean energy displacement",
  },
  {
    code: "BIOCHAR",
    label: "Biochar Carbon Removal",
    description: "Biomass pyrolysis, durable carbon sequestration, and biochar removal crediting",
  },
  {
    code: "EV_MOBILITY",
    label: "EV Mobility",
    description: "Electric vehicle charging fleets, transport electrification, and fossil displacement",
  },
  {
    code: "AGRICULTURE_LAND_USE",
    label: "Agriculture & Land Use",
    description: "Agricultural land management, soil organic carbon stock, and regenerative agriculture",
  },
] as const;

export const CANONICAL_SECTOR_CODES: readonly CanonicalSectorCode[] = [
  "COOKSTOVES",
  "HYBRID_ENERGY",
  "BIOCHAR",
  "EV_MOBILITY",
  "AGRICULTURE_LAND_USE",
] as const;

export const CANONICAL_SECTOR_LABELS: Record<CanonicalSectorCode, string> = {
  COOKSTOVES: "Clean Cookstoves",
  HYBRID_ENERGY: "Hybrid Energy & Mini-grids",
  BIOCHAR: "Biochar Carbon Removal",
  EV_MOBILITY: "EV Mobility",
  AGRICULTURE_LAND_USE: "Agriculture & Land Use",
};

/**
 * Defensive getter returning deduplicated canonical sectors.
 * Enforces:
 * - Exactly 5 options
 * - 0 duplicate codes
 * - 0 duplicate labels
 * - 0 test fixture or methodology family labels
 */
export function getCanonicalOperatingSectors(): CanonicalSectorOption[] {
  const seenCodes = new Set<string>();
  const seenLabels = new Set<string>();
  const result: CanonicalSectorOption[] = [];

  for (const item of CANONICAL_OPERATING_SECTORS) {
    if (seenCodes.has(item.code)) {
      continue;
    }
    if (seenLabels.has(item.label)) {
      continue;
    }
    seenCodes.add(item.code);
    seenLabels.add(item.label);
    result.push({ ...item });
  }

  if (result.length !== 5) {
    throw new Error(
      `Invariant violation: Primary Operating Sector must expose exactly 5 options, found ${result.length}`
    );
  }

  return result;
}

/**
 * Validates whether a given string is a canonical sector code (case-insensitive).
 */
export function isCanonicalSectorCode(value: unknown): value is CanonicalSectorCode {
  if (typeof value !== "string") return false;
  const upper = value.trim().toUpperCase();
  return (CANONICAL_SECTOR_CODES as readonly string[]).includes(upper);
}

/**
 * Known legacy UUID mappings for canonical sectors.
 */
const LEGACY_SECTOR_UUIDS: Readonly<Record<string, CanonicalSectorCode>> = {
  // Cookstoves
  "ab748cb83b7c4e07aec7d1dc5f3dcf3a": "COOKSTOVES",
  "dff43d66631b4f088763aaab12d0d5ee": "COOKSTOVES",
  // Hybrid Energy
  "15fa60ccd06a4ef1ae140359e1bd3674": "HYBRID_ENERGY",
  "7f12bfe9b81c442dad523e9318adafaa": "HYBRID_ENERGY",
  // Biochar
  "d77b6543f0f14784a840cd77e0876a91": "BIOCHAR",
  "e6db7fbe94304ff599046caed0b94cce": "BIOCHAR",
  // EV Mobility
  "ab17ade7893844b1a24dbc797a65e056": "EV_MOBILITY",
  "867f684f722c4d2f8734113f4976840e": "EV_MOBILITY",
  // Agriculture & Land Use
  "9a7a437071e644f59870975823b8ccb9": "AGRICULTURE_LAND_USE",
};

/**
 * Resolves any sector input (canonical code, human-readable label, legacy UUID,
 * alias, access request payload object, or JSON-serialized string) to its
 * canonical human-readable label.
 *
 * Guaranteed NEVER to return a raw JSON string, object serialization, or UUID.
 */
export function resolveCanonicalSectorLabel(input: unknown): string {
  if (input === null || input === undefined) {
    return "Unknown sector";
  }

  // If input is an object (or partial access request record), extract potential sector fields
  if (typeof input === "object") {
    const obj = input as Record<string, unknown>;
    const candidates = [
      obj.sector_name,
      obj.SECTOR_NAME,
      obj.sector_label,
      obj.SECTOR_LABEL,
      obj.sector_code,
      obj.SECTOR_CODE,
      obj.sector_id,
      obj.SECTOR_ID,
      obj.sector,
      obj.SECTOR,
      obj.primary_operating_sector,
      obj.PRIMARY_OPERATING_SECTOR,
      obj.code,
      obj.CODE,
      obj.name,
      obj.NAME,
      obj.use_case,
      obj.USE_CASE,
    ];

    for (const cand of candidates) {
      if (cand && typeof cand !== "object") {
        const resolved = resolveCanonicalSectorLabel(cand);
        if (resolved !== "Unknown sector") {
          return resolved;
        }
      }
    }
    return "Unknown sector";
  }

  if (typeof input !== "string") {
    return "Unknown sector";
  }

  const trimmed = input.trim();
  if (!trimmed) {
    return "Unknown sector";
  }

  // If input is JSON-serialized (starts with '{' or '['), parse safely
  if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
    try {
      const parsed = JSON.parse(trimmed);
      if (parsed && typeof parsed === "object") {
        return resolveCanonicalSectorLabel(parsed);
      }
    } catch {
      // Non-JSON or malformed; do not echo raw string
    }
  }

  // Strip methodology suffix if present: e.g. "Agriculture & Land Use - VM0042" -> "Agriculture & Land Use"
  const baseSector = trimmed.includes(" - ") ? trimmed.split(" - ")[0].trim() : trimmed;

  // Direct check against canonical codes
  const upperBase = baseSector.toUpperCase();
  if ((CANONICAL_SECTOR_CODES as readonly string[]).includes(upperBase)) {
    return CANONICAL_SECTOR_LABELS[upperBase as CanonicalSectorCode];
  }

  // Direct check against canonical human labels
  for (const label of Object.values(CANONICAL_SECTOR_LABELS)) {
    if (label.toLowerCase() === baseSector.toLowerCase()) {
      return label;
    }
  }

  // Check known UUIDs (with or without hyphens)
  const normId = baseSector.replace(/-/g, "").toLowerCase();
  if (LEGACY_SECTOR_UUIDS[normId]) {
    return CANONICAL_SECTOR_LABELS[LEGACY_SECTOR_UUIDS[normId]];
  }

  // Semantic alias matching
  const cleaned = baseSector.toLowerCase().replace(/[\s\-_&]+/g, " ").trim();
  if (cleaned.includes("cookstove") || cleaned.includes("clean cook") || cleaned.includes("ams ii g") || cleaned.includes("ams-ii.g")) {
    return CANONICAL_SECTOR_LABELS.COOKSTOVES;
  }
  if (cleaned.includes("hybrid") || cleaned.includes("mini grid") || cleaned.includes("minigrid") || cleaned.includes("renewable energy") || cleaned.includes("ams i f") || cleaned.includes("ams-i.f")) {
    return CANONICAL_SECTOR_LABELS.HYBRID_ENERGY;
  }
  if (cleaned.includes("biochar") || cleaned.includes("pyrolysis") || cleaned.includes("vm0044")) {
    return CANONICAL_SECTOR_LABELS.BIOCHAR;
  }
  if (cleaned.includes("ev mobility") || cleaned.includes("electric vehicle") || cleaned.includes("electric mobility") || cleaned.includes("ev-mobility")) {
    return CANONICAL_SECTOR_LABELS.EV_MOBILITY;
  }
  if (cleaned.includes("agric") || cleaned.includes("afolu") || cleaned.includes("land use") || cleaned.includes("soil") || cleaned.includes("vm0042")) {
    return CANONICAL_SECTOR_LABELS.AGRICULTURE_LAND_USE;
  }

  // Fail-closed against JSON, UUIDs, or raw database keys leaking to UI
  if (/^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$/i.test(trimmed) || trimmed.includes("{") || trimmed.includes("}")) {
    return "Unknown sector";
  }

  return "Unknown sector";
}

/**
 * Returns the canonical human-readable label for a sector code, or fallback string.
 */
export function getCanonicalSectorLabel(code: string): string {
  const resolved = resolveCanonicalSectorLabel(code);
  return resolved !== "Unknown sector" ? resolved : code;
}

/**
 * Normalizes any sector representation (code, label, alias, UUID) to CanonicalSectorCode.
 */
export function normalizeToCanonicalSectorCode(input: unknown): CanonicalSectorCode | null {
  if (input === null || input === undefined) return null;
  if (typeof input !== "string") return null;

  const trimmed = input.trim();
  if (!trimmed) return null;

  const upper = trimmed.toUpperCase();
  if ((CANONICAL_SECTOR_CODES as readonly string[]).includes(upper)) {
    return upper as CanonicalSectorCode;
  }

  // Check known UUIDs
  const normId = trimmed.replace(/-/g, "").toLowerCase();
  if (LEGACY_SECTOR_UUIDS[normId]) {
    return LEGACY_SECTOR_UUIDS[normId];
  }

  // Check labels
  for (const [code, label] of Object.entries(CANONICAL_SECTOR_LABELS)) {
    if (label.toLowerCase() === trimmed.toLowerCase()) {
      return code as CanonicalSectorCode;
    }
  }

  // Check semantic aliases
  const cleaned = trimmed.toLowerCase().replace(/[\s\-_&]+/g, " ");
  if (cleaned.includes("cookstove") || cleaned.includes("clean cook")) return "COOKSTOVES";
  if (cleaned.includes("hybrid") || cleaned.includes("mini grid") || cleaned.includes("minigrid")) return "HYBRID_ENERGY";
  if (cleaned.includes("biochar") || cleaned.includes("pyrolysis")) return "BIOCHAR";
  if (cleaned.includes("ev mobility") || cleaned.includes("electric vehicle")) return "EV_MOBILITY";
  if (cleaned.includes("agric") || cleaned.includes("afolu") || cleaned.includes("land use")) return "AGRICULTURE_LAND_USE";

  return null;
}

export interface CanonicalMethodologyOption {
  id: string;
  code: string;
  name: string;
  registryCode: string;
  registryName: string;
  description: string;
  version?: string;
  currentVersion?: string;
  supportedVersions?: readonly string[];
  historicalVersions?: readonly string[];
  validFrom?: string;
  selectableForNewProjects?: boolean;
  officialSourceUrl?: string;
  sourceAuthority?: string;
  lastVerifiedAt?: string;
  subsector?: string;
  registryStatus?: "ACTIVE" | "INACTIVE" | "SUPERSEDED" | "UNDER_DEVELOPMENT";
  verifieldSupport?: "FULL" | "MRV_ONLY" | "CATALOG_ONLY" | "PLANNED" | "LEGACY";
  calculationEnabled?: boolean;
  applicabilitySummary?: string;
  stableIdentifier?: string;
  associatedModules?: readonly string[];
}

/**
 * Stale / legacy UUID aliases mapped to stable canonical methodology codes.
 */
export const STALE_METHODOLOGY_UUID_ALIASES: Readonly<Record<string, string>> = {
  "ec739cc0-517a-4fa0-9ff3-ed4cc6d17667": "VM0042",
  "61114e85-8b39-470f-8c4a-70b7ae098009": "VM0044",
  "61114e85-8b39-470f-8c4a-70b7ae098007": "PURO_BIOCHAR_2025",
  "fe2f48fe-e99b-44eb-8b2b-72b330317e6a": "VM0042",
  "a7fb17ce-1d2c-4eca-99f2-3c69beff96bd": "VM0050",
  "1beee93b-1960-4acd-92b4-60d2cef61daf": "VM0050",
};

/**
 * Authoritative production-enabled primary methodologies scoped per canonical sector.
 * Supporting modules/tools (e.g. VT0014, VMD0053, BM_T_001, VMD0049) are strictly excluded.
 */
export const CANONICAL_SECTOR_METHODOLOGIES: Record<CanonicalSectorCode, readonly CanonicalMethodologyOption[]> = {
  AGRICULTURE_LAND_USE: [
    {
      id: "f238258b-f8ec-4e5a-91cf-7537422796d3",
      code: "VM0042",
      name: "Improved Agricultural Land Management",
      registryCode: "VERRA",
      registryName: "Verra (VCS)",
      version: "2.2",
      currentVersion: "2.2",
      supportedVersions: ["2.2", "2.1"],
      historicalVersions: ["2.0", "1.0"],
      validFrom: "2023-11-20",
      selectableForNewProjects: true,
      officialSourceUrl: "https://verra.org/methodologies/vm0042-improved-agricultural-land-management-v2-2/",
      sourceAuthority: "Verra",
      lastVerifiedAt: "2026-10-11",
      subsector: "Cropland / Soil Carbon / Improved Agricultural Land Management",
      registryStatus: "ACTIVE",
      verifieldSupport: "FULL",
      calculationEnabled: true,
      applicabilitySummary: "Quantifies GHG reductions and SOC removals from improved agricultural practices (e.g., reduced tillage, cover crops, improved nutrient management, organic amendments) on croplands and grasslands.",
      stableIdentifier: "VERRA:VM0042:2.2",
      description: "Quantifies greenhouse gas emission reductions and carbon dioxide removals resulting from the adoption of improved agricultural land management practices.",
      associatedModules: ["VT0014", "VMD0053", "VMD0054"],
    },
    {
      id: "615f5d40-f86a-4fdb-af23-d9f79d90d159",
      code: "VM0051",
      name: "Improved Management in Rice Production Systems",
      registryCode: "VERRA",
      registryName: "Verra (VCS)",
      version: "1.1",
      currentVersion: "1.1",
      supportedVersions: ["1.1"],
      historicalVersions: ["1.0"],
      validFrom: "2024-06-27",
      selectableForNewProjects: true,
      officialSourceUrl: "https://verra.org/methodologies/vm0051-improved-management-in-rice-production-systems-v1-1/",
      sourceAuthority: "Verra",
      lastVerifiedAt: "2026-10-11",
      subsector: "Rice Cultivation / Flooded Rice Water Management",
      registryStatus: "ACTIVE",
      verifieldSupport: "MRV_ONLY",
      calculationEnabled: false,
      applicabilitySummary: "Flooded rice systems implementing improved water regimes (e.g., alternate wetting and drying — AWD, multiple drainage) and organic residue management.",
      stableIdentifier: "VERRA:VM0051:1.1",
      description: "Quantifies emission reductions from reduced methane emissions in flooded rice production through water management and straw practices.",
    },
    {
      id: "9cc408db-c2bd-4df3-b488-44e8cff7fb73",
      code: "VM0047",
      name: "Afforestation, Reforestation, and Revegetation",
      registryCode: "VERRA",
      registryName: "Verra (VCS)",
      version: "1.1",
      currentVersion: "1.1",
      supportedVersions: ["1.1"],
      historicalVersions: ["1.0"],
      validFrom: "2024-09-05",
      selectableForNewProjects: true,
      officialSourceUrl: "https://verra.org/methodologies/vm0047-afforestation-reforestation-and-revegetation-v1-1/",
      sourceAuthority: "Verra",
      lastVerifiedAt: "2026-10-11",
      subsector: "ARR / Afforestation, Reforestation & Revegetation",
      registryStatus: "ACTIVE",
      verifieldSupport: "MRV_ONLY",
      calculationEnabled: false,
      applicabilitySummary: "ARR and revegetation activities establishing forest cover on non-forest land meeting minimum crown cover, tree height, and national forest definition criteria.",
      stableIdentifier: "VERRA:VM0047:1.1",
      description: "Afforestation, reforestation, and revegetation on eligible non-wetland lands.",
    },
    {
      id: "d6956c93-80ea-4763-9354-b7c6a84e7bbc",
      code: "VM0032",
      name: "Methodology for the Adoption of Sustainable Grasslands through Adjustment of Fire and Grazing",
      registryCode: "VERRA",
      registryName: "Verra (VCS)",
      version: "1.0",
      currentVersion: "1.0",
      supportedVersions: ["1.0"],
      historicalVersions: [],
      validFrom: "2015-09-24",
      selectableForNewProjects: true,
      officialSourceUrl: "https://verra.org/methodologies/vm0032-methodology-for-the-adoption-of-sustainable-grasslands-v1-0/",
      sourceAuthority: "Verra",
      lastVerifiedAt: "2026-10-11",
      subsector: "Grasslands / Fire & Grazing Management",
      registryStatus: "ACTIVE",
      verifieldSupport: "CATALOG_ONLY",
      calculationEnabled: false,
      applicabilitySummary: "Applicable to grassland systems where fire regime and livestock grazing pressure are adjusted to increase carbon stocks and reduce emissions.",
      stableIdentifier: "VERRA:VM0032:1.0",
      description: "Adoption of sustainable grassland practices through adjustment of fire and grazing regimes.",
    },
  ],
  BIOCHAR: [
    {
      id: "cd093f0e-0353-449e-a56b-484398ea0f9e",
      code: "VM0044",
      name: "Biochar Utilization in Soil and Non-Soil Applications",
      registryCode: "VERRA",
      registryName: "Verra (VCS)",
      version: "1.2",
      currentVersion: "1.2",
      supportedVersions: ["1.2", "1.1.0"],
      historicalVersions: ["1.0"],
      validFrom: "2024-08-15",
      selectableForNewProjects: true,
      officialSourceUrl: "https://verra.org/methodologies/vm0044-methodology-for-biochar-utilization-in-soil-and-non-soil-applications-v1-2/",
      sourceAuthority: "Verra",
      lastVerifiedAt: "2026-10-11",
      subsector: "Biomass Pyrolysis / Soil & Material Sequestration",
      registryStatus: "ACTIVE",
      verifieldSupport: "FULL",
      calculationEnabled: true,
      applicabilitySummary: "Biochar carbon removal through sustainable biomass pyrolysis and durable soil or non-soil utilization.",
      stableIdentifier: "VERRA:VM0044:1.2",
      description: "Biochar carbon removal through sustainable biomass pyrolysis and durable soil or non-soil utilization.",
    },
    {
      id: "803127f7-2ef1-464e-8d95-55ba37ff9b17",
      code: "PURO_BIOCHAR_2025",
      name: "Puro Standard Biochar Methodology",
      registryCode: "PURO_STANDARD",
      registryName: "Puro.earth Standard",
      version: "Edition 2025 v2",
      currentVersion: "Edition 2025 v2",
      supportedVersions: ["Edition 2025 v2"],
      historicalVersions: ["Edition 2024", "Edition 2022"],
      validFrom: "2025-01-01",
      selectableForNewProjects: true,
      officialSourceUrl: "https://puro.earth/biochar-methodology/",
      sourceAuthority: "Puro.earth Standard",
      lastVerifiedAt: "2026-10-11",
      subsector: "Engineered Carbon Removal / CORC",
      registryStatus: "ACTIVE",
      verifieldSupport: "FULL",
      calculationEnabled: true,
      applicabilitySummary: "Engineered biochar carbon removal crediting under the Puro Standard with independent lab verification.",
      stableIdentifier: "PURO_STANDARD:PURO_BIOCHAR_2025:2025",
      description: "Engineered biochar carbon removal crediting under the Puro Standard.",
    },
    {
      id: "8a2c728e-6a3c-5391-ba57-7da1af43c634",
      code: "BIOCHAR_C_SINK",
      name: "Global Biochar C-Sink Standard",
      registryCode: "CSI",
      registryName: "Carbon Standards International",
      version: "3.3",
      currentVersion: "3.3",
      supportedVersions: ["3.3"],
      historicalVersions: ["3.2", "3.1"],
      validFrom: "2024-01-15",
      selectableForNewProjects: true,
      officialSourceUrl: "https://www.carbon-standards.com/en/standards/global-biochar-c-sink-standard/",
      sourceAuthority: "Carbon Standards International",
      lastVerifiedAt: "2026-10-11",
      subsector: "Global & European Biochar Carbon Sink",
      registryStatus: "ACTIVE",
      verifieldSupport: "CATALOG_ONLY",
      calculationEnabled: false,
      applicabilitySummary: "Certification of biochar carbon sinks following European Biochar Certificate (EBC) and World Biochar Certificate guidelines with end-use tracking.",
      stableIdentifier: "CSI:BIOCHAR_C_SINK:3.3",
      description: "Standard for certifying the climate impact of biochar carbon sink creation.",
    },
  ],
  COOKSTOVES: [
    {
      id: "183ce6d6-d193-41ca-be0e-1096e1971c69",
      code: "GS_MECD",
      name: "Metered & Measured Energy Cooking Devices",
      registryCode: "GOLD_STANDARD",
      registryName: "Gold Standard for the Global Goals",
      version: "2.0",
      currentVersion: "2.0",
      supportedVersions: ["2.0"],
      historicalVersions: ["1.0"],
      validFrom: "2023-04-12",
      selectableForNewProjects: true,
      officialSourceUrl: "https://www.goldstandard.org/project-developer-platform/rules-and-requirements/methodologies/metered-and-measured-energy-cooking-devices",
      sourceAuthority: "Gold Standard for the Global Goals",
      lastVerifiedAt: "2026-10-11",
      subsector: "Metered Cooking Devices / IoT Thermal MRV",
      registryStatus: "ACTIVE",
      verifieldSupport: "MRV_ONLY",
      calculationEnabled: false,
      applicabilitySummary: "Projects deploying metered electric, biogas, LPG, or metered biomass cooking devices using automated data logging / IoT smart metering to quantify cooking energy directly.",
      stableIdentifier: "GOLD_STANDARD:GS_MECD:2.0",
      description: "Gold Standard methodology for metered and measured energy cooking devices utilizing high-frequency digital IoT monitoring.",
    },
    {
      id: "a7fb17ce-1d2c-4eca-99f2-3c69beff96bd",
      code: "VM0050",
      name: "Methodology for Improved Cookstoves",
      registryCode: "VERRA",
      registryName: "Verra (VCS)",
      version: "1.0",
      currentVersion: "1.0",
      supportedVersions: ["1.0"],
      historicalVersions: [],
      validFrom: "2024-03-27",
      selectableForNewProjects: true,
      officialSourceUrl: "https://verra.org/methodologies/vm0050-methodology-for-improved-cookstoves-v1-0/",
      sourceAuthority: "Verra",
      lastVerifiedAt: "2026-10-11",
      subsector: "Efficient Cookstoves / Biomass Fuel Efficiency",
      registryStatus: "ACTIVE",
      verifieldSupport: "CATALOG_ONLY",
      calculationEnabled: false,
      applicabilitySummary: "Distribution of improved cookstoves that displace non-renewable biomass in domestic or institutional thermal cooking applications, superseding VM0006 under VCS.",
      stableIdentifier: "VERRA:VM0050:1.0",
      description: "Verra VCS methodology for improved cookstoves displacing non-renewable biomass.",
    },
    {
      id: "9bd46fe2-5b2e-45a8-9c9c-5b761bdc6b98",
      code: "AMS_II_G",
      name: "Energy Efficiency Measures in Thermal Applications of Non-Renewable Biomass",
      registryCode: "UNFCCC_CDM",
      registryName: "UNFCCC Clean Development Mechanism",
      version: "14.0",
      currentVersion: "14.0",
      supportedVersions: ["14.0"],
      historicalVersions: ["13.0", "12.0", "11.0", "10.0"],
      validFrom: "2025-06-12",
      selectableForNewProjects: true,
      officialSourceUrl: "https://cdm.unfccc.int/methodologies/SSCmethodologies/approved",
      sourceAuthority: "UNFCCC CDM Executive Board",
      lastVerifiedAt: "2026-10-11",
      subsector: "Thermal Biomass Efficiency / Improved Cookstoves",
      registryStatus: "ACTIVE",
      verifieldSupport: "CATALOG_ONLY",
      calculationEnabled: false,
      applicabilitySummary: "Small-scale methodology for introduction of high-efficiency biomass stoves displacing non-renewable biomass in domestic or commercial applications.",
      stableIdentifier: "UNFCCC:AMS-II.G:14.0",
      description: "UNFCCC small-scale methodology for energy efficiency measures in thermal applications of non-renewable biomass.",
    },
  ],
  HYBRID_ENERGY: [
    {
      id: "b007c7e9-2f2a-4155-85ae-371d66c97152",
      code: "AMS_I_F",
      name: "Renewable Electricity Generation for Captive Use and Mini-grid",
      registryCode: "UNFCCC_CDM",
      registryName: "UNFCCC Clean Development Mechanism",
      version: "5.0",
      currentVersion: "5.0",
      supportedVersions: ["5.0"],
      historicalVersions: ["4.0", "3.0", "2.0", "1.0"],
      validFrom: "2022-09-08",
      selectableForNewProjects: true,
      officialSourceUrl: "https://cdm.unfccc.int/methodologies/DB/XKCRT4QQUUWXXZMQRXUGES0WON451M",
      sourceAuthority: "UNFCCC CDM Executive Board",
      lastVerifiedAt: "2026-10-11",
      subsector: "Mini-grids / Captive Renewable Generation",
      registryStatus: "ACTIVE",
      verifieldSupport: "MRV_ONLY",
      calculationEnabled: false,
      applicabilitySummary: "Installations of renewable electricity generation facilities supplying captive consumers or mini-grid distribution systems, displacing fossil-fuel-based grid electricity or local diesel generators.",
      stableIdentifier: "UNFCCC:AMS-I.F:5.0",
      description: "UNFCCC small-scale methodology for renewable electricity generation for captive use and mini-grid systems.",
    },
    {
      id: "cfed120a-8ed3-554d-9bfa-86e62b8fd4cf",
      code: "AMS_I_L",
      name: "Electrification of Rural Communities Using Renewable Energy",
      registryCode: "UNFCCC_CDM",
      registryName: "UNFCCC Clean Development Mechanism",
      version: "5.0",
      currentVersion: "5.0",
      supportedVersions: ["5.0"],
      historicalVersions: ["4.0", "3.0", "2.0", "1.0"],
      validFrom: "2024-03-22",
      selectableForNewProjects: true,
      officialSourceUrl: "https://cdm.unfccc.int/methodologies/DB/7LB4TLJF6F0ZQQ07C91ND2EOLC0WPK/",
      sourceAuthority: "UNFCCC CDM Executive Board",
      lastVerifiedAt: "2026-10-11",
      subsector: "Rural Electrification / Solar Home Systems",
      registryStatus: "ACTIVE",
      verifieldSupport: "CATALOG_ONLY",
      calculationEnabled: false,
      applicabilitySummary: "Renewable energy systems (e.g. solar home systems, micro-hydro) providing electricity to rural households and communities with no previous grid connection.",
      stableIdentifier: "UNFCCC:AMS-I.L:5.0",
      description: "UNFCCC small-scale methodology for electrification of rural communities using renewable energy systems.",
    },
    {
      id: "4b131d9b-3d26-5870-aa53-c97fd58b8020",
      code: "ACM0002",
      name: "Grid-Connected Electricity Generation from Renewable Sources",
      registryCode: "UNFCCC_CDM",
      registryName: "UNFCCC Clean Development Mechanism",
      version: "22.0",
      currentVersion: "22.0",
      supportedVersions: ["22.0"],
      historicalVersions: [
        "21.0", "20.0", "19.0", "18.0", "17.0", "16.0", "15.0", "14.0", "13.0",
        "12.0", "11.0", "10.0", "9.0", "8.0", "7.0", "6.0", "5.0", "4.0", "3.0", "2.0", "1.0"
      ],
      validFrom: "2024-05-31",
      selectableForNewProjects: true,
      officialSourceUrl: "https://cdm.unfccc.int/methodologies/DB/XB1TX7TAZ6SLWM9B7BC67THHVD16JV",
      sourceAuthority: "UNFCCC CDM Executive Board",
      lastVerifiedAt: "2026-10-11",
      subsector: "Grid-Connected Renewable Energy",
      registryStatus: "ACTIVE",
      verifieldSupport: "CATALOG_ONLY",
      calculationEnabled: false,
      applicabilitySummary: "Large-scale grid-connected renewable power generation plants supplying electricity to national or regional utility grids.",
      stableIdentifier: "UNFCCC:ACM0002:22.0",
      description: "Consolidated baseline methodology for grid-connected electricity generation from renewable sources.",
    },
  ],
  EV_MOBILITY: [
    {
      id: "f835e2ce-630d-4479-97ad-ef0a25e405af",
      code: "VM0038",
      name: "Methodology for Electric Vehicle Charging Systems",
      registryCode: "VERRA",
      registryName: "Verra (VCS)",
      version: "1.1",
      currentVersion: "1.1",
      supportedVersions: ["1.1"],
      historicalVersions: ["1.0"],
      validFrom: "2022-09-08",
      selectableForNewProjects: true,
      officialSourceUrl: "https://verra.org/methodologies/vm0038-methodology-for-electric-vehicle-charging-systems-v1-1/",
      sourceAuthority: "Verra",
      lastVerifiedAt: "2026-10-11",
      subsector: "EV Charging Infrastructure / Transport Electrification",
      registryStatus: "ACTIVE",
      verifieldSupport: "MRV_ONLY",
      calculationEnabled: false,
      applicabilitySummary: "Quantifies emission reductions from displacement of internal combustion engine vehicles through electricity supplied by grid-connected or renewable EV charging stations.",
      stableIdentifier: "VERRA:VM0038:1.1",
      description: "Verra VCS methodology for electric vehicle charging systems.",
      associatedModules: ["VMD0049"],
    },
    {
      id: "0cb3d677-647e-4873-8d31-d7c0c567d903",
      code: "AMS_III_C",
      name: "Emission Reductions by Electric and Hybrid Vehicles",
      registryCode: "UNFCCC_CDM",
      registryName: "UNFCCC Clean Development Mechanism",
      version: "16.0",
      currentVersion: "16.0",
      supportedVersions: ["16.0"],
      historicalVersions: [
        "15.0", "14.0", "13.0", "12.0", "11.0", "10.0", "9.0", "8.0", "7.0",
        "6.0", "5.0", "4.0", "3.0", "2.0", "1.0"
      ],
      validFrom: "2022-09-08",
      selectableForNewProjects: true,
      officialSourceUrl: "https://cdm.unfccc.int/methodologies/DB/HLOH5R7J6M96A23TFECTQ1BVIE24CK/",
      sourceAuthority: "UNFCCC CDM Executive Board",
      lastVerifiedAt: "2026-10-11",
      subsector: "Low-GHG Vehicle Fleets / Electric Transport",
      registryStatus: "ACTIVE",
      verifieldSupport: "CATALOG_ONLY",
      calculationEnabled: false,
      applicabilitySummary: "Commercial fleets, public transit buses, or passenger vehicles replacing conventional fossil-fueled vehicles with electric or hybrid vehicles.",
      stableIdentifier: "UNFCCC:AMS-III.C:16.0",
      description: "UNFCCC small-scale methodology for emission reductions by electric and hybrid vehicle fleets.",
    },
  ],
};

// Supporting modules and tools that must NEVER be surfaced as primary project methodologies
export const DISALLOWED_PRIMARY_METHODOLOGY_CODES: ReadonlySet<string> = new Set([
  "VT0014",
  "VMD0053",
  "VMD0054",
  "BM_T_001",
  "GS_AGRI_ACT_REQ",
  "VMD0049",
]);

// Methodologies whose calculation pathways remain unconfigured / reference-only (not production-ready)
export const UNCONFIGURED_METHODOLOGY_CODES: ReadonlySet<string> = new Set([
  // Cookstoves
  "AMS_II_G",
  "VM0006",
  "VM0050",
  "VMR0050",
  "GS_TPDDTEC",
  "GS_MECD",
  // Hybrid Energy
  "AMS_I_F",
  "AMS_I_L",
  "ACM0002",
  "CI_GRID_DISPLACEMENT",
  "ENERGY_DISPLACEMENT",
  "MINIGRID_DIESEL_DISPLACEMENT",
  "SHS_RENEWABLE_DISPLACEMENT",
  // EV Mobility
  "AMS_III_C",
  "VM0038",
  "EV_DISPLACEMENT",
  // Biochar
  "BIOCHAR_C_SINK",
  "EBC_BIOCHAR",
  "GS_BIOCHAR",
  // Agriculture
  "VM0051",
  "VM0047",
  "VM0032",
]);

/**
 * Returns authorized primary methodologies for a canonical sector.
 * Returns an empty array if the sector is unselected or unrecognized.
 */
export function getCanonicalMethodologiesForSector(sectorInput: unknown): CanonicalMethodologyOption[] {
  const code = normalizeToCanonicalSectorCode(sectorInput);
  if (!code || !CANONICAL_SECTOR_METHODOLOGIES[code]) {
    return [];
  }
  return [...CANONICAL_SECTOR_METHODOLOGIES[code]];
}

/**
 * Checks whether a methodology code or ID is valid for the given sector.
 */
export function isMethodologyCompatibleWithSector(
  sectorInput: unknown,
  methodologyCodeOrId: string
): boolean {
  const code = normalizeToCanonicalSectorCode(sectorInput);
  if (!code) return false;

  const clean = methodologyCodeOrId.trim();
  const cleanLower = clean.toLowerCase();

  // Check stale aliases
  const resolvedCode = STALE_METHODOLOGY_UUID_ALIASES[cleanLower] || clean;
  let cleanUpper = resolvedCode.toUpperCase().replace(/[-.\s]/g, "_");
  if (cleanUpper === "VMR0050" || cleanUpper === "VM0006") cleanUpper = "VM0050";
  if (cleanUpper === "PURO_BIOCHAR_2025_V2" || cleanUpper === "PURO_BIOCHAR" || cleanUpper.startsWith("PURO_BIOCHAR_2025_V2_")) cleanUpper = "PURO_BIOCHAR_2025";

  if (DISALLOWED_PRIMARY_METHODOLOGY_CODES.has(cleanUpper)) {
    return false;
  }

  const validMeths = CANONICAL_SECTOR_METHODOLOGIES[code] || [];

  return validMeths.some(
    (m) =>
      m.id.toLowerCase() === cleanLower ||
      m.code.toUpperCase() === cleanUpper ||
      m.code.replace(/[-.\s]/g, "_").toUpperCase() === cleanUpper
  );
}

/**
 * Validates whether a specified methodology version is allowed for NEW project selection.
 */
export function isMethodologyVersionSelectableForNewProjects(
  codeOrId: string,
  version?: string
): { selectable: boolean; error?: string; activeVersion: string } {
  if (!codeOrId) {
    return { selectable: true, activeVersion: "" };
  }

  const clean = codeOrId.trim();
  const cleanLower = clean.toLowerCase();
  const resolvedCode = STALE_METHODOLOGY_UUID_ALIASES[cleanLower] || clean;
  let cleanUpper = resolvedCode.toUpperCase().replace(/[-.\s]/g, "_");
  if (cleanUpper === "VMR0050" || cleanUpper === "VM0006") cleanUpper = "VM0050";
  if (cleanUpper === "PURO_BIOCHAR_2025_V2" || cleanUpper === "PURO_BIOCHAR" || cleanUpper.startsWith("PURO_BIOCHAR_2025_V2_")) cleanUpper = "PURO_BIOCHAR_2025";

  let match: CanonicalMethodologyOption | undefined;
  for (const list of Object.values(CANONICAL_SECTOR_METHODOLOGIES)) {
    match = list.find(
      (m) =>
        m.id.toLowerCase() === cleanLower ||
        m.code.toUpperCase() === cleanUpper ||
        m.code.replace(/[-.\s]/g, "_").toUpperCase() === cleanUpper ||
        (m.stableIdentifier && m.stableIdentifier.toUpperCase() === clean.toUpperCase())
    );
    if (match) break;
  }

  if (!match) {
    return { selectable: true, activeVersion: version || "" };
  }

  const curVersion = match.version || "1.0";
  if (!version || version.trim() === "") {
    return { selectable: true, activeVersion: curVersion };
  }

  const reqVer = version.trim();
  const reqVerLower = reqVer.toLowerCase();
  const supported = (match.supportedVersions || [curVersion]).map((v) => v.toLowerCase());
  const historical = (match.historicalVersions || []).map((v) => v.toLowerCase());

  if (supported.includes(reqVerLower) || reqVerLower === curVersion.toLowerCase()) {
    return { selectable: true, activeVersion: reqVer };
  }

  if (historical.includes(reqVerLower)) {
    return {
      selectable: false,
      error: `Version '${reqVer}' of ${match.code} is historical/inactive and cannot be selected for new projects. Active version is ${curVersion}.`,
      activeVersion: curVersion,
    };
  }

  return {
    selectable: false,
    error: `Version '${reqVer}' is not a recognized version of ${match.code}. Active version is ${curVersion}.`,
    activeVersion: curVersion,
  };
}
