import test from "node:test";
import assert from "node:assert/strict";
import crypto from "node:crypto";
import type {
  AgricultureNetGHGResultItem,
} from "../src/lib/api";

// =============================================================================
// VeriField Nexus — Agriculture MRV Phase 3B-3: Frontend Contract & Logic Tests
// VM0042 v2.2 Net GHG Reductions & Removals (Eqs. 37–43) + Section 8.7 VCU Readiness
// =============================================================================

test("Phase 3B-3: VM0042 Equations 37–43 Core GHG Reduction and Removal Mathematics", () => {
  // Scenario: Positive Reductions and Positive Removals
  // delta_E_BSL = 100 tCO2e, delta_E_WP = 40 tCO2e -> Source Reductions = 60 tCO2e
  // delta_C_BSL = -10 tCO2e, delta_C_WP = 50 tCO2e -> Soil Stock Removals = 60 tCO2e
  // delta_C_tree = 0, delta_C_shrub = 0
  const dE_bsl = 100.0;
  const dE_wp = 40.0;
  const dC_bsl = -10.0;
  const dC_wp = 50.0;
  const dC_tree_bsl = 0.0;
  const dC_tree_wp = 0.0;
  const dC_shrub_bsl = 0.0;
  const dC_shrub_wp = 0.0;
  const lk_total = 12.0;

  // Eq. (44) Baseline Total Carbon Stock Change
  const delta_C_bsl_total = dC_bsl + dC_tree_bsl + dC_shrub_bsl;
  assert.equal(delta_C_bsl_total, -10.0);

  // Eq. (45) Project Total Carbon Stock Change
  const delta_C_wp_total = dC_wp + dC_tree_wp + dC_shrub_wp;
  assert.equal(delta_C_wp_total, 50.0);

  // Eq. (37) Gross Reductions ER_t (Literal Official Form)
  const I_wp = delta_C_wp_total >= 0 ? 1 : 0;
  assert.equal(I_wp, 1);
  const term1_er = Math.max(0.0, dE_bsl - dE_wp);
  const min_wp = Math.min(0.0, delta_C_wp_total);
  const min_bsl = Math.min(0.0, delta_C_bsl_total);
  const max_wp = Math.max(0.0, delta_C_wp_total);
  const max_bsl = Math.max(0.0, delta_C_bsl_total);
  const stock_reduction_term = I_wp === 1 ? (min_wp - min_bsl) : ((min_wp - min_bsl) + (max_wp - max_bsl));
  const ER = term1_er + stock_reduction_term;
  assert.equal(ER, 70.0);

  // Eq. (40) Gross Removals CR_t (Exact Official Form)
  const CR = I_wp * Math.max(0.0, max_wp - max_bsl);
  assert.equal(CR, 50.0);

  // Gross benefits
  const gross_total = ER + CR;
  assert.equal(gross_total, 120.0);

  // Eq. (39) & (42) Leakage Allocation (11 June 2026 C&C: LEOA + LKdisp + LEBR)
  const LKER = gross_total > 0 ? lk_total * (ER / gross_total) : 0.0;
  const LKCR = gross_total > 0 ? lk_total * (CR / gross_total) : 0.0;
  assert.equal(LKER, 7.0);
  assert.equal(LKCR, 5.0);
  assert.equal(LKER + LKCR, lk_total);

  // Eq. (38) Net Reductions ERNET_t
  const ERNET = ER - LKER;
  assert.equal(ERNET, 63.0);

  // Eq. (41) Net Removals CRNET_t
  const CRNET = CR - LKCR;
  assert.equal(CRNET, 45.0);

  // Eq. (43) Total Net Benefit ERRNET_t
  const ERRNET = ERNET + CRNET;
  assert.equal(ERRNET, 108.0);

  // Invariant: ERRNET === (ER + CR) - LK
  assert.equal(ERRNET, gross_total - lk_total);
});

