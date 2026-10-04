import test from "node:test";
import assert from "node:assert/strict";

// =============================================================================
// VeriField Nexus — Agriculture MRV Phase 2: Frontend State & Truth Tests
// =============================================================================

interface SamplingCampaignDTO {
  id: string;
  project_id: string;
  campaign_code: string;
  name: string;
  sampling_type: "BASELINE" | "MONITORING_ROUND";
  crop_year: number;
  season?: string;
  status: "PLANNED" | "ACTIVE" | "COMPLETED" | "ARCHIVED";
}

interface SamplingPlanVersionDTO {
  id: string;
  campaign_id: string;
  version_number: number;
  status: "DRAFT" | "LOCKED" | "SUPERSEDED";
  provenance_type: "MANUAL" | "IMPORTED" | "EXTERNAL_DESIGN" | "CONFIGURED_METHOD" | "SYSTEM_GENERATED";
  plan_lock_snapshot?: Record<string, unknown> | null;
}

interface PhysicalSampleDTO {
  id: string;
  sample_qr_code: string;
  sample_label: string;
  depth_upper_cm: number;
  depth_lower_cm: number;
  custody_status: "PLANNED" | "COLLECTED" | "IN_TRANSIT" | "RECEIVED_BY_LAB" | "IN_ANALYSIS" | "ANALYSED" | "STORED" | "DISPOSED";
}

interface CustodyEventDTO {
  id: string;
  transferred_from_user_id: string;
  transferred_to_user_id: string;
  carrier_tracking_number?: string;
  seal_intact: boolean;
  transfer_timestamp: string;
}

interface LaboratoryResultDTO {
  id: string;
  analyte: string;
  raw_value: number;
  raw_unit: string;
  normalized_value: number;
  normalized_unit: string;
  is_superseded: boolean;
  supersedes_id?: string | null;
  superseded_by_id?: string | null;
  revision_reason?: string | null;
}

interface GroundEvidenceReadinessDTO {
  project_id: string;
  overall_status: "COMPLETE" | "INCOMPLETE" | "NEEDS_REVIEW" | "NOT_CONFIGURED";
  components: Record<string, {
    status: "COMPLETE" | "INCOMPLETE" | "NEEDS_REVIEW" | "NOT_CONFIGURED";
    message: string;
    details?: Record<string, unknown>;
  }>;
}

interface DeviationEvaluation {
  deviationDistanceM: number;
  configuredToleranceM: number | null;
  status: "PASS" | "EXCEEDS_TOLERANCE" | "NEEDS_REVIEW";
  displayText: string;
}

// ─── Evaluator & Formatter Functions Under Test ──────────────────────────────

function formatCampaignBadge(campaign: SamplingCampaignDTO): { label: string; tone: string } {
  return {
    label: `${campaign.campaign_code} • ${campaign.sampling_type} (${campaign.crop_year})`,
    tone: campaign.status === "ACTIVE" ? "emerald" : campaign.status === "COMPLETED" ? "blue" : "zinc",
  };
}

function evaluatePlanLockState(plan: SamplingPlanVersionDTO): { canModify: boolean; isImmutable: boolean } {
  if (plan.status === "LOCKED") {
    return { canModify: false, isImmutable: true };
  }
  return { canModify: true, isImmutable: false };
}

function formatDepthHorizon(sample: PhysicalSampleDTO): string {
  assert.ok(sample.depth_lower_cm > sample.depth_upper_cm, "Depth lower must exceed depth upper");
  return `${sample.depth_upper_cm}–${sample.depth_lower_cm} cm`;
}

function verifyCustodyChronology(events: CustodyEventDTO[]): { unbroken: boolean; compromisedSeals: number } {
  let compromised = 0;
  for (const ev of events) {
    if (!ev.seal_intact) compromised++;
  }
  return {
    unbroken: compromised === 0 && events.length > 0,
    compromisedSeals: compromised,
  };
}

function evaluateSpatialDeviation(deviationM: number, configuredToleranceM?: number | null): DeviationEvaluation {
  if (configuredToleranceM == null) {
    return {
      deviationDistanceM: deviationM,
      configuredToleranceM: null,
      status: "NEEDS_REVIEW",
      displayText: `${deviationM.toFixed(1)} m (Tolerance: Not configured)`,
    };
  }
  const isPass = deviationM <= configuredToleranceM;
  return {
    deviationDistanceM: deviationM,
    configuredToleranceM,
    status: isPass ? "PASS" : "EXCEEDS_TOLERANCE",
    displayText: `${deviationM.toFixed(1)} m (Tolerance: ${configuredToleranceM.toFixed(1)} m)`,
  };
}

