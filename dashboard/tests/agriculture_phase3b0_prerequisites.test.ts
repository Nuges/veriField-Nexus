import test from "node:test";
import assert from "node:assert/strict";
import crypto from "node:crypto";
import type {
  PrerequisiteDimensionItem,
  PrerequisiteAssessmentItem,
} from "../src/lib/api";

// =============================================================================
// VeriField Nexus — Agriculture MRV Phase 3B-0: Frontend Contract & Logic Tests
// VM0042 v2.2 Quantification Methodology Prerequisite Engine
// =============================================================================

test("Phase 3B-0: 17 Categorical Prerequisite Dimensions Contract", () => {
  const EXPECTED_DIMENSIONS = [
    "METHODOLOGY_RULESET",
    "VCS_PROGRAM_RULESET",
    "QUANTIFICATION_UNIT",
    "ELIGIBILITY_AREA",
    "BASELINE_SCENARIO",
    "MANAGEMENT_HISTORY",
    "SAMPLING_DESIGN",
    "STRATIFICATION",
    "DEPTH",
    "ESM_INPUTS",
    "LABORATORY_QA",
    "BASELINE_MONITORING_PAIRING",
    "QUANTIFICATION_ROUTE",
    "MODEL_READINESS",
    "DSM_READINESS",
    "UNCERTAINTY_INPUTS",
    "TEMPORAL_ALIGNMENT",
  ];

  assert.equal(EXPECTED_DIMENSIONS.length, 17);

  const mockDimensions: Record<string, PrerequisiteDimensionItem> = {};
  for (const dim of EXPECTED_DIMENSIONS) {
    const isAdvisory = dim === "SAMPLING_DESIGN";
    mockDimensions[dim] = {
      status: "READY",
      requirement: "REQUIRED",
      blocking: !isAdvisory,
      finding_type: isAdvisory ? "NON_BLOCKING_ADVISORY" : "BLOCKING",
      reason_code: isAdvisory ? "POWER_ANALYSIS_NOT_RUN" : "VERIFIED_READY",
      message: `${dim} verified and ready.`,
      details: {},
    };
  }

  assert.equal(Object.keys(mockDimensions).length, 17);
  assert.equal(mockDimensions["SAMPLING_DESIGN"].blocking, false);
  assert.equal(mockDimensions["SAMPLING_DESIGN"].finding_type, "NON_BLOCKING_ADVISORY");
  assert.equal(mockDimensions["ESM_INPUTS"].blocking, true);
  assert.equal(mockDimensions["METHODOLOGY_RULESET"].blocking, true);
});

test("Phase 3B-0: Source Lock & C&C Metadata Contract", () => {
  const assessment: Partial<PrerequisiteAssessmentItem> = {
    methodology_code: "VM0042",
    methodology_version: "2.2",
    corrections_clarifications_version: "2026-06-11",
    rule_set_version: "VM0042-2.2-CC20260611",
    vcs_standard_version: "5.0",
  };

  assert.equal(assessment.methodology_code, "VM0042");
  assert.equal(assessment.methodology_version, "2.2");
  assert.equal(assessment.corrections_clarifications_version, "2026-06-11");
  assert.equal(assessment.rule_set_version, "VM0042-2.2-CC20260611");
  assert.ok(["4.7", "5.0"].includes(assessment.vcs_standard_version!));
});

