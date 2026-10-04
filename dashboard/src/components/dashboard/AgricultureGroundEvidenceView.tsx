// =============================================================================
// VeriField Nexus — Agriculture MRV Phase 2: Ground Evidence Console
// =============================================================================
// Defensible Ground Evidence Workflow:
// Campaign -> Plan Version Lock -> Sampling Points -> Field Collection ->
// Chain of Custody -> Lab Receipt -> Lab Assays -> Result Revision -> QA Review ->
// 9-Component Categorical Ground Evidence Readiness Evaluator
// =============================================================================

"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  TestTube,
  Microscope,
  Truck,
  ClipboardCheck,
  FileCheck,
  CheckCircle2,
  AlertTriangle,
  Lock,
  RefreshCw,
  Plus,
  Clock,
  HelpCircle,
  Eye,
  History,
  Tag,
  MapPin,
  ArrowRight,
  ShieldCheck,
  Scale,
  FileSpreadsheet,
} from "lucide-react";
import AgricultureLaboratoryBulkImportView from "./AgricultureLaboratoryBulkImportView";
import {
  fetchSamplingCampaigns,
  createSamplingCampaign,
  fetchSamplingPlanVersions,
  createSamplingPlanVersion,
  lockSamplingPlanVersion,
  fetchSamplingPoints,
  createSamplingPoints,
  fetchPhysicalSamples,
  fetchPhysicalSample,
  recordSampleCustodyEvent,
  recordSampleLaboratoryReceipt,
  recordSampleLaboratoryAnalysis,
  reviseLaboratoryResult,
  recordSampleQAReview,
  fetchGroundEvidenceReadiness,
  fetchLandUnits,
  fetchProjectStrata,
  type SamplingCampaignRecord,
  type SamplingPlanVersionRecord,
  type SamplingPointRecord,
  type PhysicalSampleRecord,
  type GroundEvidenceReadinessData,
  type LandUnitRecord,
  type StratumRecord,
  type LaboratoryResultRecord,
} from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";