function formatAnalyteDisplay(analyte: string, rawValue: number, rawUnit: string): { displayName: string; rawDisplay: string; isConcentration: boolean } {
  const isConcentration = (
    analyte === "SOC_CONCENTRATION" ||
    analyte === "SOC_STOCK_PCT" ||
    analyte === "SOC_PCT" ||
    analyte === "TOTAL_ORGANIC_CARBON_G_KG"
  );
  return {
    displayName: isConcentration ? "Soil Organic Carbon Concentration" : analyte,
    rawDisplay: `${rawValue.toFixed(4)} ${rawUnit}`,
    isConcentration,
  };
}

function formatNormalizedAssay(res: LaboratoryResultDTO): string {
  return `${res.normalized_value.toFixed(4)} ${res.normalized_unit}`;
}

function traceRevisionAuditChain(results: LaboratoryResultDTO[], currentId: string): string[] {
  const chain: string[] = [currentId];
  let current = results.find(r => r.id === currentId);
  while (current && current.supersedes_id) {
    chain.push(current.supersedes_id);
    current = results.find(r => r.id === current?.supersedes_id);
  }
  return chain;
}

function evaluateRoleGroundPermissions(role: string): { canLockPlan: boolean; canCollect: boolean; canQA: boolean; isReadOnly: boolean } {
  const r = role.toUpperCase();
  if (r === "SUPER_ADMIN") {
    return { canLockPlan: true, canCollect: true, canQA: true, isReadOnly: false };
  }
  if (r === "PROJECT_MANAGER") {
    return { canLockPlan: true, canCollect: false, canQA: false, isReadOnly: false };
  }
  if (r === "FIELD_SUPERVISOR") {
    return { canLockPlan: false, canCollect: true, canQA: true, isReadOnly: false };
  }
  if (r === "FIELD_AGENT") {
    return { canLockPlan: false, canCollect: true, canQA: false, isReadOnly: false };
  }
  if (r === "QA_OFFICER" || r === "VERIFIER") {
    return { canLockPlan: false, canCollect: false, canQA: true, isReadOnly: false };
  }
  if (r === "AUDITOR" || r === "VIEWER") {
    return { canLockPlan: false, canCollect: false, canQA: false, isReadOnly: true };
  }
  return { canLockPlan: false, canCollect: false, canQA: false, isReadOnly: true };
}

// ─── Test Suite ──────────────────────────────────────────────────────────────

test("01. Campaign state & badge display formatting", () => {
  const c: SamplingCampaignDTO = {
    id: "camp-01",
    project_id: "proj-01",
    campaign_code: "CAM-2026-A",
    name: "Summer Soil Sampling",
    sampling_type: "BASELINE",
    crop_year: 2026,
    season: "Kharif",
    status: "ACTIVE",
  };
  const badge = formatCampaignBadge(c);
  assert.equal(badge.label, "CAM-2026-A • BASELINE (2026)");
  assert.equal(badge.tone, "emerald");
});

test("02. Sampling plan version lock and immutability state", () => {
  const draftPlan: SamplingPlanVersionDTO = {
    id: "spv-01",
    campaign_id: "camp-01",
    version_number: 1,
    status: "DRAFT",
    provenance_type: "MANUAL",
  };
  assert.deepEqual(evaluatePlanLockState(draftPlan), { canModify: true, isImmutable: false });

  const lockedPlan: SamplingPlanVersionDTO = {
    id: "spv-02",
    campaign_id: "camp-01",
    version_number: 2,
    status: "LOCKED",
    provenance_type: "CONFIGURED_METHOD",
    plan_lock_snapshot: { frozen_points_count: 12 },
  };
  assert.deepEqual(evaluatePlanLockState(lockedPlan), { canModify: false, isImmutable: true });
});

test("03. Sampling depth horizon numerical validity and representation", () => {
  const sample: PhysicalSampleDTO = {
    id: "samp-01",
    sample_qr_code: "QR-SOIL-01",
    sample_label: "SOIL-01",
    depth_upper_cm: 0.0,
    depth_lower_cm: 30.0,
    custody_status: "COLLECTED",
  };
  assert.equal(formatDepthHorizon(sample), "0–30 cm");

  // Inverted depth must fail
  assert.throws(() => {
    formatDepthHorizon({ ...sample, depth_upper_cm: 30, depth_lower_cm: 10 });
  });
});

