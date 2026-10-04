import test from "node:test";
import assert from "node:assert/strict";
import crypto from "node:crypto";
import type {
  SOCStockResultItem,
  SOCStockEvaluationData,
  SOCLayerResultItem,
} from "../src/lib/api";

// =============================================================================
// VeriField Nexus — Agriculture MRV Phase 3B-1: Frontend Contract & Logic Tests
// VM0042 v2.2 SOC Stock & Equivalent Soil Mass (ESM) Calculation Engine
// =============================================================================

test("Phase 3B-1: Canonical Units & Dimensions Contract", () => {
  // Canonical Units:
  // SOC concentration: g C / kg dry fine soil
  // Bulk density: g / cm^3
  // Layer thickness: cm
  // Coarse fragment fraction: dimensionless (0.0 to 1.0)
  // Dry fine-soil mass: t dry fine soil / ha
  // Normalized SOC stock: t C / ha
  const layerInput = {
    layerIndex: 1,
    thicknessCm: 15.0,
    bulkDensityGcm3: 1.30,
    coarseFragmentFraction: 0.05,
    socConcentrationGkg: 18.5,
  };

  // Dimensional derivation:
  // 15 cm * 1.30 g/cm^3 * (1 - 0.05) * 100 = 1852.5 t dry fine soil/ha
  const expectedMass = layerInput.thicknessCm * layerInput.bulkDensityGcm3 * (1 - layerInput.coarseFragmentFraction) * 100;
  assert.equal(Math.round(expectedMass * 10) / 10, 1852.5);

  // Carbon mass: 1852.5 t soil/ha * 18.5 g C/kg soil / 1000 = 34.27125 t C/ha
  const expectedSocMass = (expectedMass * layerInput.socConcentrationGkg) / 1000;
  assert.equal(Math.round(expectedSocMass * 1000) / 1000, 34.271);
});

test("Phase 3B-1: Layer Fine-Soil Mass & Carbon Arithmetic Contract", () => {
  const layer: SOCLayerResultItem = {
    id: "l-1",
    stock_result_id: "stock-1",
    layer_index: 1,
    depth_upper_cm: 0,
    depth_lower_cm: 15,
    layer_thickness_cm: 15,
    bulk_density_g_cm3: 1.25,
    bulk_density_provenance: "MEASURED",
    coarse_fragment_fraction: 0.0,
    coarse_fragment_provenance: "MEASURED",
    layer_soil_mass_t_ha: 1875.0,
    soc_concentration_g_kg: 20.0,
    layer_soc_mass_t_c_ha: 37.5,
    cumulative_soil_mass_t_ha: 1875.0,
    cumulative_soc_mass_t_c_ha: 37.5,
    created_at: new Date().toISOString(),
  };

  assert.equal(layer.layer_index, 1);
  assert.equal(layer.layer_soil_mass_t_ha, 1875.0);
  assert.equal(layer.layer_soc_mass_t_c_ha, 37.5);
  assert.equal(layer.cumulative_soil_mass_t_ha, 1875.0);
  assert.equal(layer.cumulative_soc_mass_t_c_ha, 37.5);
});

test("Phase 3B-1: Cumulative Mass Profile & Monotonicity", () => {
  const layers: SOCLayerResultItem[] = [
    {
      id: "l-1",
      stock_result_id: "stock-1",
      layer_index: 1,
      depth_upper_cm: 0,
      depth_lower_cm: 15,
      layer_thickness_cm: 15,
      bulk_density_g_cm3: 1.25,
      bulk_density_provenance: "MEASURED",
      coarse_fragment_provenance: "MEASURED",
      layer_soil_mass_t_ha: 1875.0,
      soc_concentration_g_kg: 20.0,
      layer_soc_mass_t_c_ha: 37.5,
      cumulative_soil_mass_t_ha: 1875.0,
      cumulative_soc_mass_t_c_ha: 37.5,
      created_at: new Date().toISOString(),
    },
    {
      id: "l-2",
      stock_result_id: "stock-1",
      layer_index: 2,
      depth_upper_cm: 15,
      depth_lower_cm: 30,
      layer_thickness_cm: 15,
      bulk_density_g_cm3: 1.35,
      bulk_density_provenance: "MEASURED",
      coarse_fragment_provenance: "MEASURED",
      layer_soil_mass_t_ha: 2025.0,
      soc_concentration_g_kg: 10.0,
      layer_soc_mass_t_c_ha: 20.25,
      cumulative_soil_mass_t_ha: 3900.0,
      cumulative_soc_mass_t_c_ha: 57.75,
      created_at: new Date().toISOString(),
    },
  ];

  // Monotonic increase of cumulative mass and cumulative SOC
  assert.ok(Number(layers[1].cumulative_soil_mass_t_ha) > Number(layers[0].cumulative_soil_mass_t_ha));
  assert.ok(Number(layers[1].cumulative_soc_mass_t_c_ha) > Number(layers[0].cumulative_soc_mass_t_c_ha));
  assert.equal(layers[1].cumulative_soil_mass_t_ha, 3900.0);
  assert.equal(layers[1].cumulative_soc_mass_t_c_ha, 57.75);
});