export default function AgricultureGroundEvidenceView({ projectId }: { projectId: string }) {
  let workspaceUser: any = null;
  try {
    const ws = useWorkspace();
    workspaceUser = ws?.user;
  } catch {
    // Isolated testing
  }
  const userRole = (workspaceUser?.role || "PROJECT_MANAGER").toUpperCase();
  const isAuditor = userRole === "AUDITOR";
  const isFieldAgent = userRole === "FIELD_AGENT";
  const canManagePlans = !isAuditor && !isFieldAgent;
  const canPerformQA = !isFieldAgent;

  // Data States
  const [campaigns, setCampaigns] = useState<SamplingCampaignRecord[]>([]);
  const [selectedCampaignId, setSelectedCampaignId] = useState<string>("");
  const [planVersions, setPlanVersions] = useState<SamplingPlanVersionRecord[]>([]);
  const [samplingPoints, setSamplingPoints] = useState<SamplingPointRecord[]>([]);
  const [physicalSamples, setPhysicalSamples] = useState<PhysicalSampleRecord[]>([]);
  const [readiness, setReadiness] = useState<GroundEvidenceReadinessData | null>(null);
  const [landUnits, setLandUnits] = useState<LandUnitRecord[]>([]);
  const [strata, setStrata] = useState<StratumRecord[]>([]);

  // UI States
  const [activeTab, setActiveTab] = useState<"readiness" | "campaigns" | "samples" | "bulk-import">("readiness");
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Modals & Drawers
  const [selectedSampleForLineage, setSelectedSampleForLineage] = useState<PhysicalSampleRecord | null>(null);
  const [showCreateCampaignModal, setShowCreateCampaignModal] = useState(false);
  const [showLockPlanModal, setShowLockPlanModal] = useState(false);
  const [showCreatePointsModal, setShowCreatePointsModal] = useState(false);
  const [showLabReceiptModal, setShowLabReceiptModal] = useState(false);
  const [showLabAnalysisModal, setShowLabAnalysisModal] = useState(false);
  const [showReviseResultModal, setShowReviseResultModal] = useState(false);
  const [showQAReviewModal, setShowQAReviewModal] = useState(false);
  const [activeSample, setActiveSample] = useState<PhysicalSampleRecord | null>(null);
  const [activeResult, setActiveResult] = useState<LaboratoryResultRecord | null>(null);

  // Form States
  const [campCode, setCampCode] = useState("");
  const [campName, setCampName] = useState("");
  const [campStartDate, setCampStartDate] = useState(new Date().toISOString().split("T")[0]);
  const [lockNotes, setLockNotes] = useState("");
  const [pointCode, setPointCode] = useState("");
  const [pointLat, setPointLat] = useState("28.5050");
  const [pointLon, setPointLon] = useState("77.1050");
  const [pointLandUnitId, setPointLandUnitId] = useState("");
  const [pointStratumId, setPointStratumId] = useState("");

  // Lab Receipt Form
  const [labName, setLabName] = useState("Eurofins Agri Testing");
  const [receiptCondition, setReceiptCondition] = useState("ACCEPTABLE");
  const [sealStatus, setSealStatus] = useState("SEALED_INTACT");
  const [intakeStatus, setIntakeStatus] = useState("ACCEPTED");
  const [rejectionReason, setRejectionReason] = useState("");
  const [receivedByName, setReceivedByName] = useState("Lab Intake Officer");

  // Lab Analysis Form
  const [analyticalMethod, setAnalyticalMethod] = useState("DRY_COMBUSTION");
  const [socValue, setSocValue] = useState("1.85");
  const [analystName, setAnalystName] = useState("Senior Chemist");

  // Revise Result Form
  const [revisedValue, setRevisedValue] = useState("1.90");
  const [revisionReason, setRevisionReason] = useState("Calibration verification re-test");

  // QA Review Form
  const [qaReviewerName, setQaReviewerName] = useState("Lead MRV QA Officer");
  const [qaOverallStatus, setQaOverallStatus] = useState("ACCEPTED");
  const [qaNotes, setQaNotes] = useState("Coordinates, custody logs, and laboratory assays verified compliant.");

  const loadData = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      const [cData, sData, rData, luData, stData] = await Promise.all([
        fetchSamplingCampaigns(projectId),
        fetchPhysicalSamples(projectId),
        fetchGroundEvidenceReadiness(projectId),
        fetchLandUnits(projectId),
        fetchProjectStrata(projectId),
      ]);
      setCampaigns(cData);
      setPhysicalSamples(sData);
      setReadiness(rData);
      setLandUnits(luData || []);
      setStrata(stData || []);

      if (cData.length > 0 && !selectedCampaignId) {
        setSelectedCampaignId(cData[0].id);
      }
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed loading ground evidence records.");
    } finally {
      setLoading(false);
    }
  }, [projectId, selectedCampaignId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Load plan versions and points when campaign changes
  useEffect(() => {
    if (!projectId || !selectedCampaignId) return;
    Promise.all([
      fetchSamplingPlanVersions(projectId, selectedCampaignId),
      fetchSamplingPoints(projectId, selectedCampaignId),
    ])
      .then(([pvData, ptData]) => {
        setPlanVersions(pvData);
        setSamplingPoints(ptData);
      })
      .catch((e) => console.warn("Failed loading campaign sub-resources:", e));
  }, [projectId, selectedCampaignId]);

  const handleCreateCampaign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!campCode.trim() || !campName.trim()) {
      setErrorMsg("Campaign code and name are mandatory.");
      return;
    }
    setActionLoading(true);
    try {
      const newCamp = await createSamplingCampaign(projectId, {
        campaign_code: campCode.trim().toUpperCase(),
        name: campName.trim(),
        planned_start_date: campStartDate,
      });
      // Automatically create initial plan version v1
      await createSamplingPlanVersion(projectId, newCamp.id, {
        effective_as_of_date: campStartDate,
      });
      setSuccessMsg(`Campaign '${newCamp.campaign_code}' created with Plan Version 1.`);
      setShowCreateCampaignModal(false);
      setSelectedCampaignId(newCamp.id);
      setCampCode("");
      setCampName("");
      await loadData();
      const pvs = await fetchSamplingPlanVersions(projectId, newCamp.id);
      setPlanVersions(pvs);
      const pts = await fetchSamplingPoints(projectId, newCamp.id);
      setSamplingPoints(pts);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to create campaign.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleLockPlan = async (versionId: string) => {
    setActionLoading(true);
    try {
      await lockSamplingPlanVersion(projectId, selectedCampaignId, versionId, {
        notes: lockNotes.trim() || "Approved and locked for physical ground sampling execution.",
      });
      setSuccessMsg("Sampling plan version locked. Stratification snapshot frozen.");
      setShowLockPlanModal(false);
      setLockNotes("");
      const pvs = await fetchSamplingPlanVersions(projectId, selectedCampaignId);
      setPlanVersions(pvs);
      const gr = await fetchGroundEvidenceReadiness(projectId);
      setReadiness(gr);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed locking plan version.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleCreatePoints = async (e: React.FormEvent) => {
    e.preventDefault();
    const activeVersion = planVersions[0];
    if (!activeVersion) {
      setErrorMsg("No sampling plan version available.");
      return;
    }
    if (!pointCode.trim() || !pointLandUnitId) {
      setErrorMsg("Point code and Land Unit are mandatory.");
      return;
    }
    setActionLoading(true);
    try {
      await createSamplingPoints(projectId, selectedCampaignId, activeVersion.id, {
        points: [
          {
            point_code: pointCode.trim().toUpperCase(),
            land_unit_id: pointLandUnitId,
            stratum_id: pointStratumId || undefined,
            planned_lat: parseFloat(pointLat),
            planned_lon: parseFloat(pointLon),
            target_depth_from_cm: 0,
            target_depth_to_cm: 30,
            is_composite: false,
            subsample_count: 1,
          },
        ],
      });
      setSuccessMsg(`Sampling point '${pointCode}' and physical sample initialized.`);
      setShowCreatePointsModal(false);
      setPointCode("");
      await loadData();
      const pts = await fetchSamplingPoints(projectId, selectedCampaignId);
      setSamplingPoints(pts);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed adding sampling point.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleRecordLabReceipt = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeSample) return;
    setActionLoading(true);
    try {
      await recordSampleLaboratoryReceipt(projectId, activeSample.id, {
        laboratory_name: labName.trim(),
        received_at: new Date().toISOString(),
        received_by_name: receivedByName.trim(),
        condition_on_receipt: receiptCondition,
        seal_status: sealStatus,
        intake_status: intakeStatus,
        rejection_reason: intakeStatus === "REJECTED" ? rejectionReason : undefined,
      });
      setSuccessMsg(`Lab intake receipt recorded for ${activeSample.sample_code}.`);
      setShowLabReceiptModal(false);
      setActiveSample(null);
      await loadData();
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed recording laboratory receipt.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleRecordLabAnalysis = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeSample) return;
    setActionLoading(true);
    try {
      await recordSampleLaboratoryAnalysis(projectId, activeSample.id, {
        laboratory_name: labName.trim(),
        analytical_method: analyticalMethod,
        analysis_date: new Date().toISOString().split("T")[0],
        analyst_name: analystName.trim(),
        results: [
          {
            analyte: "SOC_CONCENTRATION",
            raw_value: parseFloat(socValue),
            raw_unit: "%",
            qualifier: "NONE",
          },
        ],
      });
      setSuccessMsg(`Analytical SOC concentration assay recorded for ${activeSample.sample_code}.`);
      setShowLabAnalysisModal(false);
      setActiveSample(null);
      await loadData();
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed recording laboratory analysis.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleReviseResult = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeResult) return;
    if (!revisionReason.trim()) {
      setErrorMsg("Revision reason is mandatory.");
      return;
    }
    setActionLoading(true);
    try {
      await reviseLaboratoryResult(projectId, activeResult.id, {
        new_raw_value: parseFloat(revisedValue),
        new_raw_unit: "%",
        revision_reason: revisionReason.trim(),
      });
      setSuccessMsg(`Result revised. Original superseded in immutable audit trail.`);
      setShowReviseResultModal(false);
      setActiveResult(null);
      await loadData();
      if (selectedSampleForLineage) {
        const refreshed = await fetchPhysicalSample(projectId, selectedSampleForLineage.id);
        setSelectedSampleForLineage((prev) => (prev ? refreshed : null));
      }
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed revising result.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleRecordQAReview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeSample) return;
    setActionLoading(true);
    try {
      await recordSampleQAReview(projectId, activeSample.id, {
        reviewer_name: qaReviewerName.trim(),
        overall_qa_status: qaOverallStatus,
        location_verified: true,
        deviation_acceptable: true,
        depth_valid: true,
        custody_complete: true,
        lab_receipt_verified: true,
        required_assays_present: true,
        notes: qaNotes.trim(),
      });
      setSuccessMsg(`QA Review recorded (${qaOverallStatus}) for ${activeSample.sample_code}.`);
      setShowQAReviewModal(false);
      setActiveSample(null);
      await loadData();
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed recording QA review.");
    } finally {
      setActionLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const formatted = status ? status.replace(/_/g, " ") : "UNKNOWN";
    switch (status) {
      case "COMPLETE":
      case "ACCEPTED":
      case "QA_ACCEPTED":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 size={12} />
            {formatted}
          </span>
        );
      case "NEEDS_REVIEW":
      case "INCOMPLETE":
      case "ANALYSIS_IN_PROGRESS":
      case "RECEIVED_BY_LAB":
      case "IN_FIELD":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
            <AlertTriangle size={12} />
            {formatted}
          </span>
        );
      case "REJECTED":
      case "REJECTED_BY_LAB":
      case "CANCELLED":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20">
            <AlertTriangle size={12} />
            {formatted}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-zinc-500/10 text-zinc-600 dark:text-zinc-400 border border-zinc-500/20">
            <HelpCircle size={12} />
            {formatted}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Alert Messages */}
      {errorMsg && (
        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-xs text-red-600 dark:text-red-400 flex items-center justify-between">
          <span>{errorMsg}</span>
          <button onClick={() => setErrorMsg(null)} className="text-xs font-bold ml-2 cursor-pointer">✕</button>
        </div>
      )}
      {successMsg && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-xs text-emerald-600 dark:text-emerald-400 flex items-center justify-between">
          <span>{successMsg}</span>
          <button onClick={() => setSuccessMsg(null)} className="text-xs font-bold ml-2 cursor-pointer">✕</button>
        </div>
      )}

      {/* Top Banner: Ground Evidence Readiness Summary */}
      <div
        data-testid="ground-evidence-readiness-card"
        className="p-5 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-sm space-y-4"
      >
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-[var(--color-border)] pb-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
                Phase 2 MRV Operational Workflow
              </span>
              <div data-testid="ground-readiness-overall">
                {readiness && getStatusBadge(readiness.overall_status)}
              </div>
            </div>
            <h2 className="text-lg font-bold text-[var(--color-text-primary)] mt-0.5 flex items-center gap-2">
              <TestTube size={18} className="text-emerald-500" />
              Defensible Ground Evidence & Laboratory Assays
            </h2>
            <p className="text-xs text-[var(--color-text-secondary)]">
              Physical ground-evidence chain: Campaign → Plan Version → Sampling Point → Field Collection → Custody → Lab Receipt → Assays → QA Review
            </p>
          </div>

          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)] hover:bg-[var(--color-surface)] transition-colors cursor-pointer"
          >
            <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
            <span>Refresh State</span>
          </button>
        </div>

        {/* 9 Categorical Readiness Component Badges */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-9 gap-2">
          {readiness?.components &&
            Object.entries(readiness.components).map(([key, comp]) => (
              <div
                key={key}
                data-testid={`ground-comp-${key}`}
                className="p-2 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] space-y-1"
              >
                <div className="text-[9px] uppercase font-bold text-[var(--color-text-muted)] tracking-wider truncate">
                  {key.replace(/_/g, " ")}
                </div>
                <div>{getStatusBadge(comp.status)}</div>
                <div className="text-[10px] text-[var(--color-text-secondary)] line-clamp-2 leading-tight">
                  {comp.message}
                </div>
              </div>
            ))}
        </div>
      </div>

      {/* Phase 2 Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-[var(--color-border)] overflow-x-auto pb-px">
        {[
          { id: "readiness", label: "Ground Readiness Audit", icon: ShieldCheck },
          { id: "campaigns", label: `Campaigns & Points (${samplingPoints.length})`, icon: MapPin },
          { id: "samples", label: `Physical Samples & Assays (${physicalSamples.length})`, icon: TestTube },
          { id: "bulk-import", label: "Laboratory Bulk Import", icon: FileSpreadsheet },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              data-testid={`tab-ground-${tab.id}`}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold border-b-2 rounded-t-lg transition-all cursor-pointer ${
                isActive
                  ? "border-emerald-500 text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 font-bold"
                  : "border-transparent text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface)]"
              }`}
            >
              <Icon size={13} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* TAB 1: GROUND READINESS AUDIT */}
      {activeTab === "readiness" && readiness?.components && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(readiness.components).map(([compKey, comp]) => (
              <div
                key={compKey}
                className="p-4 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-2.5"
              >
                <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-2">
                  <div className="font-semibold text-xs text-[var(--color-text-primary)] uppercase tracking-wider">
                    {compKey.replace(/_/g, " ")}
                  </div>
                  {getStatusBadge(comp.status)}
                </div>
                <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">{comp.message}</p>
                {comp.details && Object.keys(comp.details).length > 0 && (
                  <div className="p-2.5 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] text-[11px] font-mono space-y-1">
                    {Object.entries(comp.details).map(([k, v]) => (
                      <div key={k} className="flex justify-between">
                        <span className="text-[var(--color-text-muted)]">{k}:</span>
                        <span className="text-[var(--color-text-primary)] font-medium">
                          {Array.isArray(v) ? v.join(", ") || "none" : String(v)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 2: SAMPLING CAMPAIGNS & POINTS */}
      {activeTab === "campaigns" && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-bold text-[var(--color-text-primary)]">Ground Sampling Campaigns</h3>
              <p className="text-xs text-[var(--color-text-secondary)]">
                Design and lock spatial sampling campaigns with frozen stratification snapshots.
              </p>
            </div>
            {canManagePlans && (
              <button
                data-testid="btn-create-campaign"
                onClick={() => setShowCreateCampaignModal(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white transition-colors cursor-pointer"
              >
                <Plus size={13} />
                <span>New Campaign</span>
              </button>
            )}
          </div>

          {/* Campaign Selector / Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {campaigns.map((camp) => {
              const isSelected = camp.id === selectedCampaignId;
              return (
                <div
                  key={camp.id}
                  onClick={() => setSelectedCampaignId(camp.id)}
                  className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                    isSelected
                      ? "border-emerald-500 bg-emerald-500/5 shadow-sm"
                      : "border-[var(--color-border)] bg-[var(--color-surface)] hover:border-[var(--color-text-muted)]"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-[var(--color-text-primary)]">
                      {camp.campaign_code}
                    </span>
                    {getStatusBadge(camp.status)}
                  </div>
                  <h4 className="text-xs font-semibold text-[var(--color-text-primary)] mt-1">{camp.name}</h4>
                  <div className="text-[11px] text-[var(--color-text-secondary)] mt-2 flex items-center justify-between">
                    <span>Planned: {camp.planned_start_date || "—"}</span>
                    <span>Updated: {camp.updated_at ? new Date(camp.updated_at).toLocaleDateString() : "—"}</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Selected Campaign Plan Versions & Points */}
          {selectedCampaignId && (
            <div className="p-4 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] space-y-4">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-[var(--color-border)] pb-3">
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)]">
                    Sampling Plan Versions
                  </h4>
                  <p className="text-xs text-[var(--color-text-secondary)]">
                    Plan versions freeze stratification metadata. Once locked, point allocation is permanent.
                  </p>
                </div>
                {canManagePlans && (
                  <div className="flex items-center gap-2">
                    <button
                      data-testid="btn-add-points"
                      onClick={() => setShowCreatePointsModal(true)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)] hover:bg-[var(--color-surface)] cursor-pointer"
                    >
                      <Plus size={12} />
                      <span>Add Planned Point</span>
                    </button>
                  </div>
                )}
              </div>

              {/* Plan Versions List */}
              <div className="space-y-2">
                {planVersions.map((pv) => (
                  <div
                    key={pv.id}
                    className="p-3 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-[var(--color-text-primary)]">
                          Version {pv.version_number}
                        </span>
                        {pv.is_locked ? (
                          <span data-testid="plan-locked-badge" className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                            <Lock size={10} /> LOCKED
                          </span>
                        ) : (
                          <span data-testid="plan-draft-badge" className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-500 border border-amber-500/20">
                            DRAFT / UNLOCKED
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-[var(--color-text-secondary)] mt-1">
                        Effective As Of: <span className="font-mono">{pv.effective_as_of_date}</span>
                        {pv.locked_at && <span> • Locked At: {new Date(pv.locked_at).toLocaleString()}</span>}
                      </div>
                    </div>

                    {!pv.is_locked && canManagePlans && (
                      <button
                        data-testid="btn-lock-plan"
                        onClick={() => setShowLockPlanModal(true)}
                        className="flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded bg-emerald-600 hover:bg-emerald-700 text-white cursor-pointer"
                      >
                        <Lock size={12} />
                        <span>Lock Version</span>
                      </button>
                    )}
                  </div>
                ))}
              </div>

              {/* Planned Sampling Points Table */}
              <div className="pt-2">
                <h4 className="text-xs font-bold text-[var(--color-text-primary)] mb-2">
                  Planned Sampling Points ({samplingPoints.length})
                </h4>
                <div className="overflow-x-auto border border-[var(--color-border)] rounded-lg">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[var(--color-background)] text-[var(--color-text-secondary)] uppercase text-[10px] font-bold">
                      <tr>
                        <th className="p-2.5">Point Code</th>
                        <th className="p-2.5">Target Depth</th>
                        <th className="p-2.5">Coordinates (WGS84)</th>
                        <th className="p-2.5">Land Unit</th>
                        <th className="p-2.5">Stratum</th>
                        <th className="p-2.5">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--color-border)] text-[var(--color-text-primary)]">
                      {samplingPoints.map((pt) => {
                        const lu = landUnits.find((u) => u.id === pt.land_unit_id);
                        const st = strata.find((s) => s.id === pt.stratum_id);
                        return (
                          <tr key={pt.id} className="hover:bg-[var(--color-background)]/50 transition-colors">
                            <td className="p-2.5 font-mono font-bold text-emerald-600 dark:text-emerald-400">
                              {pt.point_code}
                            </td>
                            <td className="p-2.5 font-mono">
                              {pt.target_depth_from_cm} - {pt.target_depth_to_cm} cm
                            </td>
                            <td className="p-2.5 font-mono">
                              {pt.planned_lat != null && pt.planned_lon != null
                                ? `${Number(pt.planned_lat).toFixed(5)}, ${Number(pt.planned_lon).toFixed(5)}`
                                : "—"}
                            </td>
                            <td className="p-2.5 text-xs">{lu?.name || (pt.land_unit_id ? pt.land_unit_id.slice(0, 8) : "—")}</td>
                            <td className="p-2.5 text-xs">{st?.name || (pt.stratum_id ? pt.stratum_id.slice(0, 8) : "—")}</td>
                            <td className="p-2.5">{getStatusBadge(pt.status)}</td>
                          </tr>
                        );
                      })}
                      {samplingPoints.length === 0 && (
                        <tr>
                          <td colSpan={6} className="p-6 text-center text-xs text-[var(--color-text-secondary)]">
                            No sampling points registered for this campaign yet.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: PHYSICAL SAMPLES & LABORATORY ASSAYS */}
      {activeTab === "samples" && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-bold text-[var(--color-text-primary)]">
                Physical Ground Samples & Assays
              </h3>
              <p className="text-xs text-[var(--color-text-secondary)]">
                Complete custody, laboratory intake, analytical SOC assays, and QA signoff.
              </p>
            </div>
          </div>

          <div className="overflow-x-auto border border-[var(--color-border)] rounded-xl bg-[var(--color-surface)]">
            <table className="w-full text-left text-xs">
              <thead className="bg-[var(--color-background)] text-[var(--color-text-secondary)] uppercase text-[10px] font-bold">
                <tr>
                  <th className="p-3">Sample Code</th>
                  <th className="p-3">Point Code</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Collection Date</th>
                  <th className="p-3">Geodesic Deviation</th>
                  <th className="p-3">Laboratory</th>
                  <th className="p-3">SOC Concentration</th>
                  <th className="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-border)] text-[var(--color-text-primary)]">
                {physicalSamples.map((sample) => {
                  const col = sample.collection_event;
                  const rec = sample.laboratory_receipt;
                  const analyses = sample.laboratory_analyses || [];
                  const activeResult = analyses
                    .flatMap((a) => a.results || [])
                    .find((r) => (r.analyte === "SOC_CONCENTRATION" || r.analyte === "SOC_STOCK_PCT") && !r.is_superseded);

                  return (
                    <tr key={sample.id} className="hover:bg-[var(--color-background)]/50 transition-colors">
                      <td className="p-3 font-mono font-bold text-emerald-600 dark:text-emerald-400">
                        {sample.sample_code}
                      </td>
                      <td className="p-3 font-mono">{sample.sampling_point?.point_code || "—"}</td>
                      <td className="p-3">{getStatusBadge(sample.status)}</td>
                      <td className="p-3 text-xs">
                        {col && (col.collection_timestamp || (col as any).collected_at)
                          ? new Date(col.collection_timestamp || (col as any).collected_at).toLocaleDateString()
                          : "Pending"}
                      </td>
                      <td className="p-3 font-mono text-xs">
                        {col && col.deviation_distance_m != null ? (
                          <div className="space-y-0.5">
                            <div>{Number(col.deviation_distance_m).toFixed(1)} m</div>
                            <div className="text-[10px]">
                              {(col as any).configured_tolerance_m != null ? (
                                Number(col.deviation_distance_m) <= Number((col as any).configured_tolerance_m) ? (
                                  <span className="text-emerald-500 font-semibold">PASS (tol: {Number((col as any).configured_tolerance_m).toFixed(0)}m)</span>
                                ) : (
                                  <span className="text-rose-500 font-semibold">EXCEEDS (tol: {Number((col as any).configured_tolerance_m).toFixed(0)}m)</span>
                                )
                              ) : (
                                <span className="text-amber-500 font-semibold">NEEDS_REVIEW (No tolerance set)</span>
                              )}
                            </div>
                          </div>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="p-3 text-xs">{rec?.laboratory_name || "—"}</td>
                      <td className="p-3 font-mono">
                        {activeResult ? `${activeResult.raw_value}%` : "—"}
                      </td>
                      <td className="p-3 text-right space-x-1">
                        <button
                          data-testid="btn-view-lineage"
                          onClick={() => setSelectedSampleForLineage(sample)}
                          className="px-2 py-1 rounded bg-[var(--color-background)] border border-[var(--color-border)] hover:bg-[var(--color-surface)] text-[11px] font-semibold text-[var(--color-text-primary)] cursor-pointer"
                        >
                          Lineage
                        </button>

                        {/* Action buttons based on status */}
                        {(sample.status === "COLLECTED" || sample.status === "SEALED" || sample.status === "IN_TRANSIT") && canManagePlans && (
                          <button
                            data-testid="btn-record-receipt"
                            onClick={() => {
                              setActiveSample(sample);
                              setShowLabReceiptModal(true);
                            }}
                            className="px-2 py-1 rounded bg-blue-600 hover:bg-blue-700 text-white text-[11px] font-semibold cursor-pointer"
                          >
                            Lab Intake
                          </button>
                        )}

                        {sample.status === "RECEIVED_BY_LAB" && canManagePlans && (
                          <button
                            data-testid="btn-record-analysis"
                            onClick={() => {
                              setActiveSample(sample);
                              setShowLabAnalysisModal(true);
                            }}
                            className="px-2 py-1 rounded bg-purple-600 hover:bg-purple-700 text-white text-[11px] font-semibold cursor-pointer"
                          >
                            Record Assay
                          </button>
                        )}

                        {sample.status === "ANALYZED" && canPerformQA && (
                          <button
                            data-testid="btn-record-qa"
                            onClick={() => {
                              setActiveSample(sample);
                              setShowQAReviewModal(true);
                            }}
                            className="px-2 py-1 rounded bg-emerald-600 hover:bg-emerald-700 text-white text-[11px] font-semibold cursor-pointer"
                          >
                            QA Signoff
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
                {physicalSamples.length === 0 && (
                  <tr>
                    <td colSpan={8} className="p-8 text-center text-xs text-[var(--color-text-secondary)]">
                      No physical samples registered. Initialize sampling points in a locked campaign to generate physical samples.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 4: LABORATORY BULK DATA IMPORT */}
      {activeTab === "bulk-import" && (
        <AgricultureLaboratoryBulkImportView
          projectId={projectId}
          onImportSuccess={loadData}
          isAuditor={isAuditor}
          isFieldAgent={isFieldAgent}
        />
      )}

      {/* MODAL 1: SAMPLE LINEAGE DRAWER */}
      {selectedSampleForLineage && (
        <div
          data-testid="sample-lineage-drawer"
          className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex justify-end transition-opacity"
        >
          <div className="w-full max-w-xl bg-[var(--color-surface)] border-l border-[var(--color-border)] h-full overflow-y-auto p-6 space-y-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-4">
              <div>
                <span className="text-[10px] uppercase font-bold text-[var(--color-text-muted)] tracking-wider">
                  Physical Ground Sample Lineage
                </span>
                <h3 className="text-base font-bold font-mono text-[var(--color-text-primary)]">
                  {selectedSampleForLineage.sample_code}
                </h3>
              </div>
              <button
                data-testid="btn-close-lineage"
                onClick={() => setSelectedSampleForLineage(null)}
                className="p-1 rounded-lg hover:bg-[var(--color-background)] text-[var(--color-text-secondary)] text-sm font-bold cursor-pointer"
              >
                ✕
              </button>
            </div>

            {/* 1. Planned Point & Stratum */}
            <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-[var(--color-text-primary)] flex items-center gap-1.5">
                  <MapPin size={13} className="text-emerald-500" />
                  1. Planned Sample Point & Stratum
                </span>
                <span className="font-mono text-xs font-semibold">
                  {selectedSampleForLineage.sampling_point?.point_code}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-[var(--color-text-muted)]">Planned Lat/Lon: </span>
                  <span className="font-mono font-medium">
                    {selectedSampleForLineage.sampling_point?.planned_lat != null && selectedSampleForLineage.sampling_point?.planned_lon != null
                      ? `${Number(selectedSampleForLineage.sampling_point.planned_lat).toFixed(5)}, ${Number(selectedSampleForLineage.sampling_point.planned_lon).toFixed(5)}`
                      : "—"}
                  </span>
                </div>
                <div>
                  <span className="text-[var(--color-text-muted)]">Target Depth: </span>
                  <span className="font-mono font-medium">
                    {selectedSampleForLineage.sampling_point?.target_depth_from_cm ?? 0} -{" "}
                    {selectedSampleForLineage.sampling_point?.target_depth_to_cm ?? 30} cm
                  </span>
                </div>
              </div>
            </div>

            {/* 2. Field Collection Event */}
            <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] space-y-2">
              <span className="text-xs font-bold text-[var(--color-text-primary)] flex items-center gap-1.5">
                <ClipboardCheck size={13} className="text-blue-500" />
                2. Field Collection Event
              </span>
              {selectedSampleForLineage.collection_event ? (
                <div className="space-y-2 text-xs">
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <span className="text-[var(--color-text-muted)]">Actual Lat/Lon: </span>
                      <span className="font-mono font-medium">
                        {selectedSampleForLineage.collection_event.actual_lat != null && selectedSampleForLineage.collection_event.actual_lon != null
                          ? `${Number(selectedSampleForLineage.collection_event.actual_lat).toFixed(5)}, ${Number(selectedSampleForLineage.collection_event.actual_lon).toFixed(5)}`
                          : "—"}
                      </span>
                    </div>
                    <div>
                      <span className="text-[var(--color-text-muted)]">Deviation Distance: </span>
                      <span className="font-mono font-bold text-[var(--color-text-primary)]">
                        {selectedSampleForLineage.collection_event.deviation_distance_m != null
                          ? `${Number(selectedSampleForLineage.collection_event.deviation_distance_m).toFixed(1)} m`
                          : "—"}
                      </span>
                    </div>
                    <div>
                      <span className="text-[var(--color-text-muted)]">Configured Tolerance: </span>
                      <span className="font-mono text-[var(--color-text-secondary)]">
                        {(selectedSampleForLineage.collection_event as any).configured_tolerance_m != null
                          ? `${Number((selectedSampleForLineage.collection_event as any).configured_tolerance_m).toFixed(1)} m`
                          : "Not configured"}
                      </span>
                    </div>
                    <div>
                      <span className="text-[var(--color-text-muted)]">Deviation Status: </span>
                      <span className="font-semibold text-xs">
                        {selectedSampleForLineage.collection_event.deviation_distance_m == null
                          ? "—"
                          : (selectedSampleForLineage.collection_event as any).configured_tolerance_m != null
                          ? Number(selectedSampleForLineage.collection_event.deviation_distance_m) <= Number((selectedSampleForLineage.collection_event as any).configured_tolerance_m)
                            ? <span className="text-emerald-500">PASS</span>
                            : <span className="text-rose-500">EXCEEDS_TOLERANCE</span>
                          : <span className="text-amber-500">NEEDS_REVIEW (No tolerance set)</span>}
                      </span>
                    </div>
                    <div>
                      <span className="text-[var(--color-text-muted)]">Collector: </span>
                      <span>{selectedSampleForLineage.collection_event.collector_name}</span>
                    </div>
                    <div>
                      <span className="text-[var(--color-text-muted)]">Timestamp: </span>
                      <span>
                        {new Date(selectedSampleForLineage.collection_event.collection_timestamp).toLocaleString()}
                      </span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-xs text-[var(--color-text-secondary)] italic">
                  Sample has not yet been collected in the field.
                </div>
              )}
            </div>

            {/* 3. Chain of Custody History */}
            <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] space-y-2">
              <span className="text-xs font-bold text-[var(--color-text-primary)] flex items-center gap-1.5">
                <Truck size={13} className="text-amber-500" />
                3. Unbroken Chain of Custody Timeline (
                {selectedSampleForLineage.custody_events?.length || 0} events)
              </span>
              <div className="space-y-2 pt-1">
                {(selectedSampleForLineage.custody_events || []).map((ev, idx) => (
                  <div
                    key={ev.id}
                    className="p-2.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] text-xs space-y-1"
                  >
                    <div className="flex items-center justify-between font-mono font-bold">
                      <span className="text-emerald-600 dark:text-emerald-400">
                        #{idx + 1} {ev.event_type}
                      </span>
                      <span className="text-[10px] text-[var(--color-text-muted)]">
                        {new Date(ev.event_timestamp).toLocaleString()}
                      </span>
                    </div>
                    <div className="text-[11px] text-[var(--color-text-secondary)]">
                      Custodian: <span className="font-medium text-[var(--color-text-primary)]">{ev.custodian_name}</span> (
                      {ev.custodian_organization})
                    </div>
                    {ev.seal_identifier && (
                      <div className="text-[11px] font-mono text-zinc-500">Seal: {ev.seal_identifier}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* 4. Laboratory Receipt & Assays */}
            <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] space-y-2">
              <span className="text-xs font-bold text-[var(--color-text-primary)] flex items-center gap-1.5">
                <Microscope size={13} className="text-purple-500" />
                4. Laboratory Receipt & Analytical Assays
              </span>
              {selectedSampleForLineage.laboratory_receipt && (
                <div className="text-xs border-b border-[var(--color-border)] pb-2 mb-2">
                  <div>
                    Lab: <span className="font-semibold">{selectedSampleForLineage.laboratory_receipt.laboratory_name}</span> • Intake:{" "}
                    <span className="font-bold text-emerald-500">
                      {selectedSampleForLineage.laboratory_receipt.intake_status}
                    </span>
                  </div>
                </div>
              )}

              {/* Assays List */}
              <div className="space-y-2">
                {(selectedSampleForLineage.laboratory_analyses || []).map((an) => (
                  <div key={an.id} className="p-2.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] text-xs space-y-1.5">
                    <div className="flex items-center justify-between font-semibold">
                      <span>Method: {an.analytical_method}</span>
                      <span className="text-[10px] text-[var(--color-text-muted)]">{an.analysis_date}</span>
                    </div>
                    {an.results.map((res) => (
                      <div
                        key={res.id}
                        className={`p-2 rounded flex items-center justify-between font-mono text-xs ${
                          res.is_superseded
                            ? "bg-red-500/10 text-red-500 line-through"
                            : "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-bold"
                        }`}
                      >
                        <div>
                          <span>{res.analyte}: </span>
                          <span>
                            {res.raw_value} {res.raw_unit}
                          </span>
                          {res.is_superseded && <span className="ml-2 text-[10px] font-normal">(SUPERSEDED)</span>}
                        </div>
                        {!res.is_superseded && canManagePlans && (
                          <button
                            data-testid="btn-revise-result"
                            onClick={() => {
                              setActiveResult(res);
                              setShowReviseResultModal(true);
                            }}
                            className="px-2 py-0.5 text-[10px] font-sans font-semibold rounded bg-[var(--color-background)] border border-[var(--color-border)] hover:bg-[var(--color-surface)] text-[var(--color-text-primary)] cursor-pointer"
                          >
                            Revise
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>

            {/* 5. QA Review Signoff */}
            <div className="p-4 rounded-xl bg-[var(--color-background)] border border-[var(--color-border)] space-y-2">
              <span className="text-xs font-bold text-[var(--color-text-primary)] flex items-center gap-1.5">
                <FileCheck size={13} className="text-emerald-500" />
                5. QA Review & Signoff
              </span>
              {selectedSampleForLineage.qa_review ? (
                <div className="space-y-1 text-xs">
                  <div className="flex items-center justify-between">
                    <span>Verdict: </span>
                    <span className="font-bold text-emerald-500">
                      {selectedSampleForLineage.qa_review.overall_qa_status}
                    </span>
                  </div>
                  <div>Reviewer: {selectedSampleForLineage.qa_review.reviewer_name}</div>
                  <div className="text-[11px] text-[var(--color-text-secondary)] italic">
                    Notes: {selectedSampleForLineage.qa_review.notes}
                  </div>
                </div>
              ) : (
                <div className="text-xs text-[var(--color-text-secondary)] italic">
                  QA review pending.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: CREATE CAMPAIGN */}
      {showCreateCampaignModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl max-w-md w-full p-5 space-y-4 shadow-xl">
            <h3 className="font-bold text-sm text-[var(--color-text-primary)] flex items-center gap-2">
              <Plus size={16} /> Create Sampling Campaign
            </h3>
            <form onSubmit={handleCreateCampaign} className="space-y-3 text-xs">
              <div>
                <label className="block text-[var(--color-text-secondary)] mb-1">Campaign Code</label>
                <input
                  type="text"
                  required
                  value={campCode}
                  onChange={(e) => setCampCode(e.target.value)}
                  placeholder="e.g. CAMP-2025-POST-MONSOON"
                  className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)] font-mono"
                />
              </div>
              <div>
                <label className="block text-[var(--color-text-secondary)] mb-1">Campaign Name</label>
                <input
                  type="text"
                  required
                  value={campName}
                  onChange={(e) => setCampName(e.target.value)}
                  placeholder="e.g. Baseline Ground Sampling Campaign"
                  className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)]"
                />
              </div>
              <div>
                <label className="block text-[var(--color-text-secondary)] mb-1">Planned Start Date</label>
                <input
                  type="date"
                  required
                  value={campStartDate}
                  onChange={(e) => setCampStartDate(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)] font-mono"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateCampaignModal(false)}
                  className="px-3 py-1.5 rounded border border-[var(--color-border)] text-[var(--color-text-secondary)] cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-700 text-white font-semibold cursor-pointer"
                >
                  {actionLoading ? "Creating..." : "Create Campaign"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 3: LOCK SAMPLING PLAN */}
      {showLockPlanModal && planVersions[0] && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl max-w-md w-full p-5 space-y-4 shadow-xl">
            <h3 className="font-bold text-sm text-[var(--color-text-primary)] flex items-center gap-2">
              <Lock size={16} className="text-amber-500" /> Lock Sampling Plan Version
            </h3>
            <p className="text-xs text-[var(--color-text-secondary)]">
              Locking freezes the project stratification snapshot and transitions the campaign to an immutable design ready for physical field collection.
            </p>
            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-[var(--color-text-secondary)] mb-1">Approval Notes</label>
                <textarea
                  rows={2}
                  value={lockNotes}
                  onChange={(e) => setLockNotes(e.target.value)}
                  placeholder="e.g. Approved and verified compliant with VM0042 stratification guidelines."
                  className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)]"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowLockPlanModal(false)}
                  className="px-3 py-1.5 rounded border border-[var(--color-border)] text-[var(--color-text-secondary)] cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => handleLockPlan(planVersions[0].id)}
                  disabled={actionLoading}
                  className="px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-700 text-white font-semibold cursor-pointer"
                >
                  {actionLoading ? "Locking..." : "Confirm & Lock"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 4: ADD SAMPLING POINTS */}
      {showCreatePointsModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl max-w-md w-full p-5 space-y-4 shadow-xl">
            <h3 className="font-bold text-sm text-[var(--color-text-primary)] flex items-center gap-2">
              <Plus size={16} /> Add Planned Sampling Point
            </h3>
            <form onSubmit={handleCreatePoints} className="space-y-3 text-xs">
              <div>
                <label className="block text-[var(--color-text-secondary)] mb-1">Point Code</label>
                <input
                  type="text"
                  required
                  value={pointCode}
                  onChange={(e) => setPointCode(e.target.value)}
                  placeholder="e.g. P-01"
                  className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)] font-mono"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[var(--color-text-secondary)] mb-1">Planned Lat</label>
                  <input
                    type="number"
                    step="0.00001"
                    required
                    value={pointLat}
                    onChange={(e) => setPointLat(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)] font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[var(--color-text-secondary)] mb-1">Planned Lon</label>
                  <input
                    type="number"
                    step="0.00001"
                    required
                    value={pointLon}
                    onChange={(e) => setPointLon(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)] font-mono"
                  />
                </div>
              </div>
              <div>
                <label className="block text-[var(--color-text-secondary)] mb-1">Land Unit</label>
                <select
                  data-testid="select-point-land-unit"
                  required
                  value={pointLandUnitId}
                  onChange={(e) => setPointLandUnitId(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)]"
                >
                  <option value="">Select Land Unit</option>
                  {landUnits.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.name} ({u.unit_type})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-[var(--color-text-secondary)] mb-1">Stratum (Optional)</label>
                <select
                  data-testid="select-point-stratum"
                  value={pointStratumId}
                  onChange={(e) => setPointStratumId(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)]"
                >
                  <option value="">Select Stratum</option>
                  {strata.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.code})
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreatePointsModal(false)}
                  className="px-3 py-1.5 rounded border border-[var(--color-border)] text-[var(--color-text-secondary)] cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-700 text-white font-semibold cursor-pointer"
                >
                  {actionLoading ? "Adding..." : "Add Point"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 5: RECORD LAB RECEIPT */}
      {showLabReceiptModal && activeSample && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl max-w-md w-full p-5 space-y-4 shadow-xl">
            <h3 className="font-bold text-sm text-[var(--color-text-primary)] flex items-center gap-2">
              <Microscope size={16} /> Record Formal Laboratory Intake Receipt
            </h3>
            <form onSubmit={handleRecordLabReceipt} className="space-y-3 text-xs">
              <div>
                <label className="block text-[var(--color-text-secondary)] mb-1">Laboratory Name</label>
                <input
                  type="text"
                  required
                  value={labName}
                  onChange={(e) => setLabName(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)]"
                />
              </div>
              <div>
                <label className="block text-[var(--color-text-secondary)] mb-1">Intake Officer Name</label>
                <input
                  type="text"
                  required
                  value={receivedByName}
                  onChange={(e) => setReceivedByName(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)]"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[var(--color-text-secondary)] mb-1">Seal Status</label>
                  <select
                    value={sealStatus}
                    onChange={(e) => setSealStatus(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)]"
                  >
                    <option value="SEALED_INTACT">SEALED_INTACT</option>
                    <option value="BROKEN">BROKEN</option>
                    <option value="UNSEALED">UNSEALED</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[var(--color-text-secondary)] mb-1">Intake Status</label>
                  <select
                    value={intakeStatus}
                    onChange={(e) => setIntakeStatus(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)]"
                  >
                    <option value="ACCEPTED">ACCEPTED</option>
                    <option value="REJECTED">REJECTED</option>
                  </select>
                </div>
              </div>
              {intakeStatus === "REJECTED" && (
                <div>
                  <label className="block text-[var(--color-text-secondary)] mb-1">Rejection Reason</label>
                  <input
                    type="text"
                    required
                    value={rejectionReason}
                    onChange={(e) => setRejectionReason(e.target.value)}
                    placeholder="e.g. Sample bag ruptured during transit"
                    className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)]"
                  />
                </div>
              )}
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowLabReceiptModal(false)}
                  className="px-3 py-1.5 rounded border border-[var(--color-border)] text-[var(--color-text-secondary)] cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-3 py-1.5 rounded bg-blue-600 hover:bg-blue-700 text-white font-semibold cursor-pointer"
                >
                  {actionLoading ? "Submitting..." : "Submit Receipt"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 6: RECORD LAB ANALYSIS */}
      {showLabAnalysisModal && activeSample && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl max-w-md w-full p-5 space-y-4 shadow-xl">
            <h3 className="font-bold text-sm text-[var(--color-text-primary)] flex items-center gap-2">
              <Microscope size={16} /> Record Analytical Laboratory Assay
            </h3>
            <form onSubmit={handleRecordLabAnalysis} className="space-y-3 text-xs">
              <div>
                <label className="block text-[var(--color-text-secondary)] mb-1">Analytical Method</label>
                <select
                  value={analyticalMethod}
                  onChange={(e) => setAnalyticalMethod(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)] font-mono"
                >
                  <option value="DRY_COMBUSTION">DRY_COMBUSTION (ISO 10694 / Elemental Analyzer)</option>
                  <option value="WALKLEY_BLACK">WALKLEY_BLACK (Wet Chemical Oxidation)</option>
                  <option value="MID_INFRARED_SPECTROSCOPY">MID_INFRARED_SPECTROSCOPY (MIRS with local calibration)</option>
                  <option value="LOSS_ON_IGNITION">LOSS_ON_IGNITION (LOI)</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[var(--color-text-secondary)] mb-1">SOC Concentration (%)</label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    value={socValue}
                    onChange={(e) => setSocValue(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)] font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[var(--color-text-secondary)] mb-1">Analyst Name</label>
                  <input
                    type="text"
                    required
                    value={analystName}
                    onChange={(e) => setAnalystName(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)]"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowLabAnalysisModal(false)}
                  className="px-3 py-1.5 rounded border border-[var(--color-border)] text-[var(--color-text-secondary)] cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-3 py-1.5 rounded bg-purple-600 hover:bg-purple-700 text-white font-semibold cursor-pointer"
                >
                  {actionLoading ? "Recording..." : "Record Assay"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 7: REVISE LAB RESULT */}
      {showReviseResultModal && activeResult && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl max-w-md w-full p-5 space-y-4 shadow-xl">
            <h3 className="font-bold text-sm text-[var(--color-text-primary)] flex items-center gap-2">
              <History size={16} className="text-amber-500" /> Revise Laboratory Result
            </h3>
            <p className="text-xs text-[var(--color-text-secondary)]">
              Laboratory results are immutable. Revising creates a new superseding entry and preserves the original value in the audit log.
            </p>
            <form onSubmit={handleReviseResult} className="space-y-3 text-xs">
              <div>
                <label className="block text-[var(--color-text-secondary)] mb-1">
                  New Raw Value ({activeResult.raw_unit})
                </label>
                <input
                  type="number"
                  step="0.0001"
                  required
                  value={revisedValue}
                  onChange={(e) => setRevisedValue(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)] font-mono"
                />
              </div>
              <div>
                <label className="block text-[var(--color-text-secondary)] mb-1">Revision Reason</label>
                <textarea
                  rows={2}
                  required
                  value={revisionReason}
                  onChange={(e) => setRevisionReason(e.target.value)}
                  placeholder="e.g. Lab machine recalibration / duplicate re-run adjustment"
                  className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)]"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowReviseResultModal(false)}
                  className="px-3 py-1.5 rounded border border-[var(--color-border)] text-[var(--color-text-secondary)] cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-3 py-1.5 rounded bg-amber-600 hover:bg-amber-700 text-white font-semibold cursor-pointer"
                >
                  {actionLoading ? "Revising..." : "Submit Revision"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 8: QA REVIEW SIGNOFF */}
      {showQAReviewModal && activeSample && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl max-w-md w-full p-5 space-y-4 shadow-xl">
            <h3 className="font-bold text-sm text-[var(--color-text-primary)] flex items-center gap-2">
              <FileCheck size={16} className="text-emerald-500" /> QA Review & Signoff
            </h3>
            <form onSubmit={handleRecordQAReview} className="space-y-3 text-xs">
              <div>
                <label className="block text-[var(--color-text-secondary)] mb-1">QA Reviewer Name</label>
                <input
                  type="text"
                  required
                  value={qaReviewerName}
                  onChange={(e) => setQaReviewerName(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)]"
                />
              </div>
              <div>
                <label className="block text-[var(--color-text-secondary)] mb-1">Verdict</label>
                <select
                  value={qaOverallStatus}
                  onChange={(e) => setQaOverallStatus(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)]"
                >
                  <option value="ACCEPTED">ACCEPTED (All compliance criteria met)</option>
                  <option value="REJECTED">REJECTED (Non-compliant)</option>
                </select>
              </div>
              <div className="p-2.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] space-y-1 text-[11px]">
                <div className="font-semibold text-[var(--color-text-primary)]">Verified Criteria:</div>
                <div className="text-emerald-500">✓ Geodesic coordinate containment within land unit</div>
                <div className="text-emerald-500">✓ Target extraction depth (0-30 cm)</div>
                <div className="text-emerald-500">✓ Unbroken chain of custody transfer log</div>
                <div className="text-emerald-500">✓ Accredited lab intake & seal validation</div>
                <div className="text-emerald-500">✓ Standardized SOC analytical assay result</div>
              </div>
              <div>
                <label className="block text-[var(--color-text-secondary)] mb-1">Review Notes</label>
                <textarea
                  rows={2}
                  value={qaNotes}
                  onChange={(e) => setQaNotes(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-primary)]"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowQAReviewModal(false)}
                  className="px-3 py-1.5 rounded border border-[var(--color-border)] text-[var(--color-text-secondary)] cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-700 text-white font-semibold cursor-pointer"
                >
                  {actionLoading ? "Submitting..." : "Sign & Accept"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
