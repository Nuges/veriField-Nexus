import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {
  getCanonicalOperatingSectors,
  getCanonicalMethodologiesForSector,
  isMethodologyCompatibleWithSector,
  normalizeToCanonicalSectorCode,
  CANONICAL_SECTOR_METHODOLOGIES,
  DISALLOWED_PRIMARY_METHODOLOGY_CODES,
  UNCONFIGURED_METHODOLOGY_CODES,
  CanonicalSectorCode,
} from "../src/lib/sectors";

test("Onboarding Methodology Scoping: Agriculture & Land Use exposes ONLY VM0042", () => {
  const agriMeths = getCanonicalMethodologiesForSector("AGRICULTURE_LAND_USE");
  assert.equal(agriMeths.length, 1, `Expected exactly 1 production methodology for agriculture, got ${agriMeths.length}`);
  assert.equal(agriMeths[0].code, "VM0042");
  assert.equal(agriMeths[0].name, "Improved Agricultural Land Management");
  assert.equal(agriMeths[0].registryCode, "VERRA");

  // Supporting modules and tools must NEVER be exposed
  const codes = agriMeths.map((m) => m.code);
  for (const tool of DISALLOWED_PRIMARY_METHODOLOGY_CODES) {
    assert.equal(codes.includes(tool), false, `Disallowed tool '${tool}' must not be present in Agriculture`);
  }
  for (const unconf of UNCONFIGURED_METHODOLOGY_CODES) {
    assert.equal(codes.includes(unconf), false, `Unconfigured methodology '${unconf}' must not be present in Agriculture`);
  }
});

test("Onboarding Methodology Scoping: Zero cross-sector leakage across all 5 sectors", () => {
  const allSectors = getCanonicalOperatingSectors();
  assert.equal(allSectors.length, 5);

  const sectorMethodologyCodes = new Map<CanonicalSectorCode, Set<string>>();
  for (const sec of allSectors) {
    const meths = getCanonicalMethodologiesForSector(sec.code);
    assert.ok(meths.length >= 1, `Sector ${sec.code} must have at least 1 production methodology`);
    sectorMethodologyCodes.set(sec.code, new Set(meths.map((m) => m.code)));
  }

  // Cross-sector uniqueness: No methodology should belong to more than one sector
  const seenCodes = new Map<string, CanonicalSectorCode>();
  for (const [secCode, codeSet] of sectorMethodologyCodes.entries()) {
    for (const methCode of codeSet) {
      const existing = seenCodes.get(methCode);
      assert.equal(
        existing,
        undefined,
        `Methodology code '${methCode}' appears in multiple sectors: '${existing}' and '${secCode}'`
      );
      seenCodes.set(methCode, secCode);
    }
  }
});

test("Onboarding Methodology Scoping: isMethodologyCompatibleWithSector validation", () => {
  // Agriculture tests
  assert.equal(isMethodologyCompatibleWithSector("AGRICULTURE_LAND_USE", "VM0042"), true);
  assert.equal(isMethodologyCompatibleWithSector("AGRICULTURE_LAND_USE", "ec739cc0-517a-4fa0-9ff3-ed4cc6d17667"), true);
  assert.equal(isMethodologyCompatibleWithSector("AGRICULTURE_LAND_USE", "VM0044"), false);
  assert.equal(isMethodologyCompatibleWithSector("AGRICULTURE_LAND_USE", "VT0014"), false);
  assert.equal(isMethodologyCompatibleWithSector("AGRICULTURE_LAND_USE", "VMD0053"), false);
  assert.equal(isMethodologyCompatibleWithSector("AGRICULTURE_LAND_USE", "BM_T_001"), false);
  assert.equal(isMethodologyCompatibleWithSector("AGRICULTURE_LAND_USE", "VM0047"), false);

  // Biochar tests
  assert.equal(isMethodologyCompatibleWithSector("BIOCHAR", "VM0044"), true);
  assert.equal(isMethodologyCompatibleWithSector("BIOCHAR", "BIOCHAR_C_SINK"), true);
  assert.equal(isMethodologyCompatibleWithSector("BIOCHAR", "PURO_BIOCHAR_2025"), true);
  assert.equal(isMethodologyCompatibleWithSector("BIOCHAR", "VM0042"), false);
  assert.equal(isMethodologyCompatibleWithSector("BIOCHAR", "AMS_I_F"), false);

  // Hybrid Energy tests
  assert.equal(isMethodologyCompatibleWithSector("HYBRID_ENERGY", "AMS_I_F"), true);
  assert.equal(isMethodologyCompatibleWithSector("HYBRID_ENERGY", "VM0042"), false);

  // EV Mobility tests
  assert.equal(isMethodologyCompatibleWithSector("EV_MOBILITY", "EV_DISPLACEMENT"), true);
  assert.equal(isMethodologyCompatibleWithSector("EV_MOBILITY", "VM0042"), false);

  // Cookstoves tests
  assert.equal(isMethodologyCompatibleWithSector("COOKSTOVES", "AMS_II_G"), true);
  assert.equal(isMethodologyCompatibleWithSector("COOKSTOVES", "VM0042"), false);
});

test("Onboarding Methodology Scoping: normalizeToCanonicalSectorCode handles aliases and UUIDs", () => {
  assert.equal(normalizeToCanonicalSectorCode("AGRICULTURE_LAND_USE"), "AGRICULTURE_LAND_USE");
  assert.equal(normalizeToCanonicalSectorCode("agriculture & land use"), "AGRICULTURE_LAND_USE");
  assert.equal(normalizeToCanonicalSectorCode("Agriculture and Land Use"), "AGRICULTURE_LAND_USE");
  assert.equal(normalizeToCanonicalSectorCode("9a7a4370-71e6-44f5-9870-975823b8ccb9"), "AGRICULTURE_LAND_USE");
  assert.equal(normalizeToCanonicalSectorCode("biochar"), "BIOCHAR");
  assert.equal(normalizeToCanonicalSectorCode("clean cookstoves"), "COOKSTOVES");
  assert.equal(normalizeToCanonicalSectorCode("unknown_sector"), null);
  assert.equal(normalizeToCanonicalSectorCode(null), null);
});

test("Onboarding Methodology Scoping: Signup page code audit guarantees no fallback to allMethodologies", () => {
  const signupPath = path.join(__dirname, "../src/app/signup/page.tsx");
  const signupCode = fs.readFileSync(signupPath, "utf-8");

  // Critical regression check: The buggy fallback must NOT exist anywhere in signup/page.tsx
  assert.equal(
    signupCode.includes("matched.length > 0 ? matched : allMethodologies"),
    false,
    "Buggy fallback 'matched.length > 0 ? matched : allMethodologies' MUST be eliminated"
  );
  assert.equal(
    signupCode.includes("setAllMethodologies"),
    false,
    "Unscoped allMethodologies state MUST be eliminated from signup page"
  );

  // Verify 'Select a sector first' disabled state exists
  assert.ok(
    signupCode.includes("Select a sector first"),
    "Signup page must display 'Select a sector first' when no sector is selected"
  );

  // Verify clear methodologyId on sector change exists
  assert.ok(
    signupCode.includes('setMethodologyId("")'),
    "Signup page must clear methodology selection on sector change"
  );

  // Verify scoping helper is invoked
  assert.ok(
    signupCode.includes("getCanonicalMethodologiesForSector"),
    "Signup page must use getCanonicalMethodologiesForSector"
  );
});
