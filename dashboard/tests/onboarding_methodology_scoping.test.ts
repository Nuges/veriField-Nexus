import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {
  getCanonicalOperatingSectors,
  getCanonicalMethodologiesForSector,
  isMethodologyCompatibleWithSector,
  isMethodologyVersionSelectableForNewProjects,
  normalizeToCanonicalSectorCode,
  DISALLOWED_PRIMARY_METHODOLOGY_CODES,
  UNCONFIGURED_METHODOLOGY_CODES,
  CanonicalSectorCode,
} from "../src/lib/sectors";

test("Onboarding Methodology Scoping: Agriculture & Land Use exposes global catalog", () => {
  const agriMeths = getCanonicalMethodologiesForSector("AGRICULTURE_LAND_USE");
  assert.ok(agriMeths.length >= 4, `Expected at least 4 catalog methodologies for agriculture, got ${agriMeths.length}`);
  
  const codes = agriMeths.map((m) => m.code);
  assert.ok(codes.includes("VM0042"), "VM0042 must be present in Agriculture");
  assert.ok(codes.includes("VM0051"), "VM0051 must be present in Agriculture");
  assert.ok(codes.includes("VM0047"), "VM0047 must be present in Agriculture");
  assert.ok(codes.includes("VM0032"), "VM0032 must be present in Agriculture");

  // Supporting modules and tools must NEVER be exposed
  for (const tool of DISALLOWED_PRIMARY_METHODOLOGY_CODES) {
    assert.equal(codes.includes(tool), false, `Disallowed tool '${tool}' must not be present in Agriculture`);
  }
});

test("Onboarding Methodology Scoping: Production gating distinguishes full calculation from catalog discovery", () => {
  const allSectors = getCanonicalOperatingSectors();
  assert.equal(allSectors.length, 5);

  // Agriculture (4 primary methodologies, 1 calculation-enabled):
  const agriMeths = getCanonicalMethodologiesForSector("AGRICULTURE_LAND_USE");
  assert.equal(agriMeths.length, 4);
  const vm0042 = agriMeths.find((m) => m.code === "VM0042");
  assert.equal(vm0042?.verifieldSupport, "FULL");
  assert.equal(vm0042?.calculationEnabled, true);

  const vm0051 = agriMeths.find((m) => m.code === "VM0051");
  assert.equal(vm0051?.verifieldSupport, "MRV_ONLY");
  assert.equal(vm0051?.calculationEnabled, false);

  // Biochar (3 primary methodologies, 2 calculation-enabled):
  const biocharMeths = getCanonicalMethodologiesForSector("BIOCHAR");
  assert.equal(biocharMeths.length, 3);
  assert.equal(biocharMeths.find((m) => m.code === "VM0044")?.calculationEnabled, true);
  assert.equal(biocharMeths.find((m) => m.code === "PURO_BIOCHAR_2025")?.calculationEnabled, true);
  assert.equal(biocharMeths.find((m) => m.code === "BIOCHAR_C_SINK")?.calculationEnabled, false);

  // Clean Cookstoves (3 primary methodologies, 0 calculation-enabled — STRICTLY GATED):
  const cookstoveMeths = getCanonicalMethodologiesForSector("COOKSTOVES");
  assert.equal(cookstoveMeths.length, 3);
  assert.ok(cookstoveMeths.every((m) => m.calculationEnabled === false));
  assert.equal(cookstoveMeths.find((m) => m.code === "GS_MECD")?.verifieldSupport, "MRV_ONLY");

  // Hybrid Energy (3 primary methodologies, 0 calculation-enabled — STRICTLY GATED):
  const hybridMeths = getCanonicalMethodologiesForSector("HYBRID_ENERGY");
  assert.equal(hybridMeths.length, 3);
  assert.ok(hybridMeths.every((m) => m.calculationEnabled === false));
  assert.equal(hybridMeths.find((m) => m.code === "AMS_I_F")?.verifieldSupport, "MRV_ONLY");

  // EV Mobility (2 primary methodologies, 0 calculation-enabled — STRICTLY GATED):
  const evMeths = getCanonicalMethodologiesForSector("EV_MOBILITY");
  assert.equal(evMeths.length, 2);
  assert.ok(evMeths.every((m) => m.calculationEnabled === false));
  assert.equal(evMeths.find((m) => m.code === "VM0038")?.verifieldSupport, "MRV_ONLY");
});

