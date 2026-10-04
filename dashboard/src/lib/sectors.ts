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
 * Returns the canonical human-readable label for a sector code, or fallback string.
 */
export function getCanonicalSectorLabel(code: string): string {
  const upper = code.trim().toUpperCase() as CanonicalSectorCode;
  return CANONICAL_SECTOR_LABELS[upper] || code;
}
