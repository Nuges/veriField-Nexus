import test from "node:test";
import assert from "node:assert/strict";
// @ts-expect-error Node strip-types requires explicit .ts extension at runtime
import { classifyDisplayProvenance } from "../src/components/spatial/provenance.ts";

test("Provenance: Provider thumbnail/visual classified as PROVIDER_VISUAL (never band composite)", () => {
  const s2ThumbnailObs = {
    scene_id: "S2B_37MBU_20240227_0_L2A",
    platform: "Sentinel-2B",
    sensor: "MSI",
    spatial_resolution_m: 10.0,
    raw_band_uris: {
      thumbnail: "https://sentinel-cogs.s3.us-west-2.amazonaws.com/thumbnail.jpg",
      visual: "https://sentinel-cogs.s3.us-west-2.amazonaws.com/visual.tif",
    },
  };

  const prov = classifyDisplayProvenance(s2ThumbnailObs, { width: 343, height: 343 });

  assert.equal(prov.sourceType, "PROVIDER_VISUAL");
  assert.equal(prov.sourceLabel, "Provider Visual");
  assert.equal(prov.displayDescription, "Provider-rendered optical preview");
  assert.equal(prov.sensorResolution, "10 m");
  assert.equal(prov.previewDimensions, "343 × 343 px");
  assert.equal(prov.bandRecipe, null, "MUST NOT claim R=B04, G=B03, B=B02 without genuine raw band compositing");
  assert.equal(prov.isSar, false);
  assert.equal(prov.isOptical, true);
});

test("Provenance: Sentinel-2 platform alone MUST NOT infer SOURCE_BAND_COMPOSITE", () => {
  const obs = {
    platform: "Sentinel-2A",
    sensor: "MSI",
    scene_id: "S2A_OPER_MSI_L2A_TL_20240101",
  };

  const prov = classifyDisplayProvenance(obs);
  assert.notEqual(prov.sourceType, "SOURCE_BAND_COMPOSITE", "Platform name must not trigger SOURCE_BAND_COMPOSITE");
  assert.equal(prov.sourceType, "PROVIDER_VISUAL");
  assert.equal(prov.bandRecipe, null);
});

test("Provenance: SAR quicklook classified as SAR_RENDER with dual-pol channels", () => {
  const s1Obs = {
    scene_id: "S1A_IW_GRDH_1SDV_20240228",
    platform: "Sentinel-1A",
    sensor: "C-SAR",
    observation_type: "SAR_C_BAND_BACKSCATTER",
    spatial_resolution_m: 10.0,
  };

  const prov = classifyDisplayProvenance(s1Obs);

  assert.equal(prov.sourceType, "SAR_RENDER");
  assert.equal(prov.sourceLabel, "Provider Quicklook");
  assert.equal(prov.displayDescription, "Dual-polarization SAR quicklook");
  assert.equal(prov.channels, "R=VV, G=VH, B=VV/VH ratio");
  assert.equal(prov.sensorResolution, "10 m (GRD)");
  assert.equal(prov.isSar, true);
  assert.equal(prov.isOptical, false);
  assert.ok(prov.disclaimer?.includes("Soil moisture inversion model is NOT_CONFIGURED"));
});

test("Provenance: Raw band composite ONLY when explicitly composited", () => {
  const compositeObs = {
    scene_id: "S2B_37MBU_20240227_0_L2A",
    platform: "Sentinel-2B",
    display_mode: "SOURCE_BAND_COMPOSITE",
    spatial_resolution_m: 10.0,
  };

  const prov = classifyDisplayProvenance(compositeObs);

  assert.equal(prov.sourceType, "SOURCE_BAND_COMPOSITE");
  assert.equal(prov.sourceLabel, "Source Band Composite");
  assert.equal(prov.bandRecipe, "R=B04, G=B03, B=B02");
  assert.equal(prov.displayDescription, "True-color RGB composite generated from calibrated source bands");
});

test("Provenance: Derived analytical outputs classified as DERIVED_PRODUCT", () => {
  const derivedObs = {
    display_source_type: "DERIVED_PRODUCT",
    observation_type: "DERIVED_INDEX",
    processing_level: "Level-3",
  };

  const prov = classifyDisplayProvenance(derivedObs);

  assert.equal(prov.sourceType, "DERIVED_PRODUCT");
  assert.equal(prov.sourceLabel, "Derived Product");
  assert.equal(prov.bandRecipe, null);
  assert.ok(prov.disclaimer?.includes("PRODUCTION_READY_WITH_LIMITATION"));
});

test("Provenance: Landsat historical baseline classified truthfully with 30m resolution", () => {
  const landsatObs = {
    scene_id: "LE07_L2SP_168061_20230331_02_T1",
    platform: "Landsat-7",
    product_code: "LANDSAT_C2_L2",
    spatial_resolution_m: 30.0,
    is_baseline: true,
  };

  const prov = classifyDisplayProvenance(landsatObs, { width: 500, height: 500 });

  assert.equal(prov.sourceType, "PROVIDER_VISUAL");
  assert.equal(prov.sourceLabel, "Provider Preview");
  assert.equal(prov.sensorResolution, "30 m");
  assert.equal(prov.previewDimensions, "500 × 500 px");
  assert.equal(prov.bandRecipe, null);
  assert.equal(prov.historicalContext, "Baseline evidence (prior to project start)");
});
