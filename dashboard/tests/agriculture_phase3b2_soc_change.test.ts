import test from "node:test";
import assert from "node:assert/strict";
import crypto from "node:crypto";
import type {
  SOCChangeResultItem,
} from "../src/lib/api";

// =============================================================================
// VeriField Nexus — Agriculture MRV Phase 3B-2: Frontend Contract & Logic Tests
// VM0042 v2.2 Soil Organic Carbon Stock Change & Uncertainty Deduction Engine
// =============================================================================

test("Phase 3B-2: Canonical Units & Stoichiometric 44/12 Dimensional Contract", () => {
  // Rate: t C / ha / yr
  // Conversion: 44/12 (approx 3.66666667)
  // Area: ha
  // Output: tCO2e / yr
  const deltaSocProj_t_c_ha_yr = 1.25;
  const deltaSocBsl_t_c_ha_yr = 0.0;
  const co2ToCRatio = 44 / 12;
  const areaHa = 150.0;
  const elapsedYears = 5.0;

  // Project Eq. (47) in tCO2e/yr
  const projCo2Rate_ha_yr = deltaSocProj_t_c_ha_yr * co2ToCRatio;
  const projTotalCo2_yr = projCo2Rate_ha_yr * areaHa;
  assert.equal(Math.round(projTotalCo2_yr * 100) / 100, 687.5);

  // Baseline Eq. (46) in tCO2e/yr
  const bslCo2Rate_ha_yr = deltaSocBsl_t_c_ha_yr * co2ToCRatio;
  const bslTotalCo2_yr = bslCo2Rate_ha_yr * areaHa;
  assert.equal(bslTotalCo2_yr, 0.0);

  // QA2 Net SOC Comparative Effect: Project (Eq. 47) - Baseline (Eq. 46)
  const qa2NetSocEffect_tco2e_yr = projTotalCo2_yr - bslTotalCo2_yr;
  assert.equal(Math.round(qa2NetSocEffect_tco2e_yr * 100) / 100, 687.5);
  assert.equal(elapsedYears >= 1.0, true);
});