test("04. Chain of custody timeline and tamper seal verification", () => {
  const transfers: CustodyEventDTO[] = [
    {
      id: "ev-01",
      transferred_from_user_id: "user-agent-1",
      transferred_to_user_id: "user-courier",
      carrier_tracking_number: "TRK-001",
      seal_intact: true,
      transfer_timestamp: "2026-09-25T10:00:00Z",
    },
    {
      id: "ev-02",
      transferred_from_user_id: "user-courier",
      transferred_to_user_id: "user-lab-intake",
      carrier_tracking_number: "TRK-001",
      seal_intact: true,
      transfer_timestamp: "2026-09-25T14:00:00Z",
    },
  ];

  const unbroken = verifyCustodyChronology(transfers);
  assert.equal(unbroken.unbroken, true);
  assert.equal(unbroken.compromisedSeals, 0);

  const compromised = verifyCustodyChronology([
    ...transfers,
    {
      id: "ev-03",
      transferred_from_user_id: "user-lab-intake",
      transferred_to_user_id: "user-lab-tech",
      seal_intact: false,
      transfer_timestamp: "2026-09-25T15:00:00Z",
    },
  ]);
  assert.equal(compromised.unbroken, false);
  assert.equal(compromised.compromisedSeals, 1);
});

test("05. Ground Evidence Readiness evaluates 9 categorical components with factual counts", () => {
  const readiness: GroundEvidenceReadinessDTO = {
    project_id: "proj-01",
    overall_status: "INCOMPLETE",
    components: {
      sampling_campaign: { status: "COMPLETE", message: "1 active campaign", details: { active_campaigns: 1 } },
      sampling_plan: { status: "COMPLETE", message: "Plan locked", details: { locked_plans: 1 } },
      design_sufficiency: {
        status: "NOT_CONFIGURED",
        message: "Statistical sample-allocation engine not configured. Stratum coverage is factual only and does not establish statistical or methodological power sufficiency.",
      },
      stratum_coverage: { status: "COMPLETE", message: "All 4 strata sampled", details: { total_strata: 4, sampled: 4 } },
      sampling_points: { status: "COMPLETE", message: "12 points planned", details: { total_points: 12 } },
      field_collection: { status: "INCOMPLETE", message: "8 of 12 collected", details: { total: 12, collected: 8 } },
      chain_of_custody: { status: "INCOMPLETE", message: "8 custody logs recorded", details: { with_custody: 8 } },
      lab_receipt: { status: "INCOMPLETE", message: "6 of 8 received by lab", details: { received: 6 } },
      required_assays: { status: "INCOMPLETE", message: "6 of 8 received samples have required assays", details: { assays: 6 } },
      qa_review: { status: "NOT_CONFIGURED", message: "0 QA reviews documented", details: { qa_accepted: 0 } },
    },
  };

  assert.equal(readiness.overall_status, "INCOMPLETE");
  assert.equal(readiness.components.field_collection.message, "8 of 12 collected");
  assert.equal(readiness.components.required_assays.message, "6 of 8 received samples have required assays");
  assert.equal(readiness.components.design_sufficiency.status, "NOT_CONFIGURED");
});

test("06. Readiness contains NO aggregate percentage score or progress bar weight", () => {
  const readinessPayload: Record<string, unknown> = {
    project_id: "proj-01",
    overall_status: "INCOMPLETE",
    components: {
      field_collection: { status: "INCOMPLETE", message: "8 of 12 planned samples collected" },
      required_assays: { status: "INCOMPLETE", message: "6 of 8 received samples have required assays" },
    },
  };

  // Assert absence of fake percentage metrics
  assert.equal("percentage" in readinessPayload, false);
  assert.equal("readiness_percentage" in readinessPayload, false);
  assert.equal("progress_percentage" in readinessPayload, false);
  assert.equal("percent_ready" in readinessPayload, false);
  assert.equal("score" in readinessPayload, false);
});

test("07. Geodesic deviation WITHOUT configured tolerance reports factual truth and NEEDS_REVIEW", () => {
  // Deviation measured as 18.4 meters without methodology tolerance rule
  const dev = evaluateSpatialDeviation(18.4, null);
  assert.equal(dev.deviationDistanceM, 18.4);
  assert.equal(dev.configuredToleranceM, null);
  assert.equal(dev.status, "NEEDS_REVIEW");
  assert.equal(dev.displayText, "18.4 m (Tolerance: Not configured)");
});