test("Onboarding Methodology Scoping: isMethodologyCompatibleWithSector validation", () => {
  // Agriculture tests (GLOBAL CATALOG)
  assert.equal(isMethodologyCompatibleWithSector("AGRICULTURE_LAND_USE", "VM0042"), true);
  assert.equal(isMethodologyCompatibleWithSector("AGRICULTURE_LAND_USE", "VM0051"), true);
  assert.equal(isMethodologyCompatibleWithSector("AGRICULTURE_LAND_USE", "VM0047"), true);
  assert.equal(isMethodologyCompatibleWithSector("AGRICULTURE_LAND_USE", "VM0032"), true);
  assert.equal(isMethodologyCompatibleWithSector("AGRICULTURE_LAND_USE", "ec739cc0-517a-4fa0-9ff3-ed4cc6d17667"), true); // Stale UUID alias
  assert.equal(isMethodologyCompatibleWithSector("AGRICULTURE_LAND_USE", "VM0044"), false);
  assert.equal(isMethodologyCompatibleWithSector("AGRICULTURE_LAND_USE", "VT0014"), false);
  assert.equal(isMethodologyCompatibleWithSector("AGRICULTURE_LAND_USE", "VMD0053"), false);
  assert.equal(isMethodologyCompatibleWithSector("AGRICULTURE_LAND_USE", "BM_T_001"), false);

  // Biochar tests
  assert.equal(isMethodologyCompatibleWithSector("BIOCHAR", "VM0044"), true);
  assert.equal(isMethodologyCompatibleWithSector("BIOCHAR", "PURO_BIOCHAR_2025"), true);
  assert.equal(isMethodologyCompatibleWithSector("BIOCHAR", "BIOCHAR_C_SINK"), true);
  assert.equal(isMethodologyCompatibleWithSector("BIOCHAR", "EBC_BIOCHAR"), false);
  assert.equal(isMethodologyCompatibleWithSector("BIOCHAR", "GS_BIOCHAR"), false);
  assert.equal(isMethodologyCompatibleWithSector("BIOCHAR", "VM0042"), false);
  assert.equal(isMethodologyCompatibleWithSector("BIOCHAR", "AMS_I_F"), false);

  // Clean Cookstoves tests
  assert.equal(isMethodologyCompatibleWithSector("COOKSTOVES", "GS_MECD"), true);
  assert.equal(isMethodologyCompatibleWithSector("COOKSTOVES", "VM0050"), true);
  assert.equal(isMethodologyCompatibleWithSector("COOKSTOVES", "AMS_II_G"), true);
  assert.equal(isMethodologyCompatibleWithSector("COOKSTOVES", "VMR0050"), true); // Legacy alias resolves to VM0050
  assert.equal(isMethodologyCompatibleWithSector("COOKSTOVES", "VM0006"), true);  // Superseded alias resolves to VM0050
  assert.equal(isMethodologyCompatibleWithSector("COOKSTOVES", "GS_TPDDTEC"), false);
  assert.equal(isMethodologyCompatibleWithSector("COOKSTOVES", "VM0042"), false);
  assert.equal(isMethodologyCompatibleWithSector("COOKSTOVES", "VM0044"), false);

  // Hybrid Energy tests
  assert.equal(isMethodologyCompatibleWithSector("HYBRID_ENERGY", "AMS_I_F"), true);
  assert.equal(isMethodologyCompatibleWithSector("HYBRID_ENERGY", "AMS_I_L"), true);
  assert.equal(isMethodologyCompatibleWithSector("HYBRID_ENERGY", "ACM0002"), true);
  assert.equal(isMethodologyCompatibleWithSector("HYBRID_ENERGY", "CI_GRID_DISPLACEMENT"), false);
  assert.equal(isMethodologyCompatibleWithSector("HYBRID_ENERGY", "ENERGY_DISPLACEMENT"), false);
  assert.equal(isMethodologyCompatibleWithSector("HYBRID_ENERGY", "MINIGRID_DIESEL_DISPLACEMENT"), false);
  assert.equal(isMethodologyCompatibleWithSector("HYBRID_ENERGY", "SHS_RENEWABLE_DISPLACEMENT"), false);
  assert.equal(isMethodologyCompatibleWithSector("HYBRID_ENERGY", "VM0042"), false);

  // EV Mobility tests
  assert.equal(isMethodologyCompatibleWithSector("EV_MOBILITY", "VM0038"), true);
  assert.equal(isMethodologyCompatibleWithSector("EV_MOBILITY", "AMS_III_C"), true);
  assert.equal(isMethodologyCompatibleWithSector("EV_MOBILITY", "VMD0049"), false); // Supporting tool strictly disallowed as primary
  assert.equal(isMethodologyCompatibleWithSector("EV_MOBILITY", "EV_DISPLACEMENT"), false);
  assert.equal(isMethodologyCompatibleWithSector("EV_MOBILITY", "VM0042"), false);
  assert.equal(isMethodologyCompatibleWithSector("EV_MOBILITY", "VM0044"), false);
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

test("Onboarding Methodology Scoping: Authoritative UNFCCC methodology versions verified", () => {
  // Cookstoves: AMS-II.G must be version 14.0 (stableIdentifier: UNFCCC:AMS-II.G:14.0)
  const cookstoves = getCanonicalMethodologiesForSector("COOKSTOVES");
  const amsIIG = cookstoves.find((m) => m.code === "AMS_II_G");
  assert.ok(amsIIG, "AMS-II.G must be present in COOKSTOVES");
  assert.equal(amsIIG?.version, "14.0", "AMS-II.G current active version must be 14.0");
  assert.equal(amsIIG?.stableIdentifier, "UNFCCC:AMS-II.G:14.0");
  assert.equal(amsIIG?.selectableForNewProjects, true);
  assert.ok(amsIIG?.historicalVersions?.includes("13.0"), "AMS-II.G historical versions must include 13.0");

  // Hybrid Energy: AMS-I.F must be 5.0, AMS-I.L must be 5.0, ACM0002 must be 22.0
  const hybrid = getCanonicalMethodologiesForSector("HYBRID_ENERGY");
  const amsIF = hybrid.find((m) => m.code === "AMS_I_F");
  assert.ok(amsIF, "AMS-I.F must be present in HYBRID_ENERGY");
  assert.equal(amsIF?.version, "5.0", "AMS-I.F current active version must be 5.0");
  assert.equal(amsIF?.stableIdentifier, "UNFCCC:AMS-I.F:5.0");

  const amsIL = hybrid.find((m) => m.code === "AMS_I_L");
  assert.ok(amsIL, "AMS-I.L must be present in HYBRID_ENERGY");
  assert.equal(amsIL?.version, "5.0", "AMS-I.L current active version must be 5.0");
  assert.equal(amsIL?.stableIdentifier, "UNFCCC:AMS-I.L:5.0");
  assert.ok(amsIL?.historicalVersions?.includes("3.0"), "AMS-I.L historical versions must include 3.0");

  const acm0002 = hybrid.find((m) => m.code === "ACM0002");
  assert.ok(acm0002, "ACM0002 must be present in HYBRID_ENERGY");
  assert.equal(acm0002?.version, "22.0", "ACM0002 current active version must be 22.0");
  assert.equal(acm0002?.stableIdentifier, "UNFCCC:ACM0002:22.0");
  assert.ok(acm0002?.historicalVersions?.includes("21.0"), "ACM0002 historical versions must include 21.0");

  // EV Mobility: AMS-III.C must be 16.0
  const ev = getCanonicalMethodologiesForSector("EV_MOBILITY");
  const amsIIIC = ev.find((m) => m.code === "AMS_III_C");
  assert.ok(amsIIIC, "AMS-III.C must be present in EV_MOBILITY");
  assert.equal(amsIIIC?.version, "16.0", "AMS-III.C current active version must be 16.0");
  assert.equal(amsIIIC?.stableIdentifier, "UNFCCC:AMS-III.C:16.0");
});

test("Onboarding Methodology Scoping: isMethodologyVersionSelectableForNewProjects rejects historical versions", () => {
  // AMS-II.G: reject v13.0, allow v14.0
  const v13 = isMethodologyVersionSelectableForNewProjects("AMS_II_G", "13.0");
  assert.equal(v13.selectable, false);
  assert.ok(v13.error?.includes("historical/inactive"));
  assert.equal(v13.activeVersion, "14.0");

  const v14 = isMethodologyVersionSelectableForNewProjects("AMS_II_G", "14.0");
  assert.equal(v14.selectable, true);
  assert.equal(v14.activeVersion, "14.0");

  // AMS-I.L: reject v3.0, allow v5.0
  const v3 = isMethodologyVersionSelectableForNewProjects("AMS_I_L", "3.0");
  assert.equal(v3.selectable, false);
  assert.ok(v3.error?.includes("historical/inactive"));
  assert.equal(v3.activeVersion, "5.0");

  const v5 = isMethodologyVersionSelectableForNewProjects("AMS_I_L", "5.0");
  assert.equal(v5.selectable, true);
  assert.equal(v5.activeVersion, "5.0");

  // ACM0002: reject v21.0, allow v22.0
  const v21 = isMethodologyVersionSelectableForNewProjects("ACM0002", "21.0");
  assert.equal(v21.selectable, false);
  assert.ok(v21.error?.includes("historical/inactive"));
  assert.equal(v21.activeVersion, "22.0");

  const v22 = isMethodologyVersionSelectableForNewProjects("ACM0002", "22.0");
  assert.equal(v22.selectable, true);
  assert.equal(v22.activeVersion, "22.0");

  // Default when version is omitted: defaults to active version
  const def = isMethodologyVersionSelectableForNewProjects("ACM0002");
  assert.equal(def.selectable, true);
  assert.equal(def.activeVersion, "22.0");
});