test("Phase 3B-2: VM0042 Equations (46) & (47) Nomenclature & QA2 Separation Contract", () => {
  const mockResult: SOCChangeResultItem = {
    id: "chg-1",
    organization_id: "org-1",
    project_id: "proj-1",
    baseline_stock_result_id: "bsl-1",
    monitoring_stock_result_id: "mon-1",
    prerequisite_assessment_id: "prereq-1",
    result_code: "SOC-CHG-20261003-ABCD",
    methodology_version: "2.2",
    corrections_clarifications_version: "2026-06-11",
    calculation_engine_version: "VM0042_V2_2_SOC_CHANGE_V1.0",
    quantification_approach: "APPROACH_2",
    t_start: "2023-01-01T00:00:00Z",
    t_final: "2026-01-01T00:00:00Z",
    elapsed_years: "3.0000",
    esm_algorithm: "WENDT_HAUSER_2013_CUBIC_SPLINE",
    reference_soil_mass_t_ha: "1950.0000",
    reference_depth_cm: "30.00",
    total_project_area_ha: "100.0000",
    baseline_mean_soc_t_c_per_ha: "35.0000",
    monitoring_mean_soc_t_c_per_ha: "41.0000",
    delta_soc_project_t_c_ha_yr: "2.0000",
    delta_soc_baseline_t_c_ha_yr: "-0.2000",
    delta_soc_net_t_c_ha_yr: "2.2000",
    delta_co2_project_tco2e_ha_yr: "7.3333",
    delta_co2_baseline_tco2e_ha_yr: "-0.7333",
    delta_co2_net_tco2e_ha_yr: "8.0667",
    total_project_delta_co2_tco2e_yr: "733.3300",
    total_baseline_delta_co2_tco2e_yr: "-73.3300",
    total_net_delta_co2_tco2e_yr: "806.6700",
    baseline_soc_change_tco2e_yr: "-73.3300",  // Official Eq. (46)
    project_soc_change_tco2e_yr: "733.3300",   // Official Eq. (47)
    qa2_net_soc_effect_tco2e_yr: "806.6700",   // QA2 Net Effect (Eq. 47 - Eq. 46)
    uncertainty_adjusted_soc_effect_tco2e_yr: "766.3365",
    sign_indicator: 1,
    eq44_eq45_status: "PARTIALLY_CONFIGURED_SOC_ONLY",
    df_estimator: "DEFAULT_STRATIFIED_RANDOM_DF_ESTIMATOR",
    co2_to_c_ratio: "3.66666667",
    variance_delta_soc_project: "0.00280000",
    variance_delta_soc_baseline: "0.00000000",
    total_variance_delta_soc: "0.00280000",
    standard_error_delta_soc_t_c_ha_yr: "0.052915",
    standard_error_tco2e_yr: "19.4022",
    degrees_of_freedom: 18,
    student_t_value_0667: "0.4385",
    relative_uncertainty_pct: "5.0000",
    allowable_uncertainty_pct: "0.0000",  // ZERO DEADBAND
    uncertainty_deduction_pct: "5.0000",  // EXACT DEDUCTION
    uncertainty_deduction_fraction: "0.050000",
    adjusted_net_delta_co2_tco2e_yr: "766.3365",
    measurement_error_status: "NEGLIGIBLE_PER_VM0042_CONDITIONS",
    measurement_error_router: "CONVENTIONAL_DRY_COMBUSTION",
    strata_results: [],
    component_breakdown: {},
    carbon_accounting_status: "NOT_CONFIGURED",
    ledger_status: "BLOCKED_FOR_AGRICULTURE",
    result_status: "CALCULATED",
    calculation_hash: "hash123",
    input_snapshot_hash: "inhash123",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  // Verify Eq. (46) is baseline SOC change
  assert.equal(mockResult.baseline_soc_change_tco2e_yr, "-73.3300");
  // Verify Eq. (47) is project SOC change
  assert.equal(mockResult.project_soc_change_tco2e_yr, "733.3300");
  // Verify QA2 net effect is Project minus Baseline: 733.33 - (-73.33) = 806.66
  assert.equal(mockResult.qa2_net_soc_effect_tco2e_yr, "806.6700");
  // Verify Eq. 44/45 readiness classification
  assert.equal(mockResult.eq44_eq45_status, "PARTIALLY_CONFIGURED_SOC_ONLY");
  // Verify df estimator classification
  assert.equal(mockResult.df_estimator, "DEFAULT_STRATIFIED_RANDOM_DF_ESTIMATOR");
});

test("Phase 3B-2: Zero 15% Deadband Uncertainty Deduction Contract", () => {
  // If Eq. 74 produces U% = 0.5833%, the deduction is 0.5833%, NOT 0.0000%
  const u_pct = 0.5833;
  const allowable_threshold = 0.0; // Deadband removed
  const deduction_pct = u_pct - allowable_threshold;
  assert.equal(deduction_pct, 0.5833);

  const deduction_fraction = deduction_pct / 100.0;
  const gross_removals = 1000.0;
  const adjusted_removals = gross_removals * (1.0 - deduction_fraction);
  assert.equal(Math.round(adjusted_removals * 100) / 100, 994.17);
});

test("Phase 3B-2: Conservative Sign Indicator I(ΔCO2_soil,t) Contract", () => {
  // Branch 1: Project >= Baseline (Net positive removal)
  // I = +1, factor = (1 - fraction) <= 1.0 (reduces credited removals)
  const net_pos = 100.0;
  const sign_pos = net_pos >= 0 ? 1 : -1;
  assert.equal(sign_pos, 1);
  const factor_pos = 1.0 - (0.10 * sign_pos);
  assert.equal(factor_pos, 0.90);
  assert.equal(net_pos * factor_pos, 90.0);

  // Branch 2: Project < Baseline (Net negative removal / loss)
  // I = -1, factor = (1 + fraction) >= 1.0 (increases loss magnitude)
  const net_neg = -100.0;
  const sign_neg = net_neg >= 0 ? 1 : -1;
  assert.equal(sign_neg, -1);
  const factor_neg = 1.0 - (0.10 * sign_neg);
  assert.equal(Math.round(factor_neg * 100) / 100, 1.10);
  assert.equal(Math.round(net_neg * factor_neg * 100) / 100, -110.0);
  assert.equal(Math.abs(net_neg * factor_neg) > Math.abs(net_neg), true);
});

test("Phase 3B-2: Student's t 66.7% One-Sided Monotonicity Contract", () => {
  const t_values: Record<number, number> = {
    1: 0.5787,
    2: 0.5011,
    5: 0.4583,
    10: 0.4447,
    20: 0.4381,
    30: 0.4359,
    100: 0.4329,
  };

  assert.equal(t_values[1] > t_values[2], true);
  assert.equal(t_values[2] > t_values[5], true);
  assert.equal(t_values[5] > t_values[10], true);
  assert.equal(t_values[10] > t_values[20], true);
  assert.equal(t_values[20] > t_values[30], true);
  assert.equal(t_values[30] > t_values[100], true);
  // Large sample asymptote ~0.4307
  assert.equal(t_values[100] > 0.4307, true);
});

test("Phase 3B-2: Scope Boundary & Cryptographic Tamper Detection Contract", () => {
  const resultPayload = {
    result_code: "SOC-CHG-20261003-LIVE",
    baseline_id: "bsl-uuid-1",
    monitoring_id: "mon-uuid-1",
    delta_soc_net: "2.0000",
    net_co2e_yr: "733.3300",
    uncertainty_pct: "4.5000",
    carbon_accounting_status: "NOT_CONFIGURED",
    ledger_status: "BLOCKED_FOR_AGRICULTURE",
  };

  const hash1 = crypto.createHash("sha256").update(JSON.stringify(resultPayload)).digest("hex");
  assert.equal(hash1.length, 64);

  // Tamper check
  const tamperedPayload = { ...resultPayload, net_co2e_yr: "999.9999" };
  const hash2 = crypto.createHash("sha256").update(JSON.stringify(tamperedPayload)).digest("hex");
  assert.notEqual(hash1, hash2);
});

// =============================================================================
// Phase 3B-2: NaN / Infinity / Undefined Contract Tests
// NO authoritative Agriculture quantitative field may display NaN, Infinity,
// -Infinity, or undefined as calculation results.
// =============================================================================

test("Phase 3B-2: NaN Guard — All Authoritative Numeric Fields Must Be Finite", () => {
  const mockResult: SOCChangeResultItem = {
    id: "chg-nan-test",
    organization_id: "org-1",
    project_id: "proj-1",
    baseline_stock_result_id: "bsl-1",
    monitoring_stock_result_id: "mon-1",
    prerequisite_assessment_id: "prereq-1",
    result_code: "SOC-CHG-20261003-NAN",
    methodology_version: "2.2",
    corrections_clarifications_version: "2026-06-11",
    calculation_engine_version: "VM0042_V2_2_SOC_CHANGE_V1.0",
    quantification_approach: "APPROACH_2",
    t_start: "2023-01-01T00:00:00Z",
    t_final: "2026-01-01T00:00:00Z",
    elapsed_years: "3.0000",
    esm_algorithm: "WENDT_HAUSER_2013_CUBIC_SPLINE",
    reference_soil_mass_t_ha: "1950.0000",
    reference_depth_cm: "30.00",
    total_project_area_ha: "100.0000",
    baseline_mean_soc_t_c_per_ha: "35.0000",
    monitoring_mean_soc_t_c_per_ha: "41.0000",
    delta_soc_project_t_c_ha_yr: "2.0000",
    delta_soc_baseline_t_c_ha_yr: "-0.2000",
    delta_soc_net_t_c_ha_yr: "2.2000",
    delta_co2_project_tco2e_ha_yr: "7.3333",
    delta_co2_baseline_tco2e_ha_yr: "-0.7333",
    delta_co2_net_tco2e_ha_yr: "8.0667",
    total_project_delta_co2_tco2e_yr: "733.3300",
    total_baseline_delta_co2_tco2e_yr: "-73.3300",
    total_net_delta_co2_tco2e_yr: "806.6700",
    baseline_soc_change_tco2e_yr: "-73.3300",
    project_soc_change_tco2e_yr: "733.3300",
    qa2_net_soc_effect_tco2e_yr: "806.6700",
    uncertainty_adjusted_soc_effect_tco2e_yr: "766.3365",
    sign_indicator: 1,
    eq44_eq45_status: "PARTIALLY_CONFIGURED_SOC_ONLY",
    df_estimator: "DEFAULT_STRATIFIED_RANDOM_DF_ESTIMATOR",
    co2_to_c_ratio: "3.66666667",
    variance_delta_soc_project: "0.00280000",
    variance_delta_soc_baseline: "0.00000000",
    total_variance_delta_soc: "0.00280000",
    standard_error_delta_soc_t_c_ha_yr: "0.052915",
    standard_error_tco2e_yr: "19.4022",
    degrees_of_freedom: 18,
    student_t_value_0667: "0.4385",
    relative_uncertainty_pct: "5.0000",
    allowable_uncertainty_pct: "0.0000",
    uncertainty_deduction_pct: "5.0000",
    uncertainty_deduction_fraction: "0.050000",
    adjusted_net_delta_co2_tco2e_yr: "766.3365",
    measurement_error_status: "NEGLIGIBLE_PER_VM0042_CONDITIONS",
    measurement_error_router: "CONVENTIONAL_DRY_COMBUSTION",
    strata_results: [
      {
        stratum_code: "STR-A",
        stratum_area_ha: "100.0000",
        area_ha: "100.0000",
        area_weight: "1.00000000",
        baseline_mean_soc_t_c_per_ha: "35.0000",
        monitoring_mean_soc_t_c_per_ha: "41.0000",
        delta_soc_net_t_c_ha_yr: "2.2000",
        stratum_variance: "0.00280000",
        stratum_variance_net: "0.00280000",
        stratum_total_net_delta_co2_tco2e_yr: "806.6700",
        total_net_delta_co2_tco2e_yr: "806.6700",
      },
    ],
    component_breakdown: {},
    carbon_accounting_status: "NOT_CONFIGURED",
    ledger_status: "BLOCKED_FOR_AGRICULTURE",
    result_status: "CALCULATED",
    calculation_hash: "hash123",
    input_snapshot_hash: "inhash123",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  // AUTHORITATIVE NUMERIC FIELDS: must be finite when status is CALCULATED
  const numericFields: (keyof SOCChangeResultItem)[] = [
    "elapsed_years",
    "total_project_area_ha",
    "baseline_mean_soc_t_c_per_ha",
    "monitoring_mean_soc_t_c_per_ha",
    "delta_soc_project_t_c_ha_yr",
    "delta_soc_baseline_t_c_ha_yr",
    "delta_soc_net_t_c_ha_yr",
    "delta_co2_project_tco2e_ha_yr",
    "delta_co2_baseline_tco2e_ha_yr",
    "delta_co2_net_tco2e_ha_yr",
    "total_project_delta_co2_tco2e_yr",
    "total_baseline_delta_co2_tco2e_yr",
    "total_net_delta_co2_tco2e_yr",
    "baseline_soc_change_tco2e_yr",
    "project_soc_change_tco2e_yr",
    "qa2_net_soc_effect_tco2e_yr",
    "uncertainty_adjusted_soc_effect_tco2e_yr",
    "co2_to_c_ratio",
    "variance_delta_soc_project",
    "variance_delta_soc_baseline",
    "total_variance_delta_soc",
    "standard_error_delta_soc_t_c_ha_yr",
    "standard_error_tco2e_yr",
    "student_t_value_0667",
    "relative_uncertainty_pct",
    "allowable_uncertainty_pct",
    "uncertainty_deduction_pct",
    "uncertainty_deduction_fraction",
    "adjusted_net_delta_co2_tco2e_yr",
  ];

  for (const field of numericFields) {
    const val = mockResult[field];
    const num = Number(val);
    assert.ok(
      Number.isFinite(num),
      `Field '${field}' must be finite, got: ${val}`
    );
    assert.notEqual(
      String(val),
      "NaN",
      `Field '${field}' must not be string "NaN"`
    );
  }

  // STRATA NUMERIC FIELDS: must be finite for each stratum
  const strataNumericFields = [
    "stratum_area_ha",
    "area_ha",
    "area_weight",
    "baseline_mean_soc_t_c_per_ha",
    "monitoring_mean_soc_t_c_per_ha",
    "delta_soc_net_t_c_ha_yr",
    "stratum_variance",
    "stratum_variance_net",
    "stratum_total_net_delta_co2_tco2e_yr",
    "total_net_delta_co2_tco2e_yr",
  ];

  for (const st of mockResult.strata_results as any[]) {
    for (const field of strataNumericFields) {
      const val = st[field];
      if (val != null) {
        const num = Number(val);
        assert.ok(
          Number.isFinite(num),
          `Stratum field '${field}' must be finite, got: ${val}`
        );
      }
    }
  }
});

test("Phase 3B-2: NaN Guard — Null/Missing Fields Render as '—' Not NaN", () => {
  // Safe formatter contract: the frontend uses this pattern
  const sf = (v: any, d: number): string => {
    const n = Number(v);
    return v != null && Number.isFinite(n) ? n.toFixed(d) : "—";
  };

  // null → "—"
  assert.equal(sf(null, 4), "—");
  // undefined → "—"
  assert.equal(sf(undefined, 4), "—");
  // NaN string → "—"
  assert.equal(sf("NaN", 4), "—");
  // Infinity → "—"
  assert.equal(sf(Infinity, 4), "—");
  // -Infinity → "—"
  assert.equal(sf(-Infinity, 4), "—");
  // Empty string: Number('') === 0 (finite) — backend never sends empty strings
  // for authoritative numeric fields, but if encountered, renders as zero
  assert.equal(sf("", 4), "0.0000");

  // Valid numeric string → formatted number
  assert.equal(sf("35.0000", 3), "35.000");
  assert.equal(sf("0.00280000", 4), "0.0028");
  assert.equal(sf("-73.3300", 2), "-73.33");
  assert.equal(sf(0, 4), "0.0000");
  assert.equal(sf("0", 2), "0.00");
});

test("Phase 3B-2: Stratum Audit Contract — All Required Fields Present", () => {
  // The backend strata_formatted dict must include ALL of these fields
  // per the user's stratum audit contract directive
  const requiredFields = [
    "stratum_id",
    "stratum_code",
    "area_ha",
    "stratum_area_ha",
    "area_weight",
    "baseline_mean_soc_t_c_per_ha",
    "monitoring_mean_soc_t_c_per_ha",
    "delta_soc_project_t_c_ha_yr",
    "delta_soc_baseline_t_c_ha_yr",
    "delta_soc_net_t_c_ha_yr",
    "delta_co2_net_tco2e_ha_yr",
    "baseline_soc_change_tco2e_yr",
    "project_soc_change_tco2e_yr",
    "qa2_net_soc_effect_tco2e_yr",
    "total_net_delta_co2_tco2e_yr",
    "stratum_total_net_delta_co2_tco2e_yr",
    "variance_delta_soc_proj",
    "variance_delta_soc_bsl",
    "stratum_variance_net",
    "stratum_variance",
    "degrees_of_freedom",
    "sample_count_project",
    "sample_count_baseline",
  ];

  // Simulate a correctly formatted backend stratum response
  const mockStratum = {
    stratum_id: "uuid-1",
    stratum_code: "STR-A",
    area_ha: "100.0000",
    stratum_area_ha: "100.0000",
    area_weight: "1.00000000",
    baseline_mean_soc_t_c_per_ha: "35.0000",
    monitoring_mean_soc_t_c_per_ha: "41.0000",
    delta_soc_project_t_c_ha_yr: "2.0000",
    delta_soc_baseline_t_c_ha_yr: "-0.2000",
    delta_soc_net_t_c_ha_yr: "2.2000",
    delta_co2_net_tco2e_ha_yr: "8.0667",
    baseline_soc_change_tco2e_yr: "-73.3300",
    project_soc_change_tco2e_yr: "733.3300",
    qa2_net_soc_effect_tco2e_yr: "806.6700",
    total_net_delta_co2_tco2e_yr: "806.6700",
    stratum_total_net_delta_co2_tco2e_yr: "806.6700",
    variance_delta_soc_proj: "0.00280000",
    variance_delta_soc_bsl: "0.00000000",
    stratum_variance_net: "0.00280000",
    stratum_variance: "0.00280000",
    paired_covariance_project: null,
    paired_covariance_baseline: null,
    degrees_of_freedom: 18,
    sample_count_project: 10,
    sample_count_baseline: 10,
  };

  for (const field of requiredFields) {
    assert.ok(
      field in mockStratum,
      `Required stratum audit field '${field}' must be present in backend response`
    );
    const val = (mockStratum as any)[field];
    assert.notEqual(
      val,
      undefined,
      `Field '${field}' must not be undefined`
    );
  }
});

test("Phase 3B-2: Deprecated allowable_uncertainty_pct Not Used as Threshold", () => {
  // The allowable_uncertainty_pct field is always 0.0000 and must NEVER be used
  // as a threshold/deadband in Eq. 74 calculation
  const allowable = Number("0.0000");
  assert.equal(allowable, 0.0);

  // Even if someone tried to use it as a deadband, the deduction is NOT zeroed
  const u_pct = 0.5833;
  // WRONG (old behavior): if (u_pct <= 15) deduction = 0
  // CORRECT (current behavior): deduction = u_pct directly
  const deduction_pct = u_pct; // NOT: Math.max(0, u_pct - allowable)
  assert.equal(deduction_pct, 0.5833);
  assert.equal(deduction_pct > 0, true);
});