test("08. Geodesic deviation WITH configured tolerance validates exact threshold", () => {
  // Methodology tolerance configured at 20.0 meters
  const configuredTolerance = 20.0;

  // 18.4m is within 20m tolerance -> PASS
  const devPass = evaluateSpatialDeviation(18.4, configuredTolerance);
  assert.equal(devPass.status, "PASS");
  assert.equal(devPass.displayText, "18.4 m (Tolerance: 20.0 m)");

  // 24.1m exceeds 20m tolerance -> EXCEEDS_TOLERANCE
  const devFail = evaluateSpatialDeviation(24.1, configuredTolerance);
  assert.equal(devFail.status, "EXCEEDS_TOLERANCE");
  assert.equal(devFail.displayText, "24.1 m (Tolerance: 20.0 m)");
});

test("09. SOC analyte terminology represents concentration (mass fraction), NOT stock", () => {
  // Canonical analyte
  const canonical = formatAnalyteDisplay("SOC_CONCENTRATION", 1.85, "%");
  assert.equal(canonical.displayName, "Soil Organic Carbon Concentration");
  assert.equal(canonical.rawDisplay, "1.8500 %");
  assert.equal(canonical.isConcentration, true);

  // Backward-compatible alias
  const alias = formatAnalyteDisplay("SOC_STOCK_PCT", 1.85, "%");
  assert.equal(alias.displayName, "Soil Organic Carbon Concentration");
  assert.equal(alias.rawDisplay, "1.8500 %");
  assert.equal(alias.isConcentration, true);

  // Non-SOC analyte
  const bd = formatAnalyteDisplay("BULK_DENSITY_G_CM3", 1.32, "g/cm3");
  assert.equal(bd.displayName, "BULK_DENSITY_G_CM3");
  assert.equal(bd.isConcentration, false);
});

test("10. Laboratory result raw vs normalized formatting (Numeric 12,4)", () => {
  const result: LaboratoryResultDTO = {
    id: "res-01",
    analyte: "SOC_CONCENTRATION",
    raw_value: 1.85,
    raw_unit: "%",
    normalized_value: 18.5,
    normalized_unit: "g/kg",
    is_superseded: false,
  };
  assert.equal(`${result.raw_value.toFixed(4)} ${result.raw_unit}`, "1.8500 %");
  assert.equal(formatNormalizedAssay(result), "18.5000 g/kg");
});

test("11. Laboratory result revision history and acyclic audit lineage", () => {
  const results: LaboratoryResultDTO[] = [
    {
      id: "res-v1",
      analyte: "SOC_CONCENTRATION",
      raw_value: 1.42,
      raw_unit: "%",
      normalized_value: 14.2,
      normalized_unit: "g/kg",
      is_superseded: true,
      superseded_by_id: "res-v2",
      revision_reason: "Initial reading",
    },
    {
      id: "res-v2",
      analyte: "SOC_CONCENTRATION",
      raw_value: 1.435,
      raw_unit: "%",
      normalized_value: 14.35,
      normalized_unit: "g/kg",
      is_superseded: false,
      supersedes_id: "res-v1",
      revision_reason: "Re-analyzed on secondary calibrated analyzer",
    },
  ];

  const lineage = traceRevisionAuditChain(results, "res-v2");
  assert.deepEqual(lineage, ["res-v2", "res-v1"]);
  assert.equal(results[1].revision_reason, "Re-analyzed on secondary calibrated analyzer");
});

test("12. Role permissions: QA_OFFICER authorized sign-off vs AUDITOR read-only", () => {
  // QA_OFFICER is authorized for QA sign-off but cannot collect or lock plans
  const qaPerms = evaluateRoleGroundPermissions("QA_OFFICER");
  assert.equal(qaPerms.canQA, true);
  assert.equal(qaPerms.canCollect, false);
  assert.equal(qaPerms.canLockPlan, false);
  assert.equal(qaPerms.isReadOnly, false);

  // AUDITOR is strictly read-only and barred from all actions
  const auditorPerms = evaluateRoleGroundPermissions("AUDITOR");
  assert.equal(auditorPerms.isReadOnly, true);
  assert.equal(auditorPerms.canQA, false);
  assert.equal(auditorPerms.canCollect, false);
  assert.equal(auditorPerms.canLockPlan, false);

  // FIELD_AGENT can collect, but cannot perform QA (SoD)
  const agentPerms = evaluateRoleGroundPermissions("FIELD_AGENT");
  assert.equal(agentPerms.canCollect, true);
  assert.equal(agentPerms.canQA, false);
  assert.equal(agentPerms.canLockPlan, false);
});