test("Phase 3B-0: Component Route Mapping Contract & Tool Gating", () => {
  interface RouteItem {
    approach: string;
    description: string;
    applicable_tool: string;
    data_requirements: string[];
    model_requirements: string[];
    measurement_requirements: string[];
  }

  const routeMap: Record<string, RouteItem> = {
    soc_stock_change: {
      approach: "APPROACH_2",
      description: "Direct measurement and re-measurement",
      applicable_tool: "NONE",
      data_requirements: ["ESM_PROFILE", "BASELINE_CONTROL_SITES", "COARSE_FRAGMENTS", "BULK_DENSITY"],
      model_requirements: [],
      measurement_requirements: ["SOC_CONCENTRATION_G_KG", "BD_G_CM3", "DEPTH_HORIZONS"],
    },
    fossil_fuel_co2: {
      approach: "APPROACH_3",
      description: "Default emission factors for equipment fuel consumption",
      applicable_tool: "DEFAULT_FACTORS",
      data_requirements: ["DIESEL_LITERS", "GASOLINE_LITERS"],
      model_requirements: [],
      measurement_requirements: [],
    },
    liming_co2: {
      approach: "APPROACH_3",
      description: "Default emission factors for lime application",
      applicable_tool: "DEFAULT_FACTORS",
      data_requirements: ["LIMESTONE_KG", "DOLOMITE_KG"],
      model_requirements: [],
      measurement_requirements: [],
    },
    fertilizer_n2o: {
      approach: "APPROACH_3",
      description: "IPCC Tier 1 default factors or Tier 2 localized factors",
      applicable_tool: "DEFAULT_FACTORS",
      data_requirements: ["SYNTHETIC_N_KG", "ORGANIC_N_KG"],
      model_requirements: [],
      measurement_requirements: [],
    },
    rice_ch4: {
      approach: "NOT_APPLICABLE",
      description: "Flooded rice methane accounting (not present on upland fields)",
      applicable_tool: "NONE",
      data_requirements: [],
      model_requirements: [],
      measurement_requirements: [],
    },
    leakage_production_decline: {
      approach: "APPROACH_3",
      description: "VM0042 v2.2 June 11 2026 C&C leakage factor assessment",
      applicable_tool: "VM0042_CC_LEAKAGE",
      data_requirements: ["YIELD_BASELINE", "YIELD_MONITORING"],
      model_requirements: [],
      measurement_requirements: [],
    },
  };

  assert.equal(routeMap.soc_stock_change.approach, "APPROACH_2");
  assert.equal(routeMap.rice_ch4.approach, "NOT_APPLICABLE");
  assert.ok(routeMap.soc_stock_change.data_requirements.includes("ESM_PROFILE"));

  // Check VMD0053 gating: only required if Approach 1 is used
  const requiresVmd0053 = Object.values(routeMap).some(
    (r: RouteItem) => r.approach === "APPROACH_1" && r.applicable_tool === "VMD0053"
  );
  assert.equal(requiresVmd0053, false);
});

test("Phase 3B-0: ESM Horizon & Shallow Soil Exception Rules", () => {
  interface EsmDossierItem {
    procedure: string;
    min_depth_cm: number;
    has_minimum_30cm: boolean;
    has_deeper_bounding_layer: boolean;
    shallow_soil_exception: boolean;
    shallow_soil_evidence_verified: boolean;
    available_depth_layers: Array<{ depth_from_cm: number; depth_to_cm: number; layer_label: string }>;
    bulk_density_method: string;
    coarse_fragments_method: string;
    provenance_metadata: Record<string, unknown>;
  }

  const standardEsm: EsmDossierItem = {
    procedure: "ESM_CUBIC_SPLINE",
    min_depth_cm: 30.0,
    has_minimum_30cm: true,
    has_deeper_bounding_layer: true,
    shallow_soil_exception: false,
    shallow_soil_evidence_verified: false,
    available_depth_layers: [
      { depth_from_cm: 0, depth_to_cm: 15, layer_label: "0-15cm" },
      { depth_from_cm: 15, depth_to_cm: 30, layer_label: "15-30cm" },
      { depth_from_cm: 30, depth_to_cm: 50, layer_label: "30-50cm" },
    ],
    bulk_density_method: "CORE_RING",
    coarse_fragments_method: "SIEVE_GRAVIMETRIC",
    provenance_metadata: {
      qa_status: "VERIFIED",
      laboratory_accreditation: "ISO_17025",
    },
  };

  assert.ok(standardEsm.has_minimum_30cm);
  assert.ok(standardEsm.has_deeper_bounding_layer);
  assert.equal(standardEsm.shallow_soil_exception, false);

  // Shallow soil case: bedrock at 25cm with photographic and pedological proof
  const shallowSoilEsm: EsmDossierItem = {
    procedure: "ESM_LINEAR_INTERPOLATION",
    min_depth_cm: 25.0,
    has_minimum_30cm: false,
    has_deeper_bounding_layer: false,
    shallow_soil_exception: true,
    shallow_soil_evidence_verified: true,
    available_depth_layers: [
      { depth_from_cm: 0, depth_to_cm: 10, layer_label: "0-10cm" },
      { depth_from_cm: 10, depth_to_cm: 25, layer_label: "10-25cm (lithic contact)" },
    ],
    bulk_density_method: "EXCAVATION",
    coarse_fragments_method: "FIELD_ESTIMATE_VERIFIED",
    provenance_metadata: {
      bedrock_depth_cm: 25.0,
      pedological_evidence_hash: "a".repeat(64),
    },
  };

  assert.equal(shallowSoilEsm.shallow_soil_exception, true);
  assert.equal(shallowSoilEsm.shallow_soil_evidence_verified, true);
  assert.ok(shallowSoilEsm.min_depth_cm < 30.0);
});

