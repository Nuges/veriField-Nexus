import test from "node:test";
import assert from "node:assert/strict";
// @ts-expect-error Node strip-types requires explicit .ts extension at runtime
import { getSectorSpatialConfig } from "../src/components/spatial/SectorSpatialConfig.ts";

test("SectorSpatialConfig - Agriculture & Land Use", () => {
  const config = getSectorSpatialConfig("AGRICULTURE_LAND_USE");
  assert.equal(config.sectorCode, "AGRICULTURE_LAND_USE");
  assert.equal(config.assetSingular, "Land Unit");
  assert.equal(config.assetPlural, "Land Units");
  assert.equal(config.emptyTitle, "No land boundaries registered.");
  assert.equal(config.supportsEarthObservation, true);
  assert.deepEqual(config.allowedEOProviders, ["SENTINEL_2", "SENTINEL_1", "LANDSAT_8_9"]);

  const layerIds = config.availableLayers.map(l => l.id);
  assert.ok(layerIds.includes("boundaries"), "Must include project boundaries");
  assert.ok(layerIds.includes("land_units"), "Must include land units");
  assert.ok(layerIds.includes("soil_samples"), "Must include soil samples");
  assert.ok(layerIds.includes("tree_observations"), "Must include tree observations");
  assert.ok(layerIds.includes("sentinel_2"), "Must include Sentinel-2");
  assert.ok(layerIds.includes("sentinel_1"), "Must include Sentinel-1");
  assert.ok(layerIds.includes("landsat"), "Must include Landsat");

  // Invariant check: Agriculture must NOT include biochar facilities or cookstoves
  assert.ok(!layerIds.includes("facilities"), "Agriculture must not have biochar facilities");
  assert.ok(!layerIds.includes("devices"), "Agriculture must not have cookstove devices");
});

test("SectorSpatialConfig - AFOLU Alias resolves to Agriculture", () => {
  const config = getSectorSpatialConfig("afolu");
  assert.equal(config.sectorCode, "AGRICULTURE_LAND_USE");
  assert.equal(config.supportsEarthObservation, true);
});

test("SectorSpatialConfig - Biochar Carbon Removal", () => {
  const config = getSectorSpatialConfig("BIOCHAR");
  assert.equal(config.sectorCode, "BIOCHAR");
  assert.equal(config.assetSingular, "Facility");
  assert.equal(config.assetPlural, "Facilities");
  assert.equal(config.emptyTitle, "No biochar facilities registered.");

  const layerIds = config.availableLayers.map(l => l.id);
  assert.ok(layerIds.includes("facilities"), "Must include production facilities");
  assert.ok(layerIds.includes("feedstock_sources"), "Must include feedstock sources");
  assert.ok(layerIds.includes("storage_locations"), "Must include storage locations");
  assert.ok(layerIds.includes("end_use_sites"), "Must include end-use sites");
  assert.ok(layerIds.includes("linked_land_units"), "Must include linked agricultural land");

  // Invariant check: Biochar does NOT have native soil samples or cookstove devices
  assert.ok(!layerIds.includes("soil_samples"), "Biochar must not have native soil sample layer");
  assert.ok(!layerIds.includes("devices"), "Biochar must not have cookstove devices");
});

test("SectorSpatialConfig - Hybrid Energy", () => {
  const config = getSectorSpatialConfig("HYBRID_ENERGY");
  assert.equal(config.sectorCode, "HYBRID_ENERGY");
  assert.equal(config.emptyTitle, "No energy assets registered.");

  const layerIds = config.availableLayers.map(l => l.id);
  assert.ok(layerIds.includes("generation_assets"));
  assert.ok(layerIds.includes("inverters_meters"));
  assert.ok(layerIds.includes("generators"));
  assert.ok(layerIds.includes("facility_boundary"));

  // Invariant check: No agriculture or biochar layers
  assert.ok(!layerIds.includes("land_units"));
  assert.ok(!layerIds.includes("feedstock_sources"));
});

test("SectorSpatialConfig - EV Mobility", () => {
  const config = getSectorSpatialConfig("EV_MOBILITY");
  assert.equal(config.sectorCode, "EV_MOBILITY");
  assert.equal(config.emptyTitle, "No charging stations registered.");
  assert.equal(config.supportsEarthObservation, false);

  const layerIds = config.availableLayers.map(l => l.id);
  assert.ok(layerIds.includes("charging_stations"));
  assert.ok(layerIds.includes("chargers"));
  assert.ok(layerIds.includes("operating_sites"));
});

test("SectorSpatialConfig - Clean Cookstoves & Privacy Safe Clustering", () => {
  const config = getSectorSpatialConfig("COOKSTOVES");
  assert.equal(config.sectorCode, "COOKSTOVES");
  assert.equal(config.emptyTitle, "No cookstove devices registered.");
  assert.equal(config.privacySafeClustering, true, "Must enforce privacy-safe clustering for households");
  assert.equal(config.supportsEarthObservation, false);

  const layerIds = config.availableLayers.map(l => l.id);
  assert.ok(layerIds.includes("deployment_clusters"));
  assert.ok(layerIds.includes("devices"));
  assert.ok(layerIds.includes("field_activities"));
});