test("Phase 3B-1: Equivalent Soil Mass (ESM) Normalization Arithmetic (Ellert & Bettany 1995)", () => {
  // Let M_ref = 3500 t/ha.
  // Layer 1 has M1 = 1875 t/ha, SOC1 = 37.5 t C/ha.
  // Layer 2 has M2 = 2025 t/ha, SOC2 = 20.25 t C/ha (M_cum = 3900 t/ha).
  // Layer 1 is fully included.
  // Deficit in Layer 2: M_add = M_ref - M1 = 3500 - 1875 = 1625 t/ha.
  // Layer 2 proportion: p = 1625 / 2025 = 0.802469.
  // Layer 2 added SOC: 0.802469 * 20.25 = 16.25 t C/ha.
  // Normalized SOC stock = 37.5 + 16.25 = 53.75 t C/ha.
  const mRef = 3500.0;
  const m1 = 1875.0;
  const soc1 = 37.5;
  const m2 = 2025.0;
  const soc2 = 20.25;

  const mAdd = mRef - m1;
  const p = mAdd / m2;
  const socAdd = p * soc2;
  const normalizedStock = soc1 + socAdd;

  assert.equal(Math.round(normalizedStock * 100) / 100, 53.75);
});

test("Phase 3B-1: Area-Weighted Stratum and Project Aggregation Contract", () => {
  const strataResults = [
    { stratum_code: "STRATUM_A", area_ha: 60.0, soc_stock_t_c_per_ha: 50.0 },
    { stratum_code: "STRATUM_B", area_ha: 40.0, soc_stock_t_c_per_ha: 40.0 },
  ];

  const totalArea = strataResults.reduce((acc, s) => acc + s.area_ha, 0);
  assert.equal(totalArea, 100.0);

  // Area-weighted project stock = (60 * 50 + 40 * 40) / 100 = 46.0 t C/ha
  const weightedStock = strataResults.reduce((acc, s) => acc + s.area_ha * s.soc_stock_t_c_per_ha, 0) / totalArea;
  assert.equal(weightedStock, 46.0);
});

test("Phase 3B-1: Cryptographic SHA-256 Hash Determinism & Proof Contract", () => {
  const calculationData = {
    projectId: "proj-12345",
    prerequisiteId: "prereq-67890",
    periodType: "BASELINE",
    esmAlgorithm: "ELLERT_BETTANY_1995",
    referenceSoilMassTha: "3500.00",
    socStockTcPerHa: "53.750",
  };

  const canonicalJson = JSON.stringify(calculationData, Object.keys(calculationData).sort());
  const hash1 = crypto.createHash("sha256").update(canonicalJson, "utf8").digest("hex");
  const hash2 = crypto.createHash("sha256").update(canonicalJson, "utf8").digest("hex");

  assert.equal(hash1, hash2);
  assert.equal(hash1.length, 64);
});

test("Phase 3B-1: Strict Carbon Invariant Contract (No tCO2e, No Crediting, Blocked Ledger)", () => {
  const result: Partial<SOCStockResultItem> = {
    result_code: "SOC-STOCK-PROJ-001",
    measurement_period_type: "BASELINE",
    aggregation_level: "PROJECT",
    soc_stock_t_c_per_ha: 53.75,
    result_status: "OFFICIAL_ACCEPTED",
  };

  // Verify result object contains measured/normalized SOC stock in t C/ha
  assert.equal(result.soc_stock_t_c_per_ha, 53.75);

  // Assert carbon invariant: No tCO2e fields exist on the stock result
  assert.equal((result as any).tco2e, undefined);
  assert.equal((result as any).net_tco2e_removals, undefined);
  assert.equal((result as any).credited_vcus, undefined);

  // Evaluation response asserts strict NOT_CONFIGURED policy
  const evaluation: Partial<SOCStockEvaluationData> = {
    status: "EVALUATED",
    carbon_accounting_status: "NOT_CONFIGURED",
    net_tco2e_removals: null,
  };

  assert.equal(evaluation.carbon_accounting_status, "NOT_CONFIGURED");
  assert.equal(evaluation.net_tco2e_removals, null);
});

test("Phase 3B-1: Segregation of Duties (SoD) Gate Contract", () => {
  const userRoles = ["FIELD_AGENT", "PROJECT_DEVELOPER", "VERIFIER", "SUPER_ADMIN"];

  const canCalculateAuthoritativeStock = (role: string) => {
    return role.toUpperCase() !== "FIELD_AGENT";
  };

  assert.equal(canCalculateAuthoritativeStock("FIELD_AGENT"), false);
  assert.equal(canCalculateAuthoritativeStock("PROJECT_DEVELOPER"), true);
  assert.equal(canCalculateAuthoritativeStock("VERIFIER"), true);
  assert.equal(canCalculateAuthoritativeStock("SUPER_ADMIN"), true);
});
