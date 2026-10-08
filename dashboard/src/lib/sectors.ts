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
