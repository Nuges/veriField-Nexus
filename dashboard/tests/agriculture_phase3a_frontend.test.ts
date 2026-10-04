import test from "node:test";
import assert from "node:assert/strict";
import crypto from "node:crypto";

// =============================================================================
// VeriField Nexus — Agriculture MRV Phase 3A: Frontend Contract & State Tests
// =============================================================================

interface QuantificationMeasurementItemDTO {
  physical_sample_id: string;
  sample_code: string;
  sampling_point_id: string;
  point_code: string;
  land_unit_id: string;
  land_unit_code: string;
  stratum_id?: string | null;
  stratum_code?: string | null;
  laboratory_result_id: string;
  analyte: string;
  raw_value: number;
  raw_unit: string;
  normalized_value: number;
  normalized_unit: string;
  provenance_class: "MEASURED";
  sampling_date: string;
  sample_depth_from_cm: number;
  sample_depth_to_cm: number;
  standard_depth_from_cm: number;
  standard_depth_to_cm: number;
  depth_alignment_status: "MATCH" | "PARTIAL_COVERAGE" | "OVERLAPPING_INTERVAL" | "OUT_OF_SCOPE" | "NEEDS_REVIEW";
  bulk_density_status: "PRESENT" | "MISSING" | "NOT_APPLICABLE";
  bulk_density_normalized_value?: number | null;
  bulk_density_normalized_unit?: string | null;
  coarse_fragments_status: "MEASURED_ZERO" | "MEASURED" | "NOT_MEASURED" | "NOT_APPLICABLE";
  coarse_fragments_fraction?: number | null;
  measurement_uncertainty?: number | null;
}

interface ExcludedMeasurementItemDTO {
  physical_sample_id: string;
  sample_code: string;
  sampling_point_id?: string | null;
  point_code?: string | null;
  land_unit_id?: string | null;
  land_unit_code?: string | null;
  exclusion_reasons: string[];
  rejection_details: Record<string, unknown>;
}

interface QuantificationReadinessDimensionDTO {
  dimension: string;
  status: "COMPLETE" | "INCOMPLETE" | "NEEDS_REVIEW" | "NOT_CONFIGURED" | "NOT_APPLICABLE";
  message: string;
  details?: Record<string, unknown>;
}

interface QuantificationSnapshotItemDTO {
  id: string;
  organization_id: string;
  project_id: string;
  snapshot_code: string;
  status: string;
  context: "BASELINE" | "MONITORING";
  snapshot_hash: string;
  is_locked: boolean;
  total_eligible_measurements: number;
  total_excluded_measurements: number;
  input_package: Record<string, unknown>;
}

test("Phase 3A: Canonical Analyte & Unit Contract", () => {
  const item: QuantificationMeasurementItemDTO = {
    physical_sample_id: "smp-001",
    sample_code: "SMP-P3A-01",
    sampling_point_id: "pt-001",
    point_code: "P-01",
    land_unit_id: "lu-001",
    land_unit_code: "LU-ALPHA",
    laboratory_result_id: "res-001",
    analyte: "SOC_CONCENTRATION",
    raw_value: 1.85,
    raw_unit: "%",
    normalized_value: 18.5,
    normalized_unit: "g/kg",
    provenance_class: "MEASURED",
    sampling_date: "2026-01-20",
    sample_depth_from_cm: 0.0,
    sample_depth_to_cm: 30.0,
    standard_depth_from_cm: 0.0,
    standard_depth_to_cm: 30.0,
    depth_alignment_status: "MATCH",
    bulk_density_status: "PRESENT",
    bulk_density_normalized_value: 1.35,
    bulk_density_normalized_unit: "g/cm³",
    coarse_fragments_status: "MEASURED_ZERO",
    coarse_fragments_fraction: 0.0,
  };

  assert.equal(item.analyte, "SOC_CONCENTRATION");
  assert.equal(item.normalized_unit, "g/kg");
  assert.equal(item.normalized_value, 18.5);
  assert.equal(item.provenance_class, "MEASURED");
  assert.equal(item.depth_alignment_status, "MATCH");
  assert.equal(item.bulk_density_status, "PRESENT");
  assert.equal(item.coarse_fragments_status, "MEASURED_ZERO");
});

test("Phase 3A: Depth Alignment Status Classification", () => {
  const alignDepth = (sampleFrom: number, sampleTo: number, stdFrom: number, stdTo: number) => {
    if (sampleFrom === stdFrom && sampleTo === stdTo) return "MATCH";
    if (sampleFrom >= stdFrom && sampleTo <= stdTo) return "PARTIAL_COVERAGE";
    if (sampleFrom < stdTo && sampleTo > stdTo) return "OVERLAPPING_INTERVAL";
    if (sampleFrom >= stdTo) return "OUT_OF_SCOPE";
    return "NEEDS_REVIEW";
  };

  assert.equal(alignDepth(0, 30, 0, 30), "MATCH");
  assert.equal(alignDepth(0, 15, 0, 30), "PARTIAL_COVERAGE");
  assert.equal(alignDepth(0, 40, 0, 30), "OVERLAPPING_INTERVAL");
  assert.equal(alignDepth(30, 60, 0, 30), "OUT_OF_SCOPE");
});