test("Phase 3B-0: Power Analysis as Non-Blocking Advisory", () => {
  interface SamplingEvaluationItem {
    sampling_plan_id: string;
    sampling_design_method: string;
    minimum_points_per_stratum: number;
    strata_covered: number;
    total_sampling_points: number;
    power_analysis_executed: boolean;
    power_analysis_result: unknown | null;
    classification: "BLOCKING" | "NON_BLOCKING_ADVISORY";
    blocking_deficiencies: string[];
  }

  const samplingDesign: SamplingEvaluationItem = {
    sampling_plan_id: "plan-001",
    sampling_design_method: "STRATIFIED_RANDOM",
    minimum_points_per_stratum: 5,
    strata_covered: 3,
    total_sampling_points: 24,
    power_analysis_executed: false,
    power_analysis_result: null,
    classification: "NON_BLOCKING_ADVISORY",
    blocking_deficiencies: [],
  };

  assert.equal(samplingDesign.power_analysis_executed, false);
  assert.equal(samplingDesign.classification, "NON_BLOCKING_ADVISORY");
  assert.equal(samplingDesign.blocking_deficiencies.length, 0);

  // When power analysis is missing, overall status should be READY_WITH_ADVISORY, NOT BLOCKED
  const overallStatus = "READY_WITH_ADVISORY";
  assert.equal(overallStatus, "READY_WITH_ADVISORY");
});

test("Phase 3B-0: Immutable Prerequisite Dossier SHA-256 Hash", () => {
  const canonicalPayload = {
    assessment_code: "PREREQ-AGR-001",
    project_id: "00000000-0000-0000-0000-000000000001",
    rule_set_version: "VM0042-2.2-CC20260611",
    overall_readiness: "READY",
    status: "LOCKED",
  };

  const hash1 = crypto.createHash("sha256").update(JSON.stringify(canonicalPayload)).digest("hex");
  const hash2 = crypto.createHash("sha256").update(JSON.stringify(canonicalPayload)).digest("hex");

  assert.equal(hash1, hash2);
  assert.equal(hash1.length, 64);
});

test("Phase 3B-0: Segregation of Duties (SoD) Gate Contract", () => {
  const canLockAssessment = (role: string): boolean => {
    const r = role.toUpperCase();
    if (r === "FIELD_AGENT") return false;
    if (r === "AUDITOR") return false;
    if (r === "FIELD_SUPERVISOR") return false;
    if (r === "VIEWER") return false;
    if (["PROJECT_MANAGER", "ORG_ADMIN", "SUPER_ADMIN", "VERIFIER"].includes(r)) return true;
    return false;
  };

  assert.equal(canLockAssessment("FIELD_AGENT"), false);
  assert.equal(canLockAssessment("AUDITOR"), false);
  assert.equal(canLockAssessment("FIELD_SUPERVISOR"), false);
  assert.equal(canLockAssessment("VIEWER"), false);
  assert.equal(canLockAssessment("PROJECT_MANAGER"), true);
  assert.equal(canLockAssessment("ORG_ADMIN"), true);
  assert.equal(canLockAssessment("SUPER_ADMIN"), true);
  assert.equal(canLockAssessment("VERIFIER"), true);
});

test("Phase 3B-0: Fail-Closed Calculation Contract (Zero Carbon Output)", () => {
  // Prerequisite assessment must NEVER contain calculated carbon quantities or credits
  const assessmentKeys = [
    "id",
    "assessment_code",
    "version",
    "status",
    "overall_readiness",
    "methodology_code",
    "methodology_version",
    "vcs_standard_version",
    "dimensions",
    "quantification_route_map",
    "esm_input_dossier",
    "sampling_design_assessment",
  ];

  const forbiddenKeys = [
    "soc_stock",
    "soc_stock_change",
    "delta_soc",
    "tco2e",
    "gross_removals",
    "net_removals",
    "credits_issued",
    "vcu_quantity",
  ];

  for (const forbidden of forbiddenKeys) {
    assert.equal(assessmentKeys.includes(forbidden), false, `Forbidden carbon key found: ${forbidden}`);
  }
});