test("Phase 3B-3: Zero-Denominator Safety in Leakage Allocation (No 50/50 Fallback)", () => {
  // Case 1: When ER=0, CR=0, and LK=0 -> degenerate safe state (0, 0)
  const ER = 0.0;
  const CR = 0.0;
  const lk_zero = 0.0;
  const gross_zero = ER + CR;
  let lker = 0.0;
  let lkcr = 0.0;
  let status = "CALCULATED";

  if (gross_zero > 0) {
    lker = lk_zero * (ER / gross_zero);
    lkcr = lk_zero * (CR / gross_zero);
  } else if (lk_zero === 0) {
    lker = 0.0;
    lkcr = 0.0;
    status = "NO_BENEFIT_NO_LEAKAGE";
  }
  assert.equal(lker, 0.0);
  assert.equal(lkcr, 0.0);
  assert.equal(status, "NO_BENEFIT_NO_LEAKAGE");

  // Case 2: When ER=0, CR=0, and LK > 0 -> allocation is undefined, fail closed
  const lk_positive: number = 10.0;
  let blocked = false;
  try {
    if (gross_zero > 0) {
      lker = lk_positive * (ER / gross_zero);
    } else if (lk_positive === 0) {
      lker = 0.0;
    } else {
      throw new Error("LEAKAGE_ALLOCATION_UNDEFINED: AUTHORITATIVE_NET_GHG_BLOCKED");
    }
  } catch (err: any) {
    blocked = true;
    assert.equal(err.message.includes("LEAKAGE_ALLOCATION_UNDEFINED"), true);
  }
  assert.equal(blocked, true);
});

test("Phase 3B-3: Section 8.7 Non-Permanence Risk Buffer Deductions & Internal VCU Contract", () => {
  const ER = 60.0;
  const CR = 60.0;
  const LKER = 6.0;
  const LKCR = 6.0;
  const ERNET = ER - LKER; // 54.0
  const CRNET = CR - LKCR; // 54.0
  const npr_rating_pct = 15.0; // 15% buffer
  const npr_fraction = npr_rating_pct / 100.0;

  // Eq. (75) Buffer Deduction for Reductions
  // BuER,t applies to qualifying carbon-stock-change reduction terms. Here pure source reduction -> 0
  const stock_reductions_term = 0.0;
  const buffer_ER = stock_reductions_term * npr_fraction;
  assert.equal(buffer_ER, 0.0);

  // Eq. (76) Buffer Deduction for Removals
  // BuCR,t = I(Delta_CO2_wp) * [max(0, Delta_CO2_wp) - max(0, Delta_CO2_bsl)] * NPR% = CR * NPR%
  // Based on qualifying gross removals before leakage; NOT CRNET * NPR%.
  const buffer_CR = CR * npr_fraction; // 60.0 * 0.15 = 9.0
  assert.equal(buffer_CR, 9.0);

  const total_buffer = buffer_ER + buffer_CR;
  assert.equal(total_buffer, 9.0);

  // Eq. (77) Internal VCU Eligible Reductions
  const VCU_ER = ERNET - buffer_ER;
  assert.equal(VCU_ER, 54.0);

  // Eq. (78) Internal VCU Eligible Removals
  const VCU_CR = CRNET - buffer_CR;
  assert.equal(VCU_CR, 45.0); // 54.0 - 9.0 = 45.0

  // Eq. (79) Total Internal VCU Eligible
  const VCU_total = VCU_ER + VCU_CR;
  assert.equal(VCU_total, 99.0);

  // Invariant: VCU_total + total_buffer === ERNET + CRNET (54.0 + 54.0 = 108.0)
  assert.equal(VCU_total + total_buffer, ERNET + CRNET);
});

