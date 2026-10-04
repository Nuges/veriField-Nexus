import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {
  getCanonicalOperatingSectors,
  CANONICAL_SECTOR_CODES,
  isCanonicalSectorCode,
  getCanonicalSectorLabel,
} from "../src/lib/sectors";

// =============================================================================
// VeriField Nexus — Primary Operating Sector Frontend Contract Tests
// =============================================================================

test("Primary Operating Sector: Exposes exactly 5 canonical sector options", () => {
  const sectors = getCanonicalOperatingSectors();
  assert.equal(sectors.length, 5, `Expected exactly 5 sectors, got ${sectors.length}`);
});

test("Primary Operating Sector: Exact user-facing labels in canonical order", () => {
  const sectors = getCanonicalOperatingSectors();
  const expectedLabels = [
    "Clean Cookstoves",
    "Hybrid Energy & Mini-grids",
    "Biochar Carbon Removal",
    "EV Mobility",
    "Agriculture & Land Use",
  ];

  const actualLabels = sectors.map((s) => s.label);
  assert.deepEqual(actualLabels, expectedLabels, "Sector labels must match exact canonical specifications in order");
});

test("Primary Operating Sector: Exact canonical backend sector codes", () => {
  const sectors = getCanonicalOperatingSectors();
  const expectedCodes = [
    "COOKSTOVES",
    "HYBRID_ENERGY",
    "BIOCHAR",
    "EV_MOBILITY",
    "AGRICULTURE_LAND_USE",
  ];

  const actualCodes = sectors.map((s) => s.code);
  assert.deepEqual(actualCodes, expectedCodes, "Sector codes must match canonical values in order");
  assert.deepEqual(Array.from(CANONICAL_SECTOR_CODES), expectedCodes);
});

test("Primary Operating Sector: Deduplication defense guarantees 0 duplicates", () => {
  const sectors = getCanonicalOperatingSectors();
  const labelSet = new Set(sectors.map((s) => s.label));
  const codeSet = new Set(sectors.map((s) => s.code));

  assert.equal(labelSet.size, 5, "Every sector label must be distinct (0 duplicate labels)");
  assert.equal(codeSet.size, 5, "Every sector code must be distinct (0 duplicate codes)");
});

test("Primary Operating Sector: Invalid family and test fixture labels are strictly absent", () => {
  const sectors = getCanonicalOperatingSectors();
  const labels = sectors.map((s) => s.label.toLowerCase());
  const codes = sectors.map((s) => s.code.toLowerCase());

  const prohibitedPhrases = [
    "test family",
    "biochar removal family",
    "test",
    "family",
    "fam-",
    "biochar_fam_lock",
    "puro.earth",
    "vm0044",
  ];

  for (const phrase of prohibitedPhrases) {
    for (const label of labels) {
      if (phrase === "family" && label.includes("mini-grids")) continue;
      assert.ok(
        !label.includes(phrase),
        `Prohibited phrase '${phrase}' must not appear in sector label: '${label}'`
      );
    }
    for (const code of codes) {
      assert.ok(
        !code.includes(phrase),
        `Prohibited phrase '${phrase}' must not appear in sector code: '${code}'`
      );
    }
  }
});

test("Primary Operating Sector: Type guards and label lookup helpers operate correctly", () => {
  assert.equal(isCanonicalSectorCode("COOKSTOVES"), true);
  assert.equal(isCanonicalSectorCode("cookstoves"), true);
  assert.equal(isCanonicalSectorCode("HYBRID_ENERGY"), true);
  assert.equal(isCanonicalSectorCode("BIOCHAR"), true);
  assert.equal(isCanonicalSectorCode("EV_MOBILITY"), true);
  assert.equal(isCanonicalSectorCode("AGRICULTURE_LAND_USE"), true);

  assert.equal(isCanonicalSectorCode("Test Family"), false);
  assert.equal(isCanonicalSectorCode("Biochar Removal Family"), false);
  assert.equal(isCanonicalSectorCode("UNKNOWN_SECTOR"), false);
  assert.equal(isCanonicalSectorCode(null), false);
  assert.equal(isCanonicalSectorCode(undefined), false);

  assert.equal(getCanonicalSectorLabel("COOKSTOVES"), "Clean Cookstoves");
  assert.equal(getCanonicalSectorLabel("HYBRID_ENERGY"), "Hybrid Energy & Mini-grids");
  assert.equal(getCanonicalSectorLabel("BIOCHAR"), "Biochar Carbon Removal");
  assert.equal(getCanonicalSectorLabel("EV_MOBILITY"), "EV Mobility");
  assert.equal(getCanonicalSectorLabel("AGRICULTURE_LAND_USE"), "Agriculture & Land Use");
});

test("Primary Operating Sector: Signup Page static contract verification", () => {
  const signupPagePath = path.resolve(__dirname, "../src/app/signup/page.tsx");
  assert.ok(fs.existsSync(signupPagePath), "signup/page.tsx must exist");

  const signupContent = fs.readFileSync(signupPagePath, "utf-8");

  // Must consume centralized canonical sectors
  assert.ok(
    signupContent.includes("getCanonicalOperatingSectors"),
    "signup/page.tsx must import and use getCanonicalOperatingSectors"
  );
  assert.ok(
    signupContent.includes("canonicalSectors.map"),
    "signup/page.tsx must iterate over canonicalSectors"
  );

  // Must NOT iterate over families in sector dropdown
  assert.ok(
    !signupContent.includes("families.map((fam)"),
    "signup/page.tsx must not map over database families in sector dropdown"
  );

  // Must contain testid for robust E2E verification
  assert.ok(
    signupContent.includes('data-testid="primary-operating-sector-select"'),
    "signup/page.tsx must contain data-testid='primary-operating-sector-select'"
  );
});