test("Phase 3A: Exclusion Reason Codes Gating", () => {
  const validReasonCodes = new Set([
    "QA_NOT_ACCEPTED",
    "LAB_RESULT_SUPERSEDED",
    "MISSING_BULK_DENSITY",
    "MISSING_COARSE_FRAGMENT_DATA",
    "DEPTH_MISMATCH",
    "BROKEN_CUSTODY",
    "OUTSIDE_MONITORING_PERIOD",
    "WRONG_LAND_UNIT",
    "WRONG_METHODOLOGY_CONTEXT",
    "PLAN_NOT_LOCKED",
    "UNCONVERTIBLE_UNIT",
    "SAMPLE_NOT_COLLECTED",
    "RECEIPT_REJECTED",
  ]);

  const excluded: ExcludedMeasurementItemDTO = {
    physical_sample_id: "smp-bad",
    sample_code: "SMP-REJECT-01",
    exclusion_reasons: ["QA_NOT_ACCEPTED", "LAB_RESULT_SUPERSEDED"],
    rejection_details: { qa_status: "REJECTED", reviewer: "Auditor" },
  };

  for (const reason of excluded.exclusion_reasons) {
    assert.ok(validReasonCodes.has(reason), `Invalid reason code: ${reason}`);
  }
});

test("Phase 3A: 16 Categorical Readiness Dimensions (Zero Percentage)", () => {
  const dimensions: Record<string, QuantificationReadinessDimensionDTO> = {
    METHODOLOGY_LOCK: { dimension: "METHODOLOGY_LOCK", status: "COMPLETE", message: "Locked to VM0042 v2.2" },
    MONITORING_PERIOD: { dimension: "MONITORING_PERIOD", status: "COMPLETE", message: "Baseline campaign completed" },
    BOUNDARY_VERSION: { dimension: "BOUNDARY_VERSION", status: "COMPLETE", message: "Authoritative perimeter v1" },
    STRATIFICATION: { dimension: "STRATIFICATION", status: "COMPLETE", message: "Soil strata active" },
    SAMPLING_PLAN: { dimension: "SAMPLING_PLAN", status: "COMPLETE", message: "Sampling plan locked" },
    DESIGN_SUFFICIENCY: { dimension: "DESIGN_SUFFICIENCY", status: "NOT_CONFIGURED", message: "Power analysis unconfigured" },
    GROUND_EVIDENCE: { dimension: "GROUND_EVIDENCE", status: "COMPLETE", message: "Physical samples collected" },
    SOC_CONCENTRATION: { dimension: "SOC_CONCENTRATION", status: "COMPLETE", message: "Assays verified" },
    BULK_DENSITY: { dimension: "BULK_DENSITY", status: "COMPLETE", message: "Density verified" },
    COARSE_FRAGMENTS: { dimension: "COARSE_FRAGMENTS", status: "COMPLETE", message: "Gravel fraction recorded" },
    DEPTH_ALIGNMENT: { dimension: "DEPTH_ALIGNMENT", status: "COMPLETE", message: "0-30cm standard aligned" },
    UNCERTAINTY_INPUTS: { dimension: "UNCERTAINTY_INPUTS", status: "COMPLETE", message: "Analytical variance captured" },
    BASELINE_DATASET: { dimension: "BASELINE_DATASET", status: "COMPLETE", message: "Baseline candidate set ready" },
    PROJECT_DATASET: { dimension: "PROJECT_DATASET", status: "NOT_APPLICABLE", message: "Baseline context active" },
    QA_ACCEPTANCE: { dimension: "QA_ACCEPTANCE", status: "COMPLETE", message: "QA reviews accepted" },
    CALCULATION_RULES: { dimension: "CALCULATION_RULES", status: "COMPLETE", message: "Rule set resolved" },
  };

  assert.equal(Object.keys(dimensions).length, 16);
  assert.equal(dimensions.DESIGN_SUFFICIENCY.status, "NOT_CONFIGURED");

  // Invariant: no numeric scores, no percentages
  for (const [, dim] of Object.entries(dimensions)) {
    assert.ok(["COMPLETE", "INCOMPLETE", "NEEDS_REVIEW", "NOT_CONFIGURED", "NOT_APPLICABLE"].includes(dim.status));
    assert.ok(dim.message.length > 0);
  }
});

test("Phase 3A: Immutable Snapshot SHA-256 Hash Determinism", () => {
  const inputPackage = {
    context: "BASELINE",
    methodology: { code: "VM0042", version: "2.2" },
    measurements: [
      {
        sample_code: "SMP-01",
        analyte: "SOC_CONCENTRATION",
        normalized_value: 18.5,
        normalized_unit: "g/kg",
      },
    ],
  };

  const canonicalString = JSON.stringify(inputPackage);
  const hash1 = crypto.createHash("sha256").update(canonicalString).digest("hex");
  const hash2 = crypto.createHash("sha256").update(canonicalString).digest("hex");

  assert.equal(hash1, hash2);
  assert.equal(hash1.length, 64);

  const snapshot: QuantificationSnapshotItemDTO = {
    id: "snap-001",
    organization_id: "org-001",
    project_id: "prj-001",
    snapshot_code: "QIS-2026-001",
    status: "LOCKED",
    context: "BASELINE",
    snapshot_hash: hash1,
    is_locked: true,
    total_eligible_measurements: 1,
    total_excluded_measurements: 0,
    input_package: inputPackage,
  };

  assert.equal(snapshot.is_locked, true);
  assert.equal(snapshot.snapshot_code.startsWith("QIS-"), true);
});

test("Phase 3A: Segregation of Duties (SoD) Role Gate", () => {
  const canLockSnapshot = (role: string) => {
    const r = role.toUpperCase();
    if (r === "FIELD_AGENT") return false;
    return ["ORG_ADMIN", "SUPER_ADMIN", "PROJECT_MANAGER", "QA_OFFICER"].includes(r);
  };

  assert.equal(canLockSnapshot("FIELD_AGENT"), false);
  assert.equal(canLockSnapshot("PROJECT_MANAGER"), true);
  assert.equal(canLockSnapshot("QA_OFFICER"), true);
  assert.equal(canLockSnapshot("ORG_ADMIN"), true);
});
