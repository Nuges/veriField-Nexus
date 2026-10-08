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
}

/**
 * Authoritative production-enabled primary methodologies scoped per canonical sector.
 * Supporting modules/tools (e.g. VT0014, VMD0053, BM_T_001) are strictly excluded.
 */
export const CANONICAL_SECTOR_METHODOLOGIES: Record<CanonicalSectorCode, readonly CanonicalMethodologyOption[]> = {
  AGRICULTURE_LAND_USE: [
    {
      id: "ec739cc0-517a-4fa0-9ff3-ed4cc6d17667",
      code: "VM0042",
      name: "Improved Agricultural Land Management",
      registryCode: "VERRA",
      registryName: "Verra (VCS)",
      version: "2.2",
      description: "Quantifies greenhouse gas emission reductions and carbon dioxide removals resulting from the adoption of improved agricultural land management practices.",
    },
  ],
  BIOCHAR: [
    {
      id: "61114e85-8b39-470f-8c4a-70b7ae098009",
      code: "VM0044",
      name: "Biochar Utilization in Soil and Non-Soil Applications",
      registryCode: "VERRA",
      registryName: "Verra (VCS)",
      version: "1.2",
      description: "Biochar carbon removal through sustainable biomass pyrolysis and durable soil or non-soil utilization.",
    },
    {
      id: "61114e85-8b39-470f-8c4a-70b7ae098008",
      code: "BIOCHAR_C_SINK",
      name: "Biochar Carbon Sink",
      registryCode: "CSI",
      registryName: "Carbon Standards International",
      version: "1.0.0",
      description: "Standard for carbon sink certification through biochar application.",
    },
    {
      id: "61114e85-8b39-470f-8c4a-70b7ae098007",
      code: "PURO_BIOCHAR_2025",
      name: "Puro Standard Biochar Methodology",
      registryCode: "PURO_STANDARD",
      registryName: "Puro.earth Standard",
      version: "2025",
      description: "Engineered biochar carbon removal crediting under the Puro Standard.",
    },
    {
      id: "61114e85-8b39-470f-8c4a-70b7ae098006",
      code: "EBC_BIOCHAR",
      name: "European Biochar Certificate",
      registryCode: "CSI",
      registryName: "Carbon Standards International",
      version: "1.0.0",
      description: "European standard for sustainable production and carbon sink certification of biochar.",
    },
    {
      id: "61114e85-8b39-470f-8c4a-70b7ae098005",
      code: "GS_BIOCHAR",
      name: "Gold Standard Biochar Methodology",
      registryCode: "GOLD_STANDARD",
      registryName: "Gold Standard (GS)",
      version: "1.0.0",
      description: "Gold Standard methodology for biochar production and application.",
    },
  ],
  COOKSTOVES: [
    {
      id: "4685d816-3d51-4cdd-85f1-8c6aab3c50a1",
      code: "AMS_II_G",
      name: "Energy Efficiency in Thermal Applications",
      registryCode: "CDM",
      registryName: "Clean Development Mechanism",
      version: "1.0.0",
      description: "CDM methodology for energy efficiency in thermal applications including household improved cookstoves.",
    },
    {
      id: "4685d816-3d51-4cdd-85f1-8c6aab3c50a2",
      code: "GS_MECD",
      name: "Metered Energy Cooking Devices",
      registryCode: "GOLD_STANDARD",
      registryName: "Gold Standard (GS)",
      version: "3.0",
      description: "Quantification for electric and metered cooking devices displacing biomass.",
    },
    {
      id: "4685d816-3d51-4cdd-85f1-8c6aab3c50a3",
      code: "GS_TPDDTEC",
      name: "Displace Decentralized Thermal Energy",
      registryCode: "GOLD_STANDARD",
      registryName: "Gold Standard (GS)",
      version: "4.0",
      description: "Thermal energy applications displacing woody biomass.",
    },
    {
      id: "4685d816-3d51-4cdd-85f1-8c6aab3c50a4",
      code: "VM0006",
      name: "Fuel Switching (Cookstoves)",
      registryCode: "VERRA",
      registryName: "Verra (VCS)",
      version: "1.0.0",
      description: "Switching from non-renewable biomass to renewable cooking fuels.",
    },
    {
      id: "4685d816-3d51-4cdd-85f1-8c6aab3c50a5",
      code: "VMR0050",
      name: "Thermal Energy Displacement",
      registryCode: "VERRA",
      registryName: "Verra (VCS)",
      version: "1.0.0",
      description: "Displacement of non-renewable fossil or biomass energy with clean thermal appliances.",
    },
  ],
  HYBRID_ENERGY: [
    {
      id: "e1074ae1-c76c-47c7-a5de-0241d44031f1",
      code: "AMS_I_F",
      name: "Renewable Electricity for Captive Use",
      registryCode: "CDM",
      registryName: "Clean Development Mechanism",
      version: "1.0.0",
      description: "Renewable electricity generation displacing fossil fuel generators and captive mini-grids.",
    },
    {
      id: "e1074ae1-c76c-47c7-a5de-0241d44031f2",
      code: "CI_GRID_DISPLACEMENT",
      name: "C&I Grid Displacement",
      registryCode: "CDM",
      registryName: "Clean Development Mechanism",
      version: "1.0.0",
      description: "Commercial & Industrial solar installations displacing grid and diesel power.",
    },
    {
      id: "e1074ae1-c76c-47c7-a5de-0241d44031f3",
      code: "ENERGY_DISPLACEMENT",
      name: "Renewable Energy Displacement",
      registryCode: "CDM",
      registryName: "Clean Development Mechanism",
      version: "1.0.0",
      description: "Clean energy displacement of fossil generators across distributed assets.",
    },
    {
      id: "e1074ae1-c76c-47c7-a5de-0241d44031f4",
      code: "MINIGRID_DIESEL_DISPLACEMENT",
      name: "Mini-Grid Diesel Displacement",
      registryCode: "CDM",
      registryName: "Clean Development Mechanism",
      version: "1.0.0",
      description: "Community solar mini-grids displacing baseline diesel gensets.",
    },
    {
      id: "e1074ae1-c76c-47c7-a5de-0241d44031f5",
      code: "SHS_RENEWABLE_DISPLACEMENT",
      name: "Solar Home System Displacement",
      registryCode: "CDM",
      registryName: "Clean Development Mechanism",
      version: "1.0.0",
      description: "Distributed solar home systems for off-grid households displacing kerosene and diesel.",
    },
    {
      id: "e1074ae1-c76c-47c7-a5de-0241d44031f6",
      code: "ACM0002",
      name: "Grid-Connected Renewable Electricity Generation",
      registryCode: "CDM",
      registryName: "Clean Development Mechanism",
      version: "1.0.0",
      description: "Grid-connected electricity generation from renewable sources displacing baseline fossil fuel generation.",
    },
  ],
  EV_MOBILITY: [
    {
      id: "30592386-cdc7-4c42-a003-bc8aa7191aa1",
      code: "EV_DISPLACEMENT",
      name: "EV Fossil Fuel Displacement",
      registryCode: "CDM",
      registryName: "Clean Development Mechanism",
      version: "1.0.0",
      description: "Electric vehicle transport systems and fleets displacing internal combustion engines.",
    },
    {
      id: "30592386-cdc7-4c42-a003-bc8aa7191aa2",
      code: "AMS_III_C",
      name: "Emission Reductions by Low-GHG Vehicles",
      registryCode: "CDM",
      registryName: "Clean Development Mechanism",
      version: "1.0.0",
      description: "Low-greenhouse gas emission vehicles for public and commercial transport fleets.",
    },
    {
      id: "30592386-cdc7-4c42-a003-bc8aa7191aa3",
      code: "VM0038",
      name: "Electric Vehicle Charging Systems",
      registryCode: "VERRA",
      registryName: "Verra (VCS)",
      version: "1.0.0",
      description: "Quantifies emission reductions from the deployment of EV charging infrastructure.",
    },
  ],
};

// Supporting modules and tools that must NEVER be surfaced as primary project methodologies
export const DISALLOWED_PRIMARY_METHODOLOGY_CODES: ReadonlySet<string> = new Set([
  "VT0014",
  "VMD0053",
  "BM_T_001",
  "GS_AGRI_ACT_REQ",
]);

// Unconfigured methodologies
export const UNCONFIGURED_METHODOLOGY_CODES: ReadonlySet<string> = new Set([
  "VM0047",
  "VM0051",
  "VM0032",
  "VM0041",
  "BM_AG04_001",
  "BM_AG04_002",
  "BM_FR05_002",
]);

/**
 * Returns authorized production-enabled primary methodologies for a canonical sector.
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

  const validMeths = CANONICAL_SECTOR_METHODOLOGIES[code] || [];
  const clean = methodologyCodeOrId.trim();
  const cleanUpper = clean.toUpperCase();
  const cleanLower = clean.toLowerCase();

  return validMeths.some(
    (m) =>
      m.id.toLowerCase() === cleanLower ||
      m.code.toUpperCase() === cleanUpper ||
      m.code.replace(/-/g, "_").toUpperCase() === cleanUpper.replace(/-/g, "_")
  );
}
