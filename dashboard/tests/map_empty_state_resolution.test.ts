import test from 'node:test';
import assert from 'node:assert/strict';
// @ts-expect-error Node strip-types requires explicit .ts extension at runtime
import { canonicalSectorCode } from '../src/lib/moduleRegistry.ts';

// Helper matching SpatialModule's exact logic
function resolveEmptyStateCopy(sectorCode?: string) {
  const canonCode = canonicalSectorCode(sectorCode || "").toUpperCase();
  const isAgriculture = canonCode === "AGRICULTURE_LAND_USE";

  const assetLabel = isAgriculture
    ? "land units"
    : canonCode === "COOKSTOVES"
    ? "cookstoves"
    : canonCode === "HYBRID_ENERGY"
    ? "hybrid energy systems"
    : canonCode === "BIOCHAR"
    ? "biochar facilities"
    : canonCode === "EV_MOBILITY"
    ? "charging stations"
    : "assets";

  const emptyTitle = isAgriculture
    ? "No land boundaries registered."
    : `No ${assetLabel} registered.`;

  const emptySubtitle = isAgriculture
    ? "Add or capture a land unit to establish the project map."
    : canonCode === "COOKSTOVES"
    ? "Add or capture a device to establish the project map."
    : canonCode === "BIOCHAR"
    ? "Add or capture a facility to establish the project map."
    : canonCode === "EV_MOBILITY"
    ? "Add or capture a charging station to establish the project map."
    : canonCode === "HYBRID_ENERGY"
    ? "Add or capture an energy system to establish the project map."
    : "Add or capture an asset to establish the project map.";

  return { canonCode, isAgriculture, assetLabel, emptyTitle, emptySubtitle };
}

test('Section 16: Central Canonicalization', async (t) => {
  await t.test('resolves AGRICULTURE_LAND_USE -> agriculture_land_use', () => {
    assert.equal(canonicalSectorCode('AGRICULTURE_LAND_USE'), 'agriculture_land_use');
  });

  await t.test('resolves agriculture_land_use -> agriculture_land_use', () => {
    assert.equal(canonicalSectorCode('agriculture_land_use'), 'agriculture_land_use');
  });

  await t.test('resolves AGRICULTURE -> agriculture_land_use', () => {
    assert.equal(canonicalSectorCode('AGRICULTURE'), 'agriculture_land_use');
  });

  await t.test('resolves AFOLU -> agriculture_land_use', () => {
    assert.equal(canonicalSectorCode('AFOLU'), 'agriculture_land_use');
  });

  await t.test('resolves afolu -> agriculture_land_use', () => {
    assert.equal(canonicalSectorCode('afolu'), 'agriculture_land_use');
  });

  await t.test('resolves empty or missing to empty string', () => {
    assert.equal(canonicalSectorCode(''), '');
    assert.equal(canonicalSectorCode(undefined as unknown as string), '');
  });

  await t.test('resolves biochar -> biochar', () => {
    assert.equal(canonicalSectorCode('BIOCHAR'), 'biochar');
    assert.equal(canonicalSectorCode('biochar'), 'biochar');
  });

  await t.test('resolves EV -> ev_mobility', () => {
    assert.equal(canonicalSectorCode('EV'), 'ev_mobility');
    assert.equal(canonicalSectorCode('EV_MOBILITY'), 'ev_mobility');
  });
});

test('Section 15: Map Empty-State Copy Scenarios', async (t) => {
  await t.test('Scenario A: Agriculture + 0 land units -> exact Agriculture copy', () => {
    const res = resolveEmptyStateCopy('AGRICULTURE_LAND_USE');
    assert.equal(res.isAgriculture, true);
    assert.equal(res.emptyTitle, 'No land boundaries registered.');
    assert.equal(res.emptySubtitle, 'Add or capture a land unit to establish the project map.');
  });

  await t.test('Scenario A (AFOLU alias): resolves through central canonicalizer', () => {
    const res = resolveEmptyStateCopy('AFOLU');
    assert.equal(res.isAgriculture, true);
    assert.equal(res.emptyTitle, 'No land boundaries registered.');
    assert.equal(res.emptySubtitle, 'Add or capture a land unit to establish the project map.');
  });

  await t.test('Scenario C: Unknown / Missing sector -> neutral generic copy, NO Agriculture copy', () => {
    const resMissing = resolveEmptyStateCopy('');
    assert.equal(resMissing.isAgriculture, false);
    assert.equal(resMissing.emptyTitle, 'No assets registered.');
    assert.equal(resMissing.emptySubtitle, 'Add or capture an asset to establish the project map.');
    assert.doesNotMatch(resMissing.emptyTitle, /land boundaries/i);
    assert.doesNotMatch(resMissing.emptySubtitle, /land unit/i);

    const resUndefined = resolveEmptyStateCopy(undefined);
    assert.equal(resUndefined.isAgriculture, false);
    assert.equal(resUndefined.emptyTitle, 'No assets registered.');
    assert.equal(resUndefined.emptySubtitle, 'Add or capture an asset to establish the project map.');
    assert.doesNotMatch(resUndefined.emptyTitle, /land boundaries/i);
    assert.doesNotMatch(resUndefined.emptySubtitle, /land unit/i);

    const resUnknown = resolveEmptyStateCopy('UNKNOWN_SECTOR_999');
    assert.equal(resUnknown.isAgriculture, false);
    assert.equal(resUnknown.emptyTitle, 'No assets registered.');
    assert.equal(resUnknown.emptySubtitle, 'Add or capture an asset to establish the project map.');
    assert.doesNotMatch(resUnknown.emptyTitle, /land boundaries/i);
    assert.doesNotMatch(resUnknown.emptySubtitle, /land unit/i);
  });

  await t.test('Scenario D: Biochar + 0 assets -> Biochar terminology, NO Agriculture copy', () => {
    const res = resolveEmptyStateCopy('biochar');
    assert.equal(res.isAgriculture, false);
    assert.equal(res.emptyTitle, 'No biochar facilities registered.');
    assert.equal(res.emptySubtitle, 'Add or capture a facility to establish the project map.');
    assert.doesNotMatch(res.emptyTitle, /land boundaries/i);
    assert.doesNotMatch(res.emptySubtitle, /land unit/i);
  });

  await t.test('Scenario E: EV Mobility + 0 assets -> EV terminology, NO Agriculture copy', () => {
    const res = resolveEmptyStateCopy('ev_mobility');
    assert.equal(res.isAgriculture, false);
    assert.equal(res.emptyTitle, 'No charging stations registered.');
    assert.equal(res.emptySubtitle, 'Add or capture a charging station to establish the project map.');
    assert.doesNotMatch(res.emptyTitle, /land boundaries/i);
    assert.doesNotMatch(res.emptySubtitle, /land unit/i);
  });

  await t.test('Scenario E2: Cookstoves + 0 assets -> Cookstoves terminology, NO Agriculture copy', () => {
    const res = resolveEmptyStateCopy('cookstoves');
    assert.equal(res.isAgriculture, false);
    assert.equal(res.emptyTitle, 'No cookstoves registered.');
    assert.equal(res.emptySubtitle, 'Add or capture a device to establish the project map.');
    assert.doesNotMatch(res.emptyTitle, /land boundaries/i);
    assert.doesNotMatch(res.emptySubtitle, /land unit/i);
  });
});