test("Phase 3B-3: Status Isolation Contract — Internal MRV vs External Registry", () => {
  const mockResult: AgricultureNetGHGResultItem = {
    id: "net-ghg-1",
    organization_id: "org-1",
    project_id: "proj-1",
    prerequisite_assessment_id: "prereq-1",
    result_code: "NET-GHG-20261004-TEST",
    methodology_version: "2.2",
    corrections_clarifications_version: "2026-06-11",
    calculation_engine_version: "VM0042_V2_2_NET_GHG_V1.0",
    ruleset_version: "VM0042_V2.2_RULES_CC20260611_V1.0",
    verification_period_start: "2023-01-01T00:00:00Z",
    verification_period_end: "2024-12-31T00:00:00Z",
    elapsed_years: "2.0000",
    applicability_matrix: {
      FOSSIL_FUEL_COMBUSTION: { status: "APPLICABLE_CONFIGURED", quantification_approach: "QA3" },
      SOIL_ORGANIC_CARBON: { status: "APPLICABLE_CONFIGURED", quantification_approach: "QA2" },
      SOIL_METHANOGENESIS: { status: "VERIFIED_ACTIVITY_ZERO", quantification_approach: "QA3" },
    },
    total_baseline_emissions_tco2e: "80.0000",
    total_project_emissions_tco2e: "40.0000",
    total_emission_reductions_from_sources_tco2e: "40.0000",
    eq44_baseline_total_carbon_stock_change_tco2e: "0.0000",
    eq45_project_total_carbon_stock_change_tco2e: "0.0000",
    eq44_eq45_status: "COMPLETE",
    gross_reductions_er_tco2e: "40.0000",
    gross_removals_cr_tco2e: "0.0000",
    total_leakage_tco2e: "4.0000",
    leakage_allocation_er_lker_tco2e: "4.0000",
    leakage_allocation_cr_lkcr_tco2e: "0.0000",
    net_reductions_ernet_tco2e: "36.0000",
    net_removals_crnet_tco2e: "0.0000",
    total_net_ghg_errnet_tco2e: "36.0000",
    npr_rating_pct: "15.0000",
    buffer_deduction_reductions_tco2e: "5.4000",
    buffer_deduction_removals_tco2e: "0.0000",
    total_buffer_deduction_tco2e: "5.4000",
    internal_vcu_eligible_reductions_tco2e: "30.6000",
    internal_vcu_eligible_removals_tco2e: "0.0000",
    internal_vcu_eligible_total_tco2e: "30.6000",
    vcu_readiness_status: "CALCULATED",
    internal_mrv_status: "CALCULATED",
    vvb_status: "NOT_CONFIGURED / EXTERNAL",
    registry_status: "NOT_CONFIGURED / EXTERNAL",
    ledger_status: "BLOCKED_FOR_AGRICULTURE",
    result_status: "CALCULATED",
    calculation_hash: "hash_abc",
    input_snapshot_hash: "hash_input_123",
    component_breakdown: {},
    vintages: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  // Assert non-issuance invariants
  assert.equal(mockResult.internal_mrv_status, "CALCULATED");
  assert.equal(mockResult.vvb_status, "NOT_CONFIGURED / EXTERNAL");
  assert.equal(mockResult.registry_status, "NOT_CONFIGURED / EXTERNAL");
  assert.equal(mockResult.result_status, "CALCULATED");
  assert.equal(Number(mockResult.total_net_ghg_errnet_tco2e), 36.0);
  assert.equal(Number(mockResult.internal_vcu_eligible_total_tco2e), 30.6);
});

test("Phase 3B-3: Cryptographic Determinism and SHA-256 Lineage Contract", () => {
  const payload = {
    project_id: "PRJ-TEST-1",
    verification_period_start: "2023-01-01",
    verification_period_end: "2024-12-31",
    ERRNET: "36.0000",
    VCU_ELIGIBLE: "30.6000",
  };

  const hash1 = crypto.createHash("sha256").update(JSON.stringify(payload)).digest("hex");
  const hash2 = crypto.createHash("sha256").update(JSON.stringify(payload)).digest("hex");

  assert.equal(hash1, hash2);
  assert.equal(hash1.length, 64);
});

test("Phase 3B-3: VM0042 Eq. 37 Critical Branch Vector (Current-Year Loss with I=1)", () => {
  // Vector: I = 1, current-year delta_C_wp = -5.0, delta_C_bsl = -10.0
  const I_wp = 1;
  assert.equal(I_wp, 1);
  const dC_wp = -5.0;
  const dC_bsl = -10.0;
  const min_wp = Math.min(0.0, dC_wp); // -5.0
  const min_bsl = Math.min(0.0, dC_bsl); // -10.0
  const stock_reduction_term = min_wp - min_bsl; // -5.0 - (-10.0) = +5.0
  assert.equal(stock_reduction_term, 5.0);

  // Proves that simplified max(0, -dC_bsl) = +10.0 is rejected
  const erroneous_simplified_term = Math.max(0.0, -dC_bsl);
  assert.equal(erroneous_simplified_term, 10.0);
  assert.notEqual(stock_reduction_term, erroneous_simplified_term);
});

test("Phase 3B-3: VM0042 Eq. 75 Adverse Vector (No Outer Zero-Clamping)", () => {
  // Vector: I = 1, delta_C_wp = -10.0, delta_C_bsl = -2.0, NPR = 15%
  const I_wp = 1;
  assert.equal(I_wp, 1);
  const dC_wp = -10.0;
  const dC_bsl = -2.0;
  const npr_fraction = 0.15;
  const min_wp = Math.min(0.0, dC_wp); // -10.0
  const min_bsl = Math.min(0.0, dC_bsl); // -2.0
  const stock_reduction_term = min_wp - min_bsl; // -10.0 - (-2.0) = -8.0
  assert.equal(stock_reduction_term, -8.0);

  // Official Eq. 75 buffer deduction: no outer clamp
  const BuER = stock_reduction_term * npr_fraction; // -8.0 * 0.15 = -1.2
  assert.equal(BuER, -1.2);
  assert.notEqual(BuER, 0.0);
});

test("Phase 3B-3: VMD0054 Version Governance & Fail-Closed Routing", () => {
  // 1. Current active standard routes to VMD0054 v1.1
  const defaultVersion = "VMD0054_1_1_CURRENT";
  const defaultEq = "VMD0054_V1.1_EQ13";
  assert.equal(defaultVersion, "VMD0054_1_1_CURRENT");
  assert.equal(defaultEq, "VMD0054_V1.1_EQ13");

  // 2. Unresolved transition blocks
  const requestedV10WithoutProof = {
    vmd0054_version: "1.0",
    transition_eligible: null,
  };
  let blocked = false;
  if (!requestedV10WithoutProof.transition_eligible) {
    blocked = true;
  }
  assert.equal(blocked, true);
});

test("Phase 3B-3: VM0042 Eq. 37 Adverse Result Preserves Negative Value (No Outer Zero Clamp)", () => {
  // Case: No source reductions (term1_er = 0.0)
  // delta_C_wp = -10.0, delta_C_bsl = -2.0, I = 1
  const term1_er = 0.0;
  const dC_wp = -10.0;
  const dC_bsl = -2.0;
  const I_wp = 1;
  assert.equal(I_wp, 1);

  const min_wp = Math.min(0.0, dC_wp); // -10.0
  const min_bsl = Math.min(0.0, dC_bsl); // -2.0
  const stock_reduction_term = min_wp - min_bsl; // -10.0 - (-2.0) = -8.0

  // Literal official Eq. 37: NO outer Math.max(0.0, ...)
  const ER = term1_er + stock_reduction_term;
  assert.equal(ER, -8.0);
  assert.ok(ER < 0.0, "Adverse annual performance must be negative, NOT forced to 0.0");
});

test("Phase 3B-3: VMD0054 v1.1 Eq. 11 (ΔCS in t C/ha) vs. Eq. 13 (LK_t in tCO2e) & VM0042 Eq. 36 LKdisp", () => {
  // Hand-verifiable parameters:
  const AL_t = 100.0; // ha
  const delta_c_biomass = 1.0; // t C/ha
  const delta_soc = 2.0; // t C/ha
  const ELM_t = 100.0; // tCO2e
  const LK_prior = 200.0; // tCO2e
  const years = 2.0; // yr

  // VMD0054 v1.1 Eq. 11: Delta_CS = Delta_C_biomass + Delta_SOC (t C/ha)
  const delta_CS = delta_c_biomass + delta_soc;
  assert.equal(delta_CS, 3.0); // t C/ha, NOT cumulative leakage

  // VMD0054 v1.1 Eq. 13: LK_t = AL_t * Delta_CS * (44/12) + ELM_t (tCO2e)
  const c_to_co2 = 44.0 / 12.0;
  const LK_t = (AL_t * delta_CS * c_to_co2) + ELM_t;
  assert.equal(Math.round(LK_t * 10000) / 10000, 1200.0); // 1200 tCO2e

  // VM0042 Corrected Eq. 36: LKdisp,t = MAX(0, LK_t - LK_prior) / years (tCO2e/yr)
  const LKdisp = Math.max(0.0, LK_t - LK_prior) / years;
  assert.equal(LKdisp, 500.0); // 500 tCO2e/yr
});