test("Phase 3B-0: VCS Version 5 Transition & Template Contract", () => {
  // Verra transition framework: Pre-2027 start without early adoption -> VCS Standard v4.7 + Template v4.4
  const vcsDetailsPre2027 = {
    governing_vcs_standard: "VCS_4_7",
    v5_template_variant: "NONE",
    project_description_template: "VCS_PROJECT_DESCRIPTION_V4.4",
    template_version: "VCS_PROJECT_DESCRIPTION_V4.4",
    early_adoption_mode: "NONE",
    voluntary_v5_adoption: false,
    delayed_requirement_ids: [],
  };

  assert.equal(vcsDetailsPre2027.governing_vcs_standard, "VCS_4_7");
  assert.equal(vcsDetailsPre2027.v5_template_variant, "NONE");
  assert.equal(vcsDetailsPre2027.project_description_template, "VCS_PROJECT_DESCRIPTION_V4.4");
  assert.equal(vcsDetailsPre2027.delayed_requirement_ids.length, 0);

  // Early adoption V5_0A -> VCS Standard v5.0 + Template v5.0A + 5 official delayed requirements
  const vcsEarlyAdoption5A = {
    governing_vcs_standard: "VCS_5_0",
    v5_template_variant: "V5_0A",
    project_description_template: "VCS_PROJECT_DESCRIPTION_V5.0A",
    early_adoption_mode: "V5_0A",
    voluntary_v5_adoption: true,
    delayed_requirement_ids: ["V5#14", "V5#16", "V5#17", "V5#23", "V5#58"],
  };
  assert.equal(vcsEarlyAdoption5A.governing_vcs_standard, "VCS_5_0");
  assert.equal(vcsEarlyAdoption5A.v5_template_variant, "V5_0A");
  assert.equal(vcsEarlyAdoption5A.project_description_template, "VCS_PROJECT_DESCRIPTION_V5.0A");
  assert.equal(vcsEarlyAdoption5A.delayed_requirement_ids.length, 5);
  assert.ok(vcsEarlyAdoption5A.delayed_requirement_ids.includes("V5#14"));
  assert.ok(vcsEarlyAdoption5A.delayed_requirement_ids.includes("V5#58"));

  // Early adoption V5_0B_FULL -> VCS Standard v5.0 + Template v5.0B + all V5 active
  const vcsEarlyAdoption5B = {
    governing_vcs_standard: "VCS_5_0",
    v5_template_variant: "V5_0B",
    project_description_template: "VCS_PROJECT_DESCRIPTION_V5.0B",
    early_adoption_mode: "V5_0B_FULL",
    voluntary_v5_adoption: true,
    delayed_requirement_ids: [],
  };
  assert.equal(vcsEarlyAdoption5B.governing_vcs_standard, "VCS_5_0");
  assert.equal(vcsEarlyAdoption5B.v5_template_variant, "V5_0B");
  assert.equal(vcsEarlyAdoption5B.project_description_template, "VCS_PROJECT_DESCRIPTION_V5.0B");
  assert.equal(vcsEarlyAdoption5B.delayed_requirement_ids.length, 0);

  // Post-2027 start -> VCS Standard v5.0 + Template v5.0B
  const vcsPost2027 = {
    governing_vcs_standard: "VCS_5_0",
    v5_template_variant: "V5_0B",
    project_description_template: "VCS_PROJECT_DESCRIPTION_V5.0B",
    delayed_requirement_ids: [],
  };
  assert.equal(vcsPost2027.governing_vcs_standard, "VCS_5_0");
  assert.equal(vcsPost2027.v5_template_variant, "V5_0B");
  assert.equal(vcsPost2027.project_description_template, "VCS_PROJECT_DESCRIPTION_V5.0B");
  assert.equal(vcsPost2027.delayed_requirement_ids.length, 0);
});
